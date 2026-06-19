# Device-config YAML entry formats — primer

> **Defer to the file on disk.** The shapes below are starting points; the
> instrument's existing `devices.yml` (or equivalent) is authoritative. If a
> built-in class is used differently in the file you're reading, match the
> file.

The device-config YAML is a Guarneri-style flat catalog. Each top-level key
is the dotted Python import path to a class. Its value is a list of instance
dictionaries — one per instance to create. The skill `epics-2-ophyd`
appends one new key (or one new list item under an existing key) per device
it generates.

## Built-in classes

### `ophyd.EpicsMotor`

```yaml
ophyd.EpicsMotor:
  - name: m1
    prefix: "ioc:m1"
    labels: [motor]
```

`prefix` is the **full motor record name**. Per-record fields (`.RBV`,
`.VAL`, `.STOP`, etc.) are discovered by `EpicsMotor` itself; you do not
list them.

### `ophyd.EpicsSignal`

```yaml
ophyd.EpicsSignal:
  - name: my_setpoint
    read_pv: "ioc:Foo_RBV"
    write_pv: "ioc:Foo"
```

`read_pv` and `write_pv` are full PV names. Omit `write_pv` if read and write
go to the same PV.

### `ophyd.EpicsSignalRO`

```yaml
ophyd.EpicsSignalRO:
  - name: my_input
    read_pv: "ioc:Foo_RBV"
```

Full PV in `read_pv`. Use this when the underlying record is intrinsically
read-only (`*in`, `calc`, `event`, etc.).

## Custom Device subclasses

For a class the skill itself writes — say
`my_instrument.devices.foo.FooDevice` subclassing `Device` — the entry
typically carries `prefix:` plus whatever extra constructor kwargs the
`__init__` accepts (per-component PV suffixes, motor names, etc.):

```yaml
my_instrument.devices.foo.FooDevice:
  - name: foo
    prefix: "ioc:foo:"
    labels: [diagnostics]
    # Whatever else __init__ wants:
    x_motor: m1
    y_motor: m2
```

The Components defined on the class supply the suffixes; the `prefix:` here
is the parent prefix prepended to those suffixes at construction. **Read the
target class's `__init__` and the existing YAML entries for the same class
to confirm the field set** before writing a new one.

## Common pitfalls

- **Quoting.** Prefixes with colons (`"8idiSoft:CR8-D1:"`) should be quoted —
  YAML mostly tolerates unquoted colons inside a value, but quoting removes
  ambiguity. Match what the file already does.
- **Labels.** Some instruments use labels heavily, some not at all. Don't
  invent labels — match what neighbouring entries use, or omit.
- **Trailing colon in prefix.** `"ioc:foo:"` (with colon) vs `"ioc:foo"` (no
  colon) changes the suffix composition. The Component suffixes you wrote in
  the Python file must agree with the prefix style used in the YAML entry.
- **One class, many instances.** If a class already has a list under its
  dotted path, append to that list — don't duplicate the key.
