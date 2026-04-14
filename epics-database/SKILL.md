---
name: epics-database
description: Write EPICS database files (.db), templates (.template), and substitution files (.substitutions) for IOC record instances
---

# EPICS Database Skill

You are an expert at writing EPICS database files. You write three kinds of files:

1. **Database files** (`.db`) -- Define record instances with field values.
2. **Template files** (`.template`) -- Database files with macro parameters, intended for reuse via substitution.
3. **Substitution files** (`.substitutions`) -- Instantiate templates with specific macro values.

---

## 1. File Syntax

### 1.1 Record Instance Definition

```
record(recordType, "$(PREFIX):recordName") {
    field(FIELDNAME, "value")
    field(FIELDNAME, numericValue)
    info(infoName, "infoValue")
    alias("$(PREFIX):alternativeName")
}
```

- Record names are strings, typically with macro substitution `$(MACRO)` or `${MACRO}`.
- Field values are quoted strings or bare numeric constants.
- `info()` tags attach metadata (used by Channel Access, PV Access groups, autosave, etc.).
- `alias()` inside a record creates an alternative name for that record.
- Top-level `alias("originalName", "aliasName")` can also be used outside record blocks.
- Comments start with `#`.

### 1.2 Macro Substitution

```
$(MACRO)           # standard macro reference
${MACRO}           # alternate syntax (equivalent)
$(MACRO=default)   # macro with default value
```

Macros are supplied at load time via `dbLoadRecords("file.db", "MACRO1=val1,MACRO2=val2")`.

### 1.3 Substitution File Format

```
file "db/myTemplate.db" {
    pattern { PREFIX, CHANNEL, SCAN }
    { "SYS:SUB1", "Ch1", "1 second" }
    { "SYS:SUB2", "Ch2", "2 second" }
}

file "db/another.db" {
    { PREFIX = "SYS:DEV1" }
    { PREFIX = "SYS:DEV2" }
}
```

Two substitution styles:
- **pattern style**: `pattern { macroNames } { values }` -- column-oriented, good for many instances.
- **simple style**: `{ macro1 = value1, macro2 = value2 }` -- one set per line.

Loaded via `dbLoadTemplate("file.substitutions")` in st.cmd.

---

## 2. Link Field Syntax

Links connect records to data sources, other records, or hardware.

### 2.1 Database Links (PV_LINK)

```
"recordName"                    # Link to VAL field of another record
"recordName.FIELD"              # Link to a specific field
"recordName PP"                 # Process Passive -- process target if SCAN=Passive
"recordName NPP"               # No Process Passive (default for output links)
"recordName MS"                 # Maximize Severity -- propagate alarm severity
"recordName NMS"                # No Maximize Severity (default)
"recordName MSI"                # Maximize Severity if Invalid only
"recordName MSS"                # Maximize Severity and copy Status
"recordName CA"                 # Force Channel Access link (even if same IOC)
"recordName CP"                 # Channel Access + Process on monitor update
"recordName CPP"                # Channel Access + Process Passive on monitor update
"recordName NPP NMS"            # Multiple modifiers combined
```

**Link modifier rules:**
- Process modifiers: `PP`, `NPP`, `CA`, `CP`, `CPP` -- only one of these.
- Severity modifiers: `MS`, `NMS`, `MSI`, `MSS` -- only one of these.
- `CP` and `CPP` are only valid on input links (INP, INPA, etc.). They implicitly force CA.
- `PP` is the default for most input links. `NPP` is the default for output links.
- Forward links (FLNK) do not use modifiers (just the record name).

### 2.2 Constant Links

```
field(INP, "5.0")               # Constant numeric value
field(INP, "")                  # Empty / no link
```

### 2.3 JSON Links (EPICS 7+)

```
field(INP, {const: 5})          # Constant integer
field(INP, {const: "hello"})    # Constant string
field(INP, {const: [1, 2, 3]})  # Constant array
```

### 2.4 Hardware Address Links

**Instrument I/O (INST_IO)** -- most common for device support:
```
field(INP, "@parameter_string")
```

**VME I/O:**
```
field(INP, "#C0 S0 @parm")     # Card 0, Signal 0
```

---

## 3. Common Fields (dbCommon)

All records inherit these fields. The most important ones:

