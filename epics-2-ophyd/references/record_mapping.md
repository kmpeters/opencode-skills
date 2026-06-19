# EPICS Record → ophyd Component Mapping

Lookup table used when picking the ophyd component class for a chosen PV.
This is a fallback — when the instrument's existing `<instrument>/devices/`
modules use a different class for the same record type, **prefer their
choice**. The skill matches local conventions before applying this table.

## Quick reference

| EPICS record type      | ophyd component        | Notes                                       |
| ---------------------- | ---------------------- | ------------------------------------------- |
| `motor`                | `EpicsMotor`           | Full positioner: `.move(...)`, `.position`. |
| `ai`                   | `EpicsSignalRO`        | Analog input — read-only by record class.   |
| `ao`                   | `EpicsSignal`          | Analog output — read+write.                 |
| `bi`                   | `EpicsSignalRO`        | Binary input.                               |
| `bo`                   | `EpicsSignal`          | Binary output (commands, enables).          |
| `longin` / `int64in`   | `EpicsSignalRO`        | Integer input.                              |
| `longout` / `int64out` | `EpicsSignal`          | Integer output.                             |
| `mbbi` / `mbbiDirect`  | `EpicsSignalRO`        | Multi-bit input. Add `string=True`.         |
| `mbbo` / `mbboDirect`  | `EpicsSignal`          | Multi-bit output. Add `string=True`.        |
| `stringin` / `lsi`     | `EpicsSignalRO`        | Add `string=True`.                          |
| `stringout` / `lso`    | `EpicsSignal`          | Add `string=True`.                          |
| `waveform` (CHAR)      | `EpicsSignal`          | Add `string=True` (long-string convention). |
| `waveform` (other)     | `EpicsSignal`          | Numeric array; defaults are fine.           |
| `calc`                 | `EpicsSignalRO`        | Computed value, read-only.                  |
| `calcout` / `scalcout` | `EpicsSignal`          | Computed with output side.                  |
| `seq` / `sseq`         | `EpicsSignal`          | Sequencer trigger.                          |
| `busy`                 | `EpicsSignal`          | Used as a wait/handshake; read+write.       |
| `transform`            | `EpicsSignal`          | Read+write.                                 |
| `dfanout` / `fanout`   | `EpicsSignal`          | Read+write.                                 |
| `printf` / `luascript` | `EpicsSignal`          | Action triggers; treat as writable.         |
| `event` / `histogram`  | `EpicsSignalRO`        | Read-only by record class.                  |
| `subArray`             | `EpicsSignalRO`        | Read-only slice of a waveform.              |
| anything else          | `EpicsSignal`          | Safe writable default; mention in warnings. |

## Why these choices

- **Read-only vs writable.** EPICS itself enforces read-only behavior for
  `*in`, `calc`, `event`, `histogram`, and `subArray` — the underlying record
  has no writable VAL field. Mapping these to `EpicsSignalRO` makes ophyd
  reject accidental `.put(...)` calls early instead of waiting for an EPICS
  error.
- **`EpicsMotor` for motor records.** Motor records carry `.RBV`, `.VAL`,
  `.STOP`, `.HLM`, `.LLM`, `.EGU`, etc. as related fields. `EpicsMotor` knows
  about all of these and exposes `.move()`, `.set()`, `.position`, and
  `.stop()`. A bare `EpicsSignal` would only see `.VAL` and break Bluesky's
  scan plans (`bps.mv`, `bps.rel_set`).
- **`string=True` for enums and stringy waveforms.** `mbbi`/`mbbo` records
  encode numeric enums with string labels (e.g. `0=Off, 1=On, 2=Fault`). With
  `string=True`, `.get()` returns the human-readable label, which is what
  almost every plan expects. Same for `waveform` records whose `FTVL` is
  `CHAR` — those are the "long string" convention used for filenames and
  paths in many APS IOCs.

## Setpoint / readback pairs

When the chosen PVs include a pair like `Foo` (writable) + `Foo_RBV`
(read-only), or `*Cmd.VAL` + `*Rbv.VAL`, there are three reasonable patterns.
Pick the simplest that fits the use; mention the alternatives in the summary
so the user can refactor later if needed.

1. **Two separate Cpts.** Default when in doubt. The user gets independent
   handles on the setpoint and the readback.
2. **`EpicsSignal(read_pv=..., write_pv=...)`.** One signal with split read
   and write addresses. Good when the pair behaves like a single value to the
   user.
3. **`EpicsSignalWithRBV`.** Convenience wrapper for the `_RBV` convention
   specifically. Equivalent to (2) but reads cleaner when the naming follows
   the EPICS standard.
4. **`PVPositioner`** (or `PVPositionerComparator`). Use when the pair
   represents motion-like state where Bluesky needs `.set()` semantics and a
   done condition — typically with a tolerance. Heavier than the signal
   options; reserve for actual positioners.

## Edge cases to surface in the report

- **Records the parser couldn't classify.** Record types not in the table
  default to `EpicsSignal`; warn.
- **Records whose suffix still contains an unexpanded macro** (`$(...)`).
  Drop them and mention how many.
- **PVs found on a screen but not as records** (or vice-versa). Both happen:
  screens can reference PVs from loaded support modules whose db files
  weren't part of `--ioc-root`; records can exist that no screen exposes.
  List a count of each; let the user decide whether to chase the missing
  source.
- **Dominant sub-namespace.** If most chosen PVs share a leading
  sub-namespace (`Receive:Joint*`, `Slit*:size`), mention it as a candidate
  for a sub-`Device` later. Don't refactor automatically — the user owns
  shape decisions.

## What NOT to put on the generated class

- **`kind=` on normal signals.** `kind="config"` vs `kind="normal"` is a
  scientific judgment about which signals are part of the experiment
  configuration vs. live data. An auto-generated class can't know that, and
  ophyd's default (`Kind.normal`) is correct for most signals. Use
  `kind="omitted"` only for helper/diagnostic signals (e.g. `.PROC` triggers)
  that shouldn't appear in normal reads.
- **Per-Cpt docstrings.** EPICS `DESC` fields are short and often missing or
  cryptic; per-signal docstrings just clutter the file. Put DESC text in a
  trailing inline comment only when the description adds information that
  the attribute name alone doesn't already convey.
- **Default values, sub-devices, or computed signals invented by the skill.**
  The class faithfully translates chosen PVs into Components — refactoring
  (e.g. introducing a sub-`Device` for a sub-namespace, adding a derived
  computed signal) is a separate exercise the user opts into.
