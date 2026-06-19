---
name: epics-2-ophyd
description: Create an ophyd Device class that wraps an EPICS IOC's PVs for a BITS instrument package, and register it in the instrument's device-config YAML. Use whenever the user wants to add hardware support to a BITS instrument from an IOC — e.g. "make an ophyd device for this IOC", "add a device to <instrument>", "wrap these PVs into a device", "create a device class and put it in devices.yml", "build a Bluesky device for <ioc>". Trigger even if the user doesn't say "ophyd" or "skill" outright but is clearly bridging an IOC to a BITS instrument. Bias toward triggering — skills tend to under-fire.
---

# epics-2-ophyd

Bridges two repos that the user keeps separate: an **EPICS IOC source tree**
(records and screens) and a **BITS instrument repo** (Bluesky-on-the-Beamline
packages). The skill reads the IOC source, writes Python into the BITS repo,
and updates a device-config YAML so Bluesky can load the device by name. The
IOC is **not** assumed to be running — everything is discovered statically.

## Inputs (ask for whichever is missing)

- **BITS instrument repo** — the repo root. The skill expects `src/<package>/`
  packages, each with a `devices/` subpackage and a configs folder containing
  one or more device-config YAML files (`devices.yml`-style).
- **IOC source** — a local path to an EPICS IOC repo, or a clone URL. Either
  the deployed IOC or the support module the IOC loads — both contain db files
  and (usually) screens.

If only one is given, ask for the other before doing anything. Do not guess
from a parent directory; the cost of writing to the wrong instrument or
pointing at the wrong IOC is hours of confusion.

## Hard rules (read these first)

- **The IOC will not be running.** Discover PVs statically from db files and
  screens. Never `caget`/`dbl`/`puttest`. Never invent a PV that isn't in the
  IOC source.
- **Never connect or import-with-connection.** The generated module is written
  to disk and parsed; it is not instantiated. The user runs it themselves.
- **Match the instrument's ophyd flavor — don't mix.** Detect classic threaded
  ophyd vs ophyd-async from the existing `<instrument>/devices/*.py` and
  conform. The reference module at `references/reference_module.py` is classic
  threaded ophyd; treat it as the style baseline *only when the instrument
  itself has no established pattern*.
- **Defer to the instrument's local conventions** for imports, base classes,
  Component vs FormattedComponent usage, docstrings, naming, prefix+suffix
  composition, YAML entry format, and lint config. Read 2–3 existing modules
  and the existing YAML to learn them before writing.
- **Two-repo discipline.** READ from the IOC source. WRITE to the BITS repo.
  Never modify the IOC source. Never put IOC-source paths into the generated
  Python.

## Workflow

### Step 1 — Pick the instrument package

Walk `<bits_repo>/src/` for packages that have a `devices/` subpackage.

- More than one → **ASK** which (single-select, with the list of candidates).
- Exactly one → use it and say so in one sentence.
- None → stop and report. The user has pointed at the wrong repo or the BITS
  layout doesn't match expectations.

### Step 2 — Learn the instrument's conventions

Before writing anything:

1. List `<instrument>/devices/*.py` (excluding `__init__.py` and trivial
   files). Read 2–3 representative ones — prefer modules that resemble what
   you're about to build (motor-heavy → read a motor module; mixed signals →
   read a mixed one).
2. Read the config YAML(s) in the configs folder. Note how entries are shaped
   for the built-in classes (`EpicsMotor`, `EpicsSignal`, `EpicsSignalRO`) and
   for the package's own classes. See `references/yaml_entry_formats.md` for
   the built-in shapes — but the file you read on disk is authoritative.
3. Detect the ophyd flavor:
   - `from ophyd import Component, EpicsMotor, EpicsSignal` → classic threaded.
   - `from ophyd_async.core import ...`, `from ophyd_async.epics.signal import
     ...` → ophyd-async.
   - Mixed → ask. Don't decide for the user.