| Field | Type | Description |
|-------|------|-------------|
| `DESC` | STRING(41) | Description string |
| `SCAN` | MENU | Scan rate: `"Passive"`, `"Event"`, `"I/O Intr"`, `"10 second"`, `"5 second"`, `"2 second"`, `"1 second"`, `".5 second"`, `".2 second"`, `".1 second"` |
| `PINI` | MENU | Process at Init: `"NO"`, `"YES"`, `"RUN"`, `"RUNNING"`, `"PAUSE"`, `"PAUSED"` |
| `PHAS` | SHORT | Scan phase (ordering within same scan rate) |
| `EVNT` | STRING | Event name (when SCAN="Event") |
| `DTYP` | DEVICE | Device type (selects device support) |
| `FLNK` | FWDLINK | Forward link -- record to process after this one completes |
| `PRIO` | MENU | Callback priority: `"LOW"`, `"MEDIUM"`, `"HIGH"` |
| `DISV` | SHORT | Disable value (default 1) |
| `DISA` | SHORT | Disable field |
| `SDIS` | INLINK | Scanning disable link |
| `DISP` | UCHAR | Disable putField (1 = block external writes) |
| `TSE` | SHORT | Time stamp event (-2 = device support sets time) |
| `TSEL` | INLINK | Time stamp link (copy timestamp from another record) |
| `ASG` | STRING | Access security group name |
| `TPRO` | UCHAR | Trace processing (set to 1 for debug output) |

---

## 4. Record Type Reference

### 4.1 ai -- Analog Input

Reads a floating-point value. Supports linear conversion, smoothing, and alarm limits.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | DOUBLE | Current value |
| `INP` | INLINK | Input link |
| `EGU` | STRING(16) | Engineering units |
| `PREC` | SHORT | Display precision (decimal places) |
| `LINR` | MENU | Linearization: `"NO CONVERSION"`, `"SLOPE"`, `"LINEAR"`, or breakpoint table |
| `ESLO` | DOUBLE | Raw-to-EGU slope (default 1) |
| `EOFF` | DOUBLE | Raw-to-EGU offset |
| `ASLO` | DOUBLE | Adjustment slope (default 1) |
| `AOFF` | DOUBLE | Adjustment offset |
| `SMOO` | DOUBLE | Smoothing factor (0 = none, 0-1 exponential filter) |
| `HOPR` | DOUBLE | High operating range |
| `LOPR` | DOUBLE | Low operating range |
| `HIHI` | DOUBLE | Hihi alarm limit |
| `HIGH` | DOUBLE | High alarm limit |
| `LOW` | DOUBLE | Low alarm limit |
| `LOLO` | DOUBLE | Lolo alarm limit |
| `HHSV` | MENU | Hihi severity: `"NO_ALARM"`, `"MINOR"`, `"MAJOR"`, `"INVALID"` |
| `HSV` | MENU | High severity |
| `LSV` | MENU | Low severity |
| `LLSV` | MENU | Lolo severity |
| `HYST` | DOUBLE | Alarm deadband |
| `ADEL` | DOUBLE | Archive deadband |
| `MDEL` | DOUBLE | Monitor deadband |
| `AFTC` | DOUBLE | Alarm filter time constant |

```
record(ai, "$(P):Temperature") {
    field(DESC, "Thermocouple reading")
    field(INP,  "$(P):RawTemp CPP MS")
    field(EGU,  "degC")
    field(PREC, "2")
    field(HOPR, "100")
    field(LOPR, "0")
    field(HIHI, "90")
    field(HIGH, "70")
    field(LOW,  "10")
    field(LOLO, "5")
    field(HHSV, "MAJOR")
    field(HSV,  "MINOR")
    field(LSV,  "MINOR")
    field(LLSV, "MAJOR")
    field(HYST, "0.5")
    field(SCAN, "1 second")
}
```

### 4.2 ao -- Analog Output

