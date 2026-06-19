#!/usr/bin/env python3
"""Parse an EPICS IOC repo and emit a JSON description of its PVs.

The output is consumed by the epics-2-ophyd skill to propose a curated set of
PVs to wrap in an ophyd Device. The script is intentionally deterministic: it
does not invent attribute names, decide kinds, or pick docstrings. It reports
what the IOC's db files declare and what its operator screens reference.

Usage:
    parse_ioc.py --ioc-root <path> [--output ioc.json] [--prefix urExample:]

What it does
------------
1. Walks the IOC repo for *.db, *.template, and *.substitutions files.
2. Parses every record block: `record(<type>, "<name>") { field(DESC, ...) ... }`.
3. Expands substitutions files (file ... { pattern { vars } { row1 } ... }) by
   substituting each row's macros into the referenced template/db.
4. Strips a leading `$(P)` (or `$(PREFIX)`, or whatever macro the user names
   via --prefix-macro) from every record name to produce a per-record suffix.
5. Tries to discover the default IOC prefix from `iocBoot/*/st.cmd*` via
   `epicsEnvSet("PREFIX", "...")`.
6. Walks `*App/op/**/*.{bob,opi,adl,ui,edl}` and extracts every PV reference
   it finds in the screen sources. This is a "user-facing" signal — PVs that
   show up on operator screens are almost always worth including in the
   generated device. Screen scanning is best-effort; surface unknown formats
   as warnings rather than failing.
7. Emits JSON with: prefix (best guess), records (list), screen_pvs (list),
   the file inventories, and warnings.

It does NOT:
- Decide ophyd signal classes (the skill body owns that mapping).
- Generate Python source.
- Rewrite the IOC's files.
- Connect to a running IOC.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

# Record blocks: `record(type, "name") { ... }`. Names may contain $(MACRO)
# expansions, so we accept anything that isn't a quote.
RECORD_RE = re.compile(
    r'record\s*\(\s*([A-Za-z_][\w]*)\s*,\s*"([^"]+)"\s*\)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
    re.MULTILINE | re.DOTALL,
)

# Field assignments inside a record body: `field(NAME, "value")`.
FIELD_RE = re.compile(r'field\s*\(\s*([A-Z0-9_]+)\s*,\s*"([^"]*)"\s*\)')

# Macro reference: $(NAME) or $(NAME=default). The default is restricted to
# characters other than parentheses so this regex only matches the innermost
# macro of any nested expansion (e.g. for `$(DESC=Soft Motor $(SM))` it picks
# `$(SM)` first; iterative expansion then resolves the outer one).
MACRO_RE = re.compile(r"\$\(([A-Za-z_][\w]*)(?:=([^()]*))?\)")

# `epicsEnvSet("PREFIX", "urExample:")` — used to guess the default prefix.
ENVSET_RE = re.compile(
    r'epicsEnvSet\s*\(\s*"(PREFIX|P)"\s*,\s*"([^"]+)"\s*\)', re.IGNORECASE
)


@dataclass
class ScreenPV:
    """One PV reference extracted from a screen file."""

    raw: str  # As it appears in the screen, with any $(...) macros intact.
    suffix: str  # raw with the prefix macro stripped (best effort).
    has_unresolved_macro: bool  # True if the suffix still contains `$(`.
    source_file: str  # Repo-relative path to the screen.
    screen_format: str  # "bob", "opi", "adl", "ui", "edl".


@dataclass
class Record:
    """One EPICS record after macro substitution and prefix stripping."""

    record_type: str  # "ai", "bo", "motor", "waveform", ...
    suffix: str  # Name with the prefix macro stripped, e.g. "Dashboard:Connected"
    full_name: str  # Original name from the db file (still macro-expanded)
    desc: str = ""  # Contents of field(DESC, "...") if any
    dtyp: str = ""  # Contents of field(DTYP, "...") if any
    ftvl: str = ""  # waveform element type (CHAR/STRING/DOUBLE/...) if waveform
    nelm: str = ""  # waveform element count if waveform
    source_file: str = ""  # Repo-relative path to the file the record came from
    is_readonly: bool = False  # True for *in records, calc, etc. (skill confirms)


@dataclass
class ParseResult:
    ioc_root: str
    prefix_guess: str = ""
    prefix_macro: str = "P"  # The macro whose value becomes the device prefix
    db_files: list[str] = field(default_factory=list)
    template_files: list[str] = field(default_factory=list)
    substitutions_files: list[str] = field(default_factory=list)
    screen_files: list[str] = field(default_factory=list)
    records: list[Record] = field(default_factory=list)
    screen_pvs: list[ScreenPV] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


SCREEN_EXTS = {".bob", ".opi", ".adl", ".ui", ".edl"}


# Per-format PV-extraction regexes. Each regex's group(1) is the PV string.
# These are intentionally permissive — false positives (e.g. non-PV strings)
# are filtered downstream. False negatives are the real cost.
SCREEN_PV_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    # Phoebus Display Builder XML: PVs in <pv_name>...</pv_name>.
    "bob": [re.compile(r"<pv_name>\s*([^<\s][^<]*?)\s*</pv_name>")],
    # CSS-BOY XML: <pv_name>...</pv_name> (newer) or <pv>...</pv> (legacy).
    "opi": [
        re.compile(r"<pv_name>\s*([^<\s][^<]*?)\s*</pv_name>"),
        re.compile(r"<pv>\s*([^<\s][^<]*?)\s*</pv>"),
    ],
    # MEDM ADL: chan="...", rdbk="...", trig="...", and dynamic-attribute chan.
    "adl": [re.compile(r'\b(?:chan|rdbk|setp|trig|ctrl|read|write)="([^"]+)"')],
    # caQtDM (Qt Designer XML): <property name="channel"><string>PV</string>.
    # Also covers channelA..channelD for record-aware widgets.
    "ui": [
        re.compile(
            r'<property\s+name="channel[A-D]?"\s*>\s*<string[^>]*>'
            r'\s*([^<\s][^<]*?)\s*</string>',
            re.IGNORECASE,
        ),
    ],
    # EDM: lines like `controlPv "ioc:foo"`, `indicatorPv "ioc:bar"`, etc.
    "edl": [
        re.compile(
            r"\b(?:control|indicator|color|vis|alarm|readback|set|write)Pv\s+"
            r'"([^"]+)"',
            re.IGNORECASE,
        ),
    ],
}


READ_ONLY_TYPES = {
    "ai",
    "bi",
    "longin",
    "mbbi",
    "mbbiDirect",
    "stringin",
    "lsi",
    "int64in",
    "calc",
    "subArray",
    "histogram",
    "permissive",
    "event",
}


def discover_files(ioc_root: Path, result: ParseResult) -> None:
    """Find every db/template/substitutions/screen file in the repo."""
    for path in sorted(ioc_root.rglob("*")):
        if not path.is_file():
            continue
        # Skip build artifacts and .git.
        if any(part in {".git", "O.linux-x86_64", "bin", "lib"} for part in path.parts):
            continue
        rel = str(path.relative_to(ioc_root))
        suffix = path.suffix.lower()
        if suffix == ".db":
            result.db_files.append(rel)
        elif suffix == ".template":
            result.template_files.append(rel)
        elif suffix == ".substitutions":
            result.substitutions_files.append(rel)
        elif suffix in SCREEN_EXTS:
            result.screen_files.append(rel)


def discover_prefix(ioc_root: Path, result: ParseResult) -> None:
    """Look in iocBoot/*/st.cmd* for `epicsEnvSet("PREFIX", "...")`."""
    candidates: list[Path] = []
    # st.cmd* and *.cmd files plus the iocsh fragments they source (settings.iocsh,
    # etc.) — synApps-style IOCs put epicsEnvSet("PREFIX", ...) in the latter.
    for pattern in (
        "iocBoot/**/st.cmd*",
        "iocBoot/**/*.cmd",
        "iocBoot/**/*.iocsh",
    ):
        candidates.extend(ioc_root.glob(pattern))
    # Also grep iocs/<name>/iocBoot for nested IOC layouts.
    for pattern in (
        "iocs/*/iocBoot/**/st.cmd*",
        "iocs/*/iocBoot/**/*.cmd",
        "iocs/*/iocBoot/**/*.iocsh",
    ):
        candidates.extend(ioc_root.glob(pattern))

    for cmd in sorted(set(candidates)):
        try:
            text = cmd.read_text(errors="replace")
        except OSError:
            continue
        for match in ENVSET_RE.finditer(text):
            value = match.group(2)
            if value and not result.prefix_guess:
                result.prefix_guess = value
                result.warnings.append(
                    f"Prefix guessed from {cmd.relative_to(ioc_root)}: {value!r}"
                )
                return