If the instrument has no existing modules (greenfield package), use
`references/reference_module.py` as the style baseline and tell the user.

### Step 3 — Discover the IOC's PVs

Run the parser:

```bash
python3 ~/.claude/skills/epics-2-ophyd/scripts/parse_ioc.py \
    --ioc-root <ioc_path> --output /tmp/ioc_parsed.json
```

It returns:
- `records` — every record block from `*App/Db/*.{db,template,substitutions}`
  with its type and fields. Substitutions are expanded.
- `pvs_from_screens` — PVs referenced in `*App/op/**/*.{bob,opi,adl,ui,edl}`.
  These are user-facing PVs; presence here is a strong "include me" signal
  even when the record itself is in the IOC's noise floor.
- `prefix` — best-guess deployed prefix from `epicsEnvSet("PREFIX", ...)` in
  `iocBoot/*/st.cmd*`. **Do not trust it.** It's typically a developer test
  value, not the deployed prefix. Ask the user for the real deployment prefix
  before writing the YAML entry.
- `warnings` — surface every one.

The union of `records` and `pvs_from_screens` is your candidate pool.

### Step 4 — Pick which PVs to include (propose, then confirm)

Default behavior: propose a curated set, show it with reasoning, ask for
edits. Don't dump 300 records on the user and ask them to choose blindly.

The proposed set should include:
- Every `motor` record (almost always wanted).
- Every PV that appears on a screen (user-facing).
- Obvious setpoint/readback pairs (e.g. `Foo` + `Foo_RBV`, or
  `*Cmd.VAL` + `*Rbv.VAL` patterns).
- Records the IOC clearly highlights — sub-namespaces dominated by a single
  noun (`Receive:Joint{1..6}`, `Slit*:size`).

Exclude by default (mention them as "skipped — say so if you want them"):
- Pure diagnostic/admin records (`devIocStats`, `alive`, autosave bookkeeping).
- Internal calc-record intermediates with no screen presence.
- Records whose suffix still contains an unexpanded `$(...)` macro.

Present the picked set grouped (motors / setpoint+readback pairs / signals /
triggers), with the record type next to each PV and a one-line "why
included." Then ASK: "Edit this list, or proceed?"

If the user named specific PVs in the original prompt, honor that — skip the
proposal and confirm only the unclear ones.

### Step 5 — Pick component types

For each chosen PV, pick the ophyd component class. **Prefer patterns already
in the instrument's device files.** Where the instrument doesn't dictate, use
this fallback:

| Source                          | Component                                   |
| ------------------------------- | ------------------------------------------- |
| `motor` record                  | `EpicsMotor` (or local subclass if any)     |
| Read-only record (`*in`, `calc`, `event`, `histogram`, `subArray`) or a screen-side `_RBV` | `EpicsSignalRO` |
| Writable scalar                 | `EpicsSignal`                               |
| Setpoint + readback pair        | `EpicsSignal(read_pv=..., write_pv=...)` *or* `EpicsSignalWithRBV` *or* `PVPositioner` — pick the simplest that fits the use; mention the alternatives in the report |
| Group of motors                 | `MotorBundle` subclass                      |
| Other group of related PVs      | `Device` subclass                           |
| Motor + extra record fields (`.PROC`, `.STUP`, etc.) | `EpicsMotor` subclass with `Component(EpicsSignal, ".FIELD", kind="omitted")` |
| Suffix needs runtime templating | `FormattedComponent` |

`mbbi`/`mbbo`/`stringin`/`stringout`/`lsi`/`lso` and `waveform(FTVL=CHAR)`
need `string=True`. See `references/record_mapping.md` for the full type
table and the rationale.

Do **not** add `kind=` to normal signals — `kind="config"` vs `kind="normal"`
is a scientific judgment the user adds later. `kind="omitted"` is fine on
helper/diagnostic signals (e.g. `.PROC` triggers).