Writes a floating-point value. Supports drive limits, closed-loop mode, and rate of change limiting.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | DOUBLE | Desired output value |
| `OUT` | OUTLINK | Output link |
| `DOL` | INLINK | Desired output link (for closed_loop mode) |
| `OMSL` | MENU | Output mode: `"supervisory"` (default), `"closed_loop"` |
| `OIF` | MENU | Output incremental flag: `"Full"` (default), `"Incremental"` |
| `DRVH` | DOUBLE | Drive high limit |
| `DRVL` | DOUBLE | Drive low limit |
| `OROC` | DOUBLE | Output rate of change (units/sec, 0 = no limit) |
| `IVOA` | MENU | Invalid output action: `"Continue normally"`, `"Don't drive outputs"`, `"Set output to IVOV"` |
| `IVOV` | DOUBLE | Invalid output value |
| `LINR` | MENU | Linearization (same as ai) |
| `ESLO` | DOUBLE | Raw slope (default 1) |
| `EOFF` | DOUBLE | Raw offset |
| `PREC` | SHORT | Display precision |
| `EGU` | STRING(16) | Engineering units |

Alarm fields: same as ai (HIHI, HIGH, LOW, LOLO, HHSV, HSV, LSV, LLSV, HYST, ADEL, MDEL).

```
record(ao, "$(P):SetVoltage") {
    field(DESC, "Voltage setpoint")
    field(OUT,  "$(P):HW:Voltage PP")
    field(EGU,  "V")
    field(PREC, "3")
    field(DRVH, "10.0")
    field(DRVL, "0.0")
    field(HOPR, "10.0")
    field(LOPR, "0.0")
    field(PINI, "YES")
}
```

**Closed-loop pattern** (output follows another PV):
```
record(ao, "$(P):FollowSetpoint") {
    field(DOL,  "$(P):Setpoint CPP MS")
    field(OMSL, "closed_loop")
    field(OUT,  "$(P):HW:Output PP")
}
```

### 4.3 bi -- Binary Input

Reads a two-state (boolean) value.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | ENUM | Current state (0 or 1) |
| `INP` | INLINK | Input link |
| `ZNAM` | STRING(26) | Zero state name (e.g., "Off") |
| `ONAM` | STRING(26) | One state name (e.g., "On") |
| `ZSV` | MENU | Zero state severity |
| `OSV` | MENU | One state severity |
| `COSV` | MENU | Change of state severity |
| `MASK` | ULONG | Hardware mask |

```
record(bi, "$(P):DoorOpen") {
    field(DESC, "Door interlock")
    field(INP,  "$(P):HW:DoorSw")
    field(ZNAM, "Closed")
    field(ONAM, "Open")
    field(ZSV,  "NO_ALARM")
    field(OSV,  "MAJOR")
    field(SCAN, "1 second")
}
```

### 4.4 bo -- Binary Output

Writes a two-state value. Supports HIGH field for momentary/timed output.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | ENUM | Output state (0 or 1) |
| `OUT` | OUTLINK | Output link |
| `DOL` | INLINK | Desired output link |
| `OMSL` | MENU | Output mode: `"supervisory"`, `"closed_loop"` |
| `ZNAM` | STRING(26) | Zero state name |
| `ONAM` | STRING(26) | One state name |
| `ZSV` | MENU | Zero state severity |
| `OSV` | MENU | One state severity |
| `HIGH` | DOUBLE | Seconds to hold high (0 = permanent) |
| `IVOA` | MENU | Invalid output action |
| `IVOV` | USHORT | Invalid output value |

```
record(bo, "$(P):ShutterCtrl") {
    field(DESC, "Shutter control")
    field(OUT,  "$(P):HW:Shutter PP")
    field(ZNAM, "Close")
    field(ONAM, "Open")
    field(PINI, "YES")
}
```

### 4.5 mbbi -- Multi-Bit Binary Input

Reads an enumerated value with up to 16 states.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | ENUM | Current state index (0-15) |
| `INP` | INLINK | Input link |
| `NOBT` | USHORT | Number of bits |
| `SHFT` | USHORT | Shift (bit offset) |
| `ZRST`..`FFST` | STRING(26) | State 0-15 strings |
| `ZRVL`..`FFVL` | ULONG | State 0-15 raw values |
| `ZRSV`..`FFSV` | MENU | State 0-15 alarm severities |
| `UNSV` | MENU | Unknown state severity |
| `COSV` | MENU | Change of state severity |

State name fields: `ZRST` (0), `ONST` (1), `TWST` (2), `THST` (3), `FRST` (4), `FVST` (5), `SXST` (6), `SVST` (7), `EIST` (8), `NIST` (9), `TEST` (10), `ELST` (11), `TVST` (12), `TTST` (13), `FTST` (14), `FFST` (15).