def parse_record_body(body: str) -> dict[str, str]:
    """Extract field(NAME, "value") pairs from a record body."""
    fields: dict[str, str] = {}
    for fname, fval in FIELD_RE.findall(body):
        fields[fname] = fval
    return fields


def expand_macros(text: str, mapping: dict[str, str]) -> str:
    """Replace $(NAME) or $(NAME=default) with mapping[NAME] or default.

    Iterates a few times so that nested macros like $(DESC=Soft Motor $(SM))
    fully expand: pass 1 resolves the inner $(SM), pass 2 resolves the outer
    $(DESC=...). Stops when the text stops changing or after 10 passes.
    """

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        default = match.group(2) or ""
        if name in mapping:
            return mapping[name]
        return default if default else match.group(0)

    for _ in range(10):
        new_text = MACRO_RE.sub(repl, text)
        if new_text == text:
            break
        text = new_text
    return text


def strip_prefix(name: str, prefix_macro: str) -> str:
    """Strip the leading $(P) (or $(PREFIX)) macro reference from a record name.

    EPICS IOCs almost always declare records as `$(P)Some:Suffix`. The skill
    needs the suffix because the ophyd Device prefix supplies the rest at
    instantiation time.
    """
    candidates = [
        f"$({prefix_macro})",
        f"$({prefix_macro}=)",
    ]
    for cand in candidates:
        if name.startswith(cand):
            return name[len(cand) :]
    # No leading macro — return as-is so the user sees what's happening.
    return name