### Step 6 — Write the device module

Write to `<instrument>/devices/<module>.py`. Conventions:

- Snake_case module name; PascalCase class name.
- Module + class docstrings in the compact `` ``name`` `` — description style.
  See `references/reference_module.py` for the baseline.
- One symbol per import line. Stdlib above third-party.
- A `Component`'s suffix is *what gets appended to the device prefix*: a full
  PV when the device is instantiated with empty prefix (Component absorbs the
  whole address), or a relative `".FIELD"` when subclassing a record with a
  parent prefix.
- `labels=(...)` as a tuple. `kind="omitted"` only for helper/diagnostic
  signals (e.g. `.PROC`, `.STUP`).
- Class-level configuration constants as typed attributes with defaults (not
  Components). See `GSlitDevice.gap_tolerance` in the reference.
- Bluesky plans as device methods are OK when they fit naturally — use
  keyword-only args, validate inputs, write a numpydoc-style docstring, and
  `yield from bps.mv(...)`. Don't fabricate plans the user didn't ask for; the
  reference's `UsaxsSlitDevice.set_size` is a model for when it's warranted.
- Do not connect, instantiate, or import-with-side-effects.

After writing, confirm the file parses (`python3 -c "import ast;
ast.parse(open(path).read())"`). Do NOT exec it.

### Step 7 — Register in the device-config YAML

Find device-instantiating YAML files in the configs folder (any YAML whose
top-level keys are dotted class paths followed by lists of instance dicts).

- More than one → **ASK** which file to add the entry to.
- Exactly one → use it and say so.
- None → ask the user where the entry should go.

Append an entry mirroring the file's existing format. The dotted class path
key is `<bits_package>.devices.<module>.<ClassName>`. Per-entry fields depend
on the class — defer to what the file already shows for built-ins:

- `EpicsMotor` entries typically carry `prefix:`.
- `EpicsSignal` entries typically carry `read_pv:` and `write_pv:`.
- `EpicsSignalRO` entries typically carry `read_pv:`.
- Custom Device subclasses carry whatever their `__init__` accepts (prefix,
  per-motor PV suffixes, etc.). The existing file is the source of truth for
  the shape.

See `references/yaml_entry_formats.md` for the primer; defer to the file on
disk for anything ambiguous.

After writing, confirm the YAML loads (`python3 -c "import yaml;
yaml.safe_load(open(path))"`).

### Finish — report

Print:
- The Python file path (absolute) and a one-line description of what's in it.
- The YAML file path and the exact entry that was appended, inline.
- The PV list included, with a one-liner for any inferred component type that
  the user might want to revisit.
- A short note that nothing was connected to hardware and the user should
  import + test it themselves.

## Stop-and-ask checklist

These are the points where the skill **must** prompt rather than guess:

1. Multiple instrument packages under `src/` → which one.
2. Ophyd flavor mixed across the instrument's existing modules → which to use.
3. Deployed PV prefix (always — `epicsEnvSet` value is a dev default).
4. PV pick when the user didn't name specific ones → propose + confirm.
5. Multiple device-instantiating YAML files in the configs folder → which one.

## Guardrails (repeated for emphasis)

- **Never invent PVs.** Every PV in the generated file must appear in the IOC
  source (records or screens).
- **Never assume a running IOC.** No `caget`, no connection attempts, no
  imports that touch EPICS.
- **Don't guess the ophyd flavor.** Detect from existing modules; ask if mixed.
- **Match existing conventions.** The instrument's own files outrank the
  reference module.

## References

- `scripts/parse_ioc.py` — static PV discovery (records + screens). Run it;
  don't reimplement.
- `references/reference_module.py` — style baseline for classic threaded
  ophyd. Used when the instrument has no established pattern.
- `references/record_mapping.md` — EPICS record type → ophyd component class.
- `references/yaml_entry_formats.md` — built-in YAML entry shape primer.