State value fields: `ZRVL` (0), `ONVL` (1), `TWVL` (2), `THVL` (3), `FRVL` (4), `FVVL` (5), `SXVL` (6), `SVVL` (7), `EIVL` (8), `NIVL` (9), `TEVL` (10), `ELVL` (11), `TVVL` (12), `TTVL` (13), `FTVL` (14), `FFVL` (15).

State severity fields: `ZRSV` (0), `ONSV` (1), `TWSV` (2), `THSV` (3), `FRSV` (4), `FVSV` (5), `SXSV` (6), `SVSV` (7), `EISV` (8), `NISV` (9), `TESV` (10), `ELSV` (11), `TVSV` (12), `TTSV` (13), `FTSV` (14), `FFSV` (15).

```
record(mbbi, "$(P):Status") {
    field(DESC, "Device status")
    field(INP,  "$(P):HW:StatusReg")
    field(ZRST, "Idle")
    field(ONST, "Running")
    field(TWST, "Paused")
    field(THST, "Error")
    field(ZRSV, "NO_ALARM")
    field(ONSV, "NO_ALARM")
    field(TWSV, "MINOR")
    field(THSV, "MAJOR")
    field(SCAN, "1 second")
}
```

### 4.6 mbbo -- Multi-Bit Binary Output

Writes an enumerated value with up to 16 states. Same state fields as mbbi, plus:

| Field | Type | Description |
|-------|------|-------------|
| `OUT` | OUTLINK | Output link |
| `DOL` | INLINK | Desired output link |
| `OMSL` | MENU | Output mode select |
| `IVOA` | MENU | Invalid output action |
| `IVOV` | USHORT | Invalid output value |

### 4.7 mbbiDirect / mbboDirect -- Multi-Bit Binary Direct

Access individual bits (B0-B1F, 32 bits total) as separate fields. Used for register-level bit access.

**mbbiDirect key fields:** `INP`, `NOBT`, `SHFT`, `VAL` (DBF_LONG), `B0`..`B1F` (UCHAR each).
**mbboDirect key fields:** `OUT`, `DOL`, `OMSL`, `NOBT`, `SHFT`, `VAL` (DBF_LONG), `B0`..`B1F` (UCHAR each).

### 4.8 longin -- Long Integer Input

Reads a 32-bit integer value. Supports alarm limits.

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | LONG | Current value |
| `INP` | INLINK | Input link |
| `EGU` | STRING(16) | Engineering units |
| `HOPR` | LONG | High operating range |
| `LOPR` | LONG | Low operating range |

Alarm fields: HIHI, HIGH, LOW, LOLO (LONG type), HHSV, HSV, LSV, LLSV, HYST, ADEL, MDEL.

### 4.9 longout -- Long Integer Output

Writes a 32-bit integer. Similar to ao but with LONG fields.

**Key fields:** `VAL` (LONG), `OUT`, `DOL`, `OMSL`, `EGU`, `DRVH`, `DRVL`, `IVOA`, `IVOV` (LONG).

### 4.10 int64in / int64out -- 64-bit Integer I/O

Same as longin/longout but with `DBF_INT64` value and limit fields. Use for values exceeding 32-bit range.

### 4.11 stringin -- String Input

Reads a string value (max 40 characters).

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | STRING(40) | Current string value |
| `INP` | INLINK | Input link |

### 4.12 stringout -- String Output

Writes a string value (max 40 characters).

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | STRING(40) | Output string value |
| `OUT` | OUTLINK | Output link |
| `DOL` | INLINK | Desired output link |
| `OMSL` | MENU | Output mode select |

### 4.13 lsi -- Long String Input

Like stringin but supports strings longer than 40 characters.

| Field | Type | Description |
|-------|------|-------------|
| `SIZV` | USHORT | Size of VAL buffer (default 41) |
| `INP` | INLINK | Input link |
| `LEN` | ULONG | Length of last string read |

### 4.14 lso -- Long String Output

Like stringout but supports long strings.

| Field | Type | Description |
|-------|------|-------------|
| `SIZV` | USHORT | Size of VAL buffer (default 41) |
| `OUT` | OUTLINK | Output link |
| `DOL` | INLINK | Desired output link |
| `OMSL` | MENU | Output mode select |

### 4.15 calc -- Calculation