def parse_db_text(
    text: str, source: str, prefix_macro: str, extra_macros: dict[str, str] | None = None
) -> list[Record]:
    """Parse db/template text into Record objects.

    `extra_macros` lets a substitutions row pre-populate macros before record
    names are stripped. The prefix macro itself is intentionally NOT expanded
    so the suffix-stripping step is deterministic.
    """
    records: list[Record] = []
    macros = dict(extra_macros or {})

    for match in RECORD_RE.finditer(text):
        rec_type = match.group(1)
        raw_name = match.group(2)
        body = match.group(3)

        # Expand all macros except the prefix macro itself, which we strip below.
        # We achieve this by running expand_macros without the prefix in mapping.
        expanded_name = expand_macros(raw_name, macros)
        suffix = strip_prefix(expanded_name, prefix_macro)

        fields = parse_record_body(body)
        # Some fields may also contain macros (e.g. PORT). Expand those too.
        desc = expand_macros(fields.get("DESC", ""), macros)
        dtyp = expand_macros(fields.get("DTYP", ""), macros)
        ftvl = expand_macros(fields.get("FTVL", ""), macros)
        nelm = expand_macros(fields.get("NELM", ""), macros)

        # Skip template stubs whose suffix still contains an unresolved macro
        # (e.g. `$(SM)`). Those are template definitions waiting for a
        # substitutions row to instantiate them, not real PVs.
        if "$(" in suffix:
            continue

        records.append(
            Record(
                record_type=rec_type,
                suffix=suffix,
                full_name=expanded_name,
                desc=desc,
                dtyp=dtyp,
                ftvl=ftvl,
                nelm=nelm,
                source_file=source,
                is_readonly=rec_type in READ_ONLY_TYPES,
            )
        )

    return records


def parse_substitutions(
    sub_path: Path,
    ioc_root: Path,
    prefix_macro: str,
    result: ParseResult,
) -> list[Record]:
    """Expand a .substitutions file by substituting each row into its template."""
    text = sub_path.read_text(errors="replace")
    rel_sub = str(sub_path.relative_to(ioc_root))
    records: list[Record] = []

    # A substitutions file is a sequence of `file "..." { pattern { ... } { row } ... }`
    # blocks. Tokenize manually because nested braces make regex fragile.
    pos = 0
    while True:
        file_match = re.search(r'file\s+"([^"]+)"\s*\{', text[pos:])
        if not file_match:
            break
        template_ref = file_match.group(1)
        block_start = pos + file_match.end()  # Position just after the opening {
        # Find the matching closing brace for this `file { ... }` block.
        depth = 1
        i = block_start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        if depth != 0:
            result.warnings.append(f"Unbalanced braces in {rel_sub}; stopped parsing")
            break
        block_text = text[block_start : i - 1]
        pos = i

        # Resolve the template path. Substitutions files commonly reference the
        # template via a macro like $(URROBOT)/db/foo.db. We try the literal
        # path, then a few fallbacks based on the IOC root layout.
        template_paths = _resolve_template(template_ref, sub_path, ioc_root)
        template_path = next((p for p in template_paths if p.is_file()), None)
        if template_path is None:
            result.warnings.append(
                f"{rel_sub}: could not locate template {template_ref!r}"
            )
            continue
        template_text = template_path.read_text(errors="replace")

        # Inside the block: zero or more `pattern { vars } { row } { row }` groups,
        # OR `{ KEY=VAL, KEY=VAL } { ... }` style. Handle the pattern form which
        # is what synApps/areaDetector use almost exclusively.
        for prow_match in re.finditer(
            r"pattern\s*\{([^}]*)\}((?:\s*\{[^}]*\})+)", block_text
        ):
            var_names = [v.strip() for v in prow_match.group(1).split(",") if v.strip()]
            rows_blob = prow_match.group(2)
            for row_match in re.finditer(r"\{([^}]*)\}", rows_blob):
                row_values = _split_csv(row_match.group(1))
                if len(row_values) != len(var_names):
                    result.warnings.append(
                        f"{rel_sub}: row/pattern column mismatch "
                        f"({len(row_values)} values vs {len(var_names)} vars)"
                    )
                    continue
                row_macros = dict(zip(var_names, row_values))
                records.extend(
                    parse_db_text(
                        template_text,
                        source=f"{rel_sub} → {template_path.relative_to(ioc_root)}",
                        prefix_macro=prefix_macro,
                        extra_macros=row_macros,
                    )
                )

        # Also handle the simpler { KEY=VAL, ... } { ... } form (no `pattern`).
        for kv_match in re.finditer(
            r"\{\s*([A-Za-z_]\w*\s*=[^{}]+)\}", block_text
        ):
            assignments = kv_match.group(1)
            row_macros = {}
            for assign in re.split(r",\s*", assignments):
                if "=" not in assign:
                    continue
                k, v = assign.split("=", 1)
                row_macros[k.strip()] = v.strip().strip('"')
            if row_macros:
                records.extend(
                    parse_db_text(
                        template_text,
                        source=f"{rel_sub} → {template_path.relative_to(ioc_root)}",
                        prefix_macro=prefix_macro,
                        extra_macros=row_macros,
                    )
                )

    return records