Evaluates an infix expression with up to 21 input variables (A-U).

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | DOUBLE | Result of calculation |
| `CALC` | STRING(160) | Infix expression (must be valid, default "0") |
| `INPA`..`INPU` | INLINK | Input links for variables A-U |
| `A`..`U` | DOUBLE | Input variable values |
| `PREC` | SHORT | Display precision |
| `EGU` | STRING(16) | Engineering units |

Alarm fields: same as ai.

**Calc expression operators:** `+`, `-`, `*`, `/`, `%` (modulo), `**` (power), `ABS`, `SQR`, `SQRT`, `CEIL`, `FLOOR`, `NINT`, `MIN`, `MAX`, `LOG`, `LOGE` (ln), `LN` (ln), `EXP`, `SIN`, `COS`, `TAN`, `ASIN`, `ACOS`, `ATAN`, `ATAN2`, `SINH`, `COSH`, `TANH`, `!` (logical NOT), `~` (bitwise NOT), `<<`, `>>`, `&` (AND), `|` (OR), `^` (XOR), `&&`, `||`, `?:` (ternary), `<`, `<=`, `>`, `>=`, `=` or `==` (equal), `!=`, `;` (separator -- both sides evaluated, right value used), `FINITE`, `ISINF`, `ISNAN`, `D2R`, `R2D`, `RNDM` (random 0-1), `A:=expr` (assign to variable).

```
record(calc, "$(P):Average") {
    field(DESC, "Average of two inputs")
    field(CALC, "(A+B)/2")
    field(INPA, "$(P):Input1 CPP MS")
    field(INPB, "$(P):Input2 CPP MS")
    field(EGU,  "V")
    field(PREC, "3")
}
```

### 4.16 calcout -- Calculation Output

Like calc but with an output link. Adds conditional output and output calculation.

**Additional fields beyond calc:**

| Field | Type | Description |
|-------|------|-------------|
| `OUT` | OUTLINK | Output link |
| `OOPT` | MENU | Output execute option: `"Every Time"`, `"On Change"`, `"When Zero"`, `"When Non-zero"`, `"Transition To Zero"`, `"Transition To Non-zero"` |
| `DOPT` | MENU | Output data option: `"Use CALC"` (send VAL), `"Use OCAL"` (send OVAL) |
| `OCAL` | STRING(160) | Output calculation expression |
| `OVAL` | DOUBLE | Output value (result of OCAL) |
| `ODLY` | DOUBLE | Output delay (seconds) |
| `IVOA` | MENU | Invalid output action |
| `IVOV` | DOUBLE | Invalid output value |

```
record(calcout, "$(P):ConditionalWrite") {
    field(CALC, "A>B")
    field(INPA, "$(P):Value CPP")
    field(INPB, "$(P):Threshold")
    field(OOPT, "When Non-zero")
    field(DOPT, "Use OCAL")
    field(OCAL, "A")
    field(OUT,  "$(P):Target PP")
}
```

### 4.17 sub -- Subroutine

Calls a C function with 21 double inputs (A-U). Function names set at load time.

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | DOUBLE | Return value |
| `INAM` | STRING(40) | Init function name |
| `SNAM` | STRING(40) | Process function name |
| `INPA`..`INPU` | INLINK | Input links |
| `A`..`U` | DOUBLE | Input values |
| `BRSV` | MENU | Bad return severity |

Requires matching `function()` declarations in a `.dbd` file:
```
function(mySubInit)
function(mySubProcess)
```

### 4.18 aSub -- Array Subroutine

Like sub but supports typed arrays for both inputs and outputs. 21 input channels (A-U) and 21 output channels (VALA-VALU).

**Key fields:**

| Field | Type | Description |
|-------|------|-------------|
| `INAM` | STRING(41) | Init function name |
| `SNAM` | STRING(41) | Process function name |
| `ONAM` | STRING(41) | Output function name (called after SNAM) |
| `LFLG` | MENU | Link flag: `"IGNORE"`, `"READ"` (whether to read SUBL to get SNAM) |
| `EFLG` | MENU | Event flag: `"NEVER"`, `"ON CHANGE"`, `"ALWAYS"` (monitor posting for outputs) |
| `BRSV` | MENU | Bad return severity |
| `FTA`..`FTU` | MENU | Input A-U type: `"STRING"`, `"CHAR"`, `"UCHAR"`, `"SHORT"`, `"USHORT"`, `"LONG"`, `"ULONG"`, `"INT64"`, `"UINT64"`, `"FLOAT"`, `"DOUBLE"`, `"ENUM"` |
| `NOA`..`NOU` | ULONG | Input A-U max elements (default 1) |
| `NEA`..`NEU` | ULONG | Input A-U actual elements |
| `INPA`..`INPU` | INLINK | Input links |
| `FTVA`..`FTVU` | MENU | Output VALA-VALU type |
| `NOVA`..`NOVU` | ULONG | Output VALA-VALU max elements (default 1) |
| `NEVA`..`NEVU` | ULONG | Output VALA-VALU actual elements |
| `OUTA`..`OUTU` | OUTLINK | Output links |

```
record(aSub, "$(P):ArrayProcess") {
    field(SNAM, "myArrayFunc")
    field(FTA,  "DOUBLE")
    field(NOA,  "1024")
    field(INPA, "$(P):Waveform CPP")
    field(FTVA, "DOUBLE")
    field(NOVA, "1024")
    field(OUTA, "$(P):Result PP")
    field(EFLG, "ON CHANGE")
}
```

### 4.19 waveform -- Waveform (Array Input)

Stores a one-dimensional array.

| Field | Type | Description |
|-------|------|-------------|
| `INP` | INLINK | Input link |
| `FTVL` | MENU | Field type of value: `"STRING"`, `"CHAR"`, `"UCHAR"`, `"SHORT"`, `"USHORT"`, `"LONG"`, `"ULONG"`, `"INT64"`, `"UINT64"`, `"FLOAT"`, `"DOUBLE"`, `"ENUM"` |
| `NELM` | ULONG | Number of elements (max capacity) |
| `NORD` | ULONG | Number of elements read (actual count) |
| `PREC` | SHORT | Display precision |
| `EGU` | STRING(16) | Engineering units |
| `HOPR` | DOUBLE | High operating range |
| `LOPR` | DOUBLE | Low operating range |
| `MPST` | MENU | Post monitors: `"Always"`, `"On Change"` |
| `APST` | MENU | Post archive monitors: `"Always"`, `"On Change"` |

```
record(waveform, "$(P):Spectrum") {
    field(DESC, "FFT spectrum")
    field(FTVL, "DOUBLE")
    field(NELM, "2048")
    field(INP,  "$(P):HW:ADC")
    field(EGU,  "counts")
    field(SCAN, "1 second")
}
```

**Long string using waveform** (for strings > 40 chars):
```
record(waveform, "$(P):LongMessage") {
    field(FTVL, "CHAR")
    field(NELM, "256")
}
```

### 4.20 aai -- Array Analog Input

Similar to waveform. Same key fields: `INP`, `FTVL`, `NELM`, `NORD`, `PREC`, `EGU`.

### 4.21 aao -- Array Analog Output

Array output record.

| Field | Type | Description |
|-------|------|-------------|
| `OUT` | OUTLINK | Output link |
| `DOL` | INLINK | Desired output link |
| `OMSL` | MENU | Output mode select |
| `FTVL` | MENU | Element type |
| `NELM` | ULONG | Max elements |
| `NORD` | ULONG | Actual elements |

### 4.22 seq -- Sequence

Processes up to 16 output links in sequence with delays between each.

| Field | Type | Description |
|-------|------|-------------|
| `SELM` | MENU | Select mechanism: `"All"`, `"Specified"`, `"Mask"` |
| `SELN` | USHORT | Selection number (for Specified/Mask) |
| `SELL` | INLINK | Selection link (reads into SELN) |
| `OFFS` | SHORT | Selection offset |
| `DLY0`..`DLY9`, `DLYA`..`DLYF` | DOUBLE | Delays before each output (seconds) |
| `DOL0`..`DOL9`, `DOLA`..`DOLF` | INLINK | Data input links |
| `DO0`..`DO9`, `DOA`..`DOF` | DOUBLE | Data values |
| `LNK0`..`LNK9`, `LNKA`..`LNKF` | OUTLINK | Output links |

```
record(seq, "$(P):StartupSequence") {
    field(SELM, "All")
    field(DOL0, "1")
    field(LNK0, "$(P):Step1 PP")
    field(DLY1, "2.0")
    field(DOL1, "1")
    field(LNK1, "$(P):Step2 PP")
    field(DLY2, "1.0")
    field(DOL2, "1")
    field(LNK2, "$(P):Step3 PP")
}
```