def _split_csv(row: str) -> list[str]:
    """Split a substitutions row on commas, respecting double-quoted strings."""
    out: list[str] = []
    buf: list[str] = []
    in_quote = False
    for ch in row:
        if ch == '"':
            in_quote = not in_quote
            continue
        if ch == "," and not in_quote:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf).strip())
    return out


def _resolve_template(template_ref: str, sub_path: Path, ioc_root: Path) -> list[Path]:
    """Return a list of plausible filesystem paths for a template reference."""
    # Drop any leading $(MACRO)/ — we'll search for the bare filename inside the IOC.
    bare = re.sub(r"^\$\([^)]+\)/?", "", template_ref)
    candidates = [
        Path(template_ref),  # absolute or already-resolved
        sub_path.parent / template_ref,
        sub_path.parent / Path(template_ref).name,
        ioc_root / bare,
        ioc_root / "db" / Path(template_ref).name,
    ]
    # Also search any *App/Db directory.
    for db_dir in ioc_root.glob("*/Db"):
        candidates.append(db_dir / Path(template_ref).name)
    return candidates


def strip_known_prefix(name: str, prefix_macro: str, literal_prefix: str) -> str:
    """Strip the prefix from a PV name.

    Tries macro form (`$(P)`) first, then a known literal prefix
    (`RobocartUR5:`) if provided. Screens frequently embed both forms.
    """
    stripped = strip_prefix(name, prefix_macro)
    if literal_prefix and stripped.startswith(literal_prefix):
        stripped = stripped[len(literal_prefix) :]
    return stripped


def scan_screen_pvs(
    screen_path: Path,
    ioc_root: Path,
    prefix_macro: str,
    literal_prefix: str = "",
) -> list[ScreenPV]:
    """Extract PV references from one screen file."""
    suffix = screen_path.suffix.lower().lstrip(".")
    patterns = SCREEN_PV_PATTERNS.get(suffix, [])
    if not patterns:
        return []

    try:
        text = screen_path.read_text(errors="replace")
    except OSError:
        return []

    rel = str(screen_path.relative_to(ioc_root))
    found: list[ScreenPV] = []
    seen_raw: set[str] = set()

    for pattern in patterns:
        for match in pattern.finditer(text):
            raw = match.group(1).strip()
            # Filter obvious non-PVs. Screens sometimes put format strings or
            # widget IDs in fields we scan; cheap sanity checks remove most.
            if not raw or raw in seen_raw:
                continue
            if "\n" in raw or len(raw) > 200:
                continue
            # PV names contain at least one of these characters in practice;
            # widget labels and plain text generally don't.
            if not any(ch in raw for ch in ":.$"):
                continue
            # Skip MEDM CALC expressions: e.g. `CALC\{(A)\}(xxx:foo)`. These
            # appear in `chan` fields of calc widgets and contain a backslash,
            # which never appears in a real PV name.
            if "\\" in raw or "{" in raw or "}" in raw:
                continue
            # Skip bare prefix references with no suffix (`$(P)`).
            if raw.startswith("$(") and raw.endswith(")") and ")" not in raw[2:-1]:
                continue
            seen_raw.add(raw)

            stripped = strip_known_prefix(raw, prefix_macro, literal_prefix)
            found.append(
                ScreenPV(
                    raw=raw,
                    suffix=stripped,
                    has_unresolved_macro="$(" in stripped,
                    source_file=rel,
                    screen_format=suffix,
                )
            )
    return found