### 4.23 fanout -- Fanout

Processes up to 16 records (forward links only, no data).

| Field | Type | Description |
|-------|------|-------------|
| `SELM` | MENU | Select mechanism: `"All"`, `"Specified"`, `"Mask"` |
| `SELN` | USHORT | Selection number |
| `SELL` | INLINK | Selection link |
| `LNK0`..`LNK9`, `LNKA`..`LNKF` | FWDLINK | Forward links |

```
record(fanout, "$(P):ProcessAll") {
    field(SELM, "All")
    field(LNK0, "$(P):Record1")
    field(LNK1, "$(P):Record2")
    field(LNK2, "$(P):Record3")
    field(SCAN, "1 second")
}
```

### 4.24 dfanout -- Data Fanout

Distributes a single value to up to 8 output links.

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | DOUBLE | Value to distribute |
| `DOL` | INLINK | Data input link |
| `OMSL` | MENU | Output mode select |
| `OUTA`..`OUTH` | OUTLINK | Output links (8 total) |
| `SELM` | MENU | Select: `"All"`, `"Specified"`, `"Mask"` |

### 4.25 sel -- Select

Selects one value from up to 12 inputs.

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | DOUBLE | Selected value |
| `SELM` | MENU | Select mechanism: `"Specified"`, `"High Signal"`, `"Low Signal"`, `"Median Signal"` |
| `SELN` | USHORT | Selection number (for Specified mode) |
| `NVL` | INLINK | Link to read SELN |
| `INPA`..`INPL` | INLINK | 12 input links |
| `A`..`L` | DOUBLE | Input values |

### 4.26 compress -- Compress / Circular Buffer

Stores a circular buffer of values, optionally with N-to-1 compression.

| Field | Type | Description |
|-------|------|-------------|
| `INP` | INLINK | Input link |
| `ALG` | MENU | Algorithm: `"N to 1 Low Value"`, `"N to 1 High Value"`, `"N to 1 Average"`, `"Average"`, `"Circular Buffer"`, `"N to 1 Median"` |
| `NSAM` | ULONG | Number of samples (buffer size) |
| `N` | ULONG | N-to-1 compression ratio |
| `ILIL` | DOUBLE | Init low interest limit |
| `IHIL` | DOUBLE | Init high interest limit |
| `RES` | SHORT | Reset (write 1 to clear buffer) |

```
record(compress, "$(P):History") {
    field(INP,  "$(P):Value CP")
    field(ALG,  "Circular Buffer")
    field(NSAM, "3600")
}
```

### 4.27 histogram -- Histogram

Accumulates a histogram of input values.

| Field | Type | Description |
|-------|------|-------------|
| `SVL` | INLINK | Signal value link |
| `NELM` | USHORT | Number of bins |
| `ULIM` | DOUBLE | Upper limit |
| `LLIM` | DOUBLE | Lower limit |
| `CMD` | MENU | Command: `"Read"`, `"Clear"`, `"Start"`, `"Stop"` |

### 4.28 event -- Event

Posts a named event that can trigger Event-scanned records.

| Field | Type | Description |
|-------|------|-------------|
| `VAL` | STRING(40) | Event name to post |
| `INP` | INLINK | Input link |

### 4.29 printf -- Printf

Formats a string from up to 10 inputs using a printf-style format string.

| Field | Type | Description |
|-------|------|-------------|
| `FMT` | STRING(81) | Format string |
| `OUT` | OUTLINK | Output link for result string |
| `SIZV` | USHORT | Size of output buffer (default 41) |
| `INP0`..`INP9` | INLINK | Input links |

### 4.30 subArray -- Sub-Array

Extracts a subset of elements from an array source.

| Field | Type | Description |
|-------|------|-------------|
| `INP` | INLINK | Input array link |
| `FTVL` | MENU | Element type |
| `MALM` | ULONG | Maximum array length |
| `NELM` | ULONG | Number of elements to extract |
| `INDX` | ULONG | Starting index |

---

## 5. Common Patterns

### 5.1 Alarm Configuration

```
record(ai, "$(P):Value") {
    field(HIHI, "95")
    field(HIGH, "80")
    field(LOW,  "20")
    field(LOLO, "5")
    field(HHSV, "MAJOR")
    field(HSV,  "MINOR")
    field(LSV,  "MINOR")
    field(LLSV, "MAJOR")
    field(HYST, "1.0")
}
```

### 5.2 Processing Chain with FLNK

```
record(ai, "$(P):RawValue") {
    field(SCAN, "1 second")
    field(FLNK, "$(P):Processed")
}
record(calc, "$(P):Processed") {
    field(CALC, "A*0.001+B")
    field(INPA, "$(P):RawValue NPP NMS")
    field(INPB, "$(P):Offset NPP NMS")
    field(FLNK, "$(P):Archived")
}
record(compress, "$(P):Archived") {
    field(INP,  "$(P):Processed NPP NMS")
    field(ALG,  "Circular Buffer")
    field(NSAM, "3600")
}
```

### 5.3 Timestamp Propagation

To propagate the timestamp from a source record to a downstream record:

```
record(calc, "$(P):Derived") {
    field(INPA, "$(P):Source NPP NMS")
    field(CALC, "A*2")
    field(TSEL, "$(P):Source.TIME")
}
```

### 5.4 Self-Referencing Counter

```
record(calc, "$(P):Counter") {
    field(SCAN, "1 second")
    field(CALC, "A+1")
    field(INPA, "$(P):Counter")
}
```

### 5.5 Output Record with PINI

```
record(ao, "$(P):Setpoint") {
    field(VAL,  "50.0")
    field(PINI, "YES")
    field(OUT,  "$(P):HW:SP PP")
    field(EGU,  "degC")
    field(PREC, "1")
    field(DRVH, "100")
    field(DRVL, "0")
}
```

### 5.6 Periodic Scan with I/O Intr

```
record(ai, "$(P):AsyncInput") {
    field(DTYP, "myDriver")
    field(INP,  "@channel1")
    field(SCAN, "I/O Intr")
    field(EGU,  "V")
    field(PREC, "3")
}
```

### 5.7 Template with Substitutions

**motor.template:**
```
record(ao, "$(P)$(M):SetPos") {
    field(OUT,  "$(PORT):pos PP")
    field(EGU,  "$(EGU=mm)")
    field(PREC, "$(PREC=3)")
    field(DRVH, "$(DRVH)")
    field(DRVL, "$(DRVL)")
}
record(ai, "$(P)$(M):GetPos") {
    field(INP,  "$(PORT):rbv CP MS")
    field(EGU,  "$(EGU=mm)")
    field(PREC, "$(PREC=3)")
    field(SCAN, "I/O Intr")
}
```

**motors.substitutions:**
```
file "db/motor.template" {
    pattern { P,     M,    PORT,      DRVH,  DRVL }
    { "BL1:", "m1",  "MC1:Axis1", "100", "-100" }
    { "BL1:", "m2",  "MC1:Axis2", "50",  "0"    }
    { "BL1:", "m3",  "MC1:Axis3", "200", "-200" }
}
```

---

## 6. Key Rules and Pitfalls

1. **Record names must be unique** within an IOC and should not exceed 60 characters.
2. **String fields have fixed maximum sizes**: most are 40 characters (stringin/stringout VAL), EGU is 16, state strings (ZNAM, ONAM, ZRST-FFST) are 26. Use lsi/lso or waveform with FTVL=CHAR for longer strings.
3. **CALC must always contain a valid expression** -- even if unused, use `"0"` as default.
4. **CP and CPP are only valid on input links** (INP, INPA-INPU, etc.), never on output links.
5. **FLNK does not use link modifiers** -- just specify the target record name.
6. **Output records in closed_loop mode** (`OMSL = "closed_loop"`) read their DOL link each time they process.
7. **PINI="YES" processes the record once during IOC initialization** -- useful for output records to push initial values to hardware.
8. **SCAN="I/O Intr" requires device support** that implements `get_ioint_info`.
9. **Monitor deadband (MDEL)** controls when CA monitors fire. Set to 0 for every-change notification. Set to -1 to suppress all monitors of value changes.
10. **Archive deadband (ADEL)** is separate from MDEL and controls archive event posting.
11. **For aSub records**, set `FTx` and `NOx` fields BEFORE loading. They cannot be changed at runtime. The `SNAM` function name CAN be changed at runtime.
12. **Macro defaults** -- use `$(MACRO=default)` syntax, not conditional logic. If a macro is not provided and has no default, dbLoadRecords will print a warning and substitute an empty string.