def deduplicate_screen_pvs(items: Iterable[ScreenPV]) -> list[ScreenPV]:
    """Drop duplicates that share the same suffix (keep first seen)."""
    seen: set[str] = set()
    out: list[ScreenPV] = []
    for pv in items:
        key = pv.suffix or pv.raw
        if key in seen:
            continue
        seen.add(key)
        out.append(pv)
    return out


def deduplicate(records: Iterable[Record]) -> list[Record]:
    """Drop records that share the same (suffix, record_type), keep first seen.

    Duplicates show up when the same db is loaded under multiple iocsh contexts
    or when a substitutions row targets a db that's also loaded directly.
    """
    seen: set[tuple[str, str]] = set()
    out: list[Record] = []
    for rec in records:
        key = (rec.suffix, rec.record_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ioc-root",
        required=True,
        type=Path,
        help="Path to the IOC repository root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the JSON output. Defaults to stdout.",
    )
    parser.add_argument(
        "--prefix-macro",
        default="P",
        help="Macro name used as the device prefix in record() declarations. "
        "Defaults to 'P', which is the convention used by synApps/areaDetector "
        "and most APS IOCs. Override with 'PREFIX' or similar if the IOC uses "
        "a different convention.",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Override the auto-discovered default prefix value (e.g. urExample:).",
    )
    args = parser.parse_args(argv)

    ioc_root = args.ioc_root.expanduser().resolve()
    if not ioc_root.is_dir():
        print(f"error: {ioc_root} is not a directory", file=sys.stderr)
        return 2

    result = ParseResult(ioc_root=str(ioc_root), prefix_macro=args.prefix_macro)

    discover_files(ioc_root, result)
    discover_prefix(ioc_root, result)
    if args.prefix:
        result.prefix_guess = args.prefix

    # Parse direct db/template files.
    for rel in result.db_files + result.template_files:
        path = ioc_root / rel
        try:
            text = path.read_text(errors="replace")
        except OSError as exc:
            result.warnings.append(f"could not read {rel}: {exc}")
            continue
        result.records.extend(
            parse_db_text(text, source=rel, prefix_macro=args.prefix_macro)
        )

    # Expand substitutions files.
    for rel in result.substitutions_files:
        path = ioc_root / rel
        result.records.extend(
            parse_substitutions(path, ioc_root, args.prefix_macro, result)
        )

    result.records = deduplicate(result.records)

    # Scan operator screens for PV references. Pass the known literal prefix
    # (if any) so screen PVs like "RobocartUR5:allstop.VAL" reduce to suffixes.
    for rel in result.screen_files:
        path = ioc_root / rel
        result.screen_pvs.extend(
            scan_screen_pvs(
                path,
                ioc_root,
                args.prefix_macro,
                literal_prefix=result.prefix_guess,
            )
        )
    result.screen_pvs = deduplicate_screen_pvs(result.screen_pvs)

    if result.screen_files and not result.screen_pvs:
        result.warnings.append(
            f"Scanned {len(result.screen_files)} screen file(s) but "
            "extracted no PV references — formats may be unrecognized."
        )

    # Cross-reference: which suffixes appear on screens but not in records?
    record_suffixes = {r.suffix for r in result.records}
    screen_only = sorted(
        {pv.suffix for pv in result.screen_pvs}
        - record_suffixes
        - {""}
    )
    screen_only_clean = [s for s in screen_only if "$(" not in s]

    payload = {
        "ioc_root": result.ioc_root,
        "prefix_guess": result.prefix_guess,
        "prefix_macro": result.prefix_macro,
        "db_files": result.db_files,
        "template_files": result.template_files,
        "substitutions_files": result.substitutions_files,
        "screen_files": result.screen_files,
        "record_count": len(result.records),
        "screen_pv_count": len(result.screen_pvs),
        "records": [asdict(r) for r in result.records],
        "screen_pvs": [asdict(pv) for pv in result.screen_pvs],
        "screen_only_suffixes": screen_only_clean,
        "warnings": result.warnings,
    }

    output_text = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(output_text)
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
