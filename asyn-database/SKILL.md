---
name: asyn-database
description: Write EPICS database files (.db) for asyn drivers -- DTYP choices, INP/OUT link format, setpoint/readback patterns, I/O Intr scanning, and array records
---

# asyn Database Skill

You are an expert at writing EPICS database records that connect to asyn port drivers. You understand the asyn INST_IO link format, all asyn DTYP choices, and the standard patterns for setpoint/readback record pairs.

---

## 1. INP/OUT Link Format

All asyn device support uses INST_IO links with this format:

```
field(INP, "@asyn(portName, addr, timeout)drvInfoString")
field(OUT, "@asyn(portName, addr, timeout)drvInfoString")
```

| Component | Description | Default |
|-----------|-------------|---------|
| `portName` | asyn port name (from configure command) | Required |
| `addr` | Device address (0 for single-device ports) | 0 |
| `timeout` | I/O timeout in seconds | 1.0 |
| `drvInfoString` | Parameter name string (maps to `createParam()` in driver) | Required |

The `addr` and `timeout` can be omitted:

```
"@asyn(PORT)PARAM_NAME"                     # addr=0, timeout=1.0
"@asyn(PORT, 0)PARAM_NAME"                  # timeout=1.0
"@asyn(PORT, 0, 1.0)PARAM_NAME"             # fully specified
```

With macros (most common):

```
"@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))$(PARAM)"
```

---

## 2. DTYP Reference

### 2.1 asynInt32 -- 32-bit Integer

| Record Type | DTYP | Direction |
|-------------|------|-----------|
| ai | `"asynInt32"` | Input |
| ai | `"asynInt32Average"` | Input (averaging) |
| ao | `"asynInt32"` | Output |
| bi | `"asynInt32"` | Input |
| bo | `"asynInt32"` | Output |
| mbbi | `"asynInt32"` | Input |
| mbbo | `"asynInt32"` | Output |
| longin | `"asynInt32"` | Input |
| longout | `"asynInt32"` | Output |

### 2.2 asynInt64 -- 64-bit Integer

| Record Type | DTYP | Direction |
|-------------|------|-----------|
| int64in | `"asynInt64"` | Input |
| int64out | `"asynInt64"` | Output |
| longin | `"asynInt64"` | Input (truncated to 32-bit) |
| longout | `"asynInt64"` | Output (extended to 64-bit) |
| ai | `"asynInt64"` | Input |
| ao | `"asynInt64"` | Output |

### 2.3 asynFloat64 -- 64-bit Float

| Record Type | DTYP | Direction |
|-------------|------|-----------|
| ai | `"asynFloat64"` | Input |
| ai | `"asynFloat64Average"` | Input (averaging) |
| ao | `"asynFloat64"` | Output |

### 2.4 asynUInt32Digital -- Bit-Masked Digital

| Record Type | DTYP | Direction |
|-------------|------|-----------|
| bi | `"asynUInt32Digital"` | Input |
| bo | `"asynUInt32Digital"` | Output |
| longin | `"asynUInt32Digital"` | Input |
| longout | `"asynUInt32Digital"` | Output |
| mbbi | `"asynUInt32Digital"` | Input |
| mbbo | `"asynUInt32Digital"` | Output |
| mbbiDirect | `"asynUInt32Digital"` | Input |
| mbboDirect | `"asynUInt32Digital"` | Output |

**Note:** For bi/bo the `MASK` field is set automatically from `ZRVL`/`ONVL`. For mbbi/mbbo/mbbiDirect/mbboDirect, `NOBT` and `SHFT` control the mask. For longin/longout, the full 32-bit value is used.

### 2.5 asynOctet -- String/Binary

| Record Type | DTYP | Direction | Behavior |
|-------------|------|-----------|----------|
| stringin | `"asynOctetRead"` | Input | Read string on process |
| stringin | `"asynOctetCmdResponse"` | Input | Write AOUT then read |
| stringin | `"asynOctetWriteRead"` | Input | Write AOUT then read |
| stringout | `"asynOctetWrite"` | Output | Write string |
| waveform | `"asynOctetRead"` | Input | Read into char array |
| waveform | `"asynOctetCmdResponse"` | Input | Write then read |
| waveform | `"asynOctetWriteRead"` | Input | Write then read |
| waveform | `"asynOctetWrite"` | Output | Write from char array |
| waveform | `"asynOctetWriteBinary"` | Output | Write binary (no EOS) |
| lsi | `"asynOctetRead"` | Input | Read long string |
| lsi | `"asynOctetCmdResponse"` | Input | Write then read long string |
| lsi | `"asynOctetWriteRead"` | Input | Write then read long string |
| lso | `"asynOctetWrite"` | Output | Write long string |
| printf | `"asynOctetWrite"` | Output | Formatted write |
| scalcout | `"asynOctetWrite"` | Output | String calc output write |

**`asynOctetCmdResponse` vs `asynOctetWriteRead`:** Both write a string then read a response. `CmdResponse` writes the `AOUT` field, while `WriteRead` writes the `AOUT` field. They differ in how `AOUT` is set; in practice they behave similarly.

### 2.6 Array Types

| Record Type | DTYP | Direction |
|-------------|------|-----------|
| waveform | `"asynInt8ArrayIn"` | Input |
| waveform | `"asynInt8ArrayOut"` | Output |
| waveform | `"asynInt16ArrayIn"` | Input |
| waveform | `"asynInt16ArrayOut"` | Output |
| waveform | `"asynInt32ArrayIn"` | Input |
| waveform | `"asynInt32ArrayOut"` | Output |
| waveform | `"asynInt64ArrayIn"` | Input |
| waveform | `"asynInt64ArrayOut"` | Output |
| waveform | `"asynFloat32ArrayIn"` | Input |
| waveform | `"asynFloat32ArrayOut"` | Output |
| waveform | `"asynFloat64ArrayIn"` | Input |
| waveform | `"asynFloat64ArrayOut"` | Output |
| aai | `"asynXxxArrayIn"` | Input (same DTYPs as waveform) |
| aao | `"asynXxxArrayOut"` | Output (same DTYPs as waveform) |

### 2.7 Time Series

| Record Type | DTYP | Direction |
|-------------|------|-----------|
| waveform | `"asynInt32TimeSeries"` | Input |
| waveform | `"asynInt64TimeSeries"` | Input |
| waveform | `"asynFloat64TimeSeries"` | Input |

---

## 3. Standard Record Patterns

### 3.1 Output with Readback (Setpoint/RBV Pair)

The most common pattern: an output record for the setpoint and an input record for the readback. Both use the same drvInfo string.

```
record(ao, "$(P)$(R)Voltage") {
    field(DESC, "Voltage setpoint")
    field(DTYP, "asynFloat64")
    field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))VOLTAGE")
    field(EGU,  "V")
    field(PREC, "3")
    field(DRVH, "10.0")
    field(DRVL, "0.0")
    field(PINI, "YES")
}

record(ai, "$(P)$(R)Voltage_RBV") {
    field(DESC, "Voltage readback")
    field(DTYP, "asynFloat64")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))VOLTAGE")
    field(EGU,  "V")
    field(PREC, "3")
    field(SCAN, "I/O Intr")
}
```

**Convention:** Readback records use the suffix `_RBV` and `SCAN = "I/O Intr"`.

### 3.2 Boolean Output with Readback

```
record(bo, "$(P)$(R)Enable") {
    field(DTYP, "asynInt32")
    field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))ENABLE")
    field(ZNAM, "Disable")
    field(ONAM, "Enable")
    field(PINI, "YES")
}

record(bi, "$(P)$(R)Enable_RBV") {
    field(DTYP, "asynInt32")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))ENABLE")
    field(ZNAM, "Disabled")
    field(ONAM, "Enabled")
    field(SCAN, "I/O Intr")
}
```

### 3.3 Enumeration (mbbo/mbbi)

```
record(mbbo, "$(P)$(R)Mode") {
    field(DTYP, "asynInt32")
    field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))MODE")
    field(ZRST, "Single")
    field(ONST, "Continuous")
    field(TWST, "External")
    field(PINI, "YES")
}

record(mbbi, "$(P)$(R)Mode_RBV") {
    field(DTYP, "asynInt32")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))MODE")
    field(ZRST, "Single")
    field(ONST, "Continuous")
    field(TWST, "External")
    field(SCAN, "I/O Intr")
}
```

### 3.4 Integer Output with Readback

```
record(longout, "$(P)$(R)NumSamples") {
    field(DTYP, "asynInt32")
    field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))NUM_SAMPLES")
    field(PINI, "YES")
}

record(longin, "$(P)$(R)NumSamples_RBV") {
    field(DTYP, "asynInt32")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))NUM_SAMPLES")
    field(SCAN, "I/O Intr")
}
```

### 3.5 Read-Only Status

```
record(ai, "$(P)$(R)Temperature_RBV") {
    field(DTYP, "asynFloat64")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))TEMPERATURE")
    field(EGU,  "degC")
    field(PREC, "1")
    field(SCAN, "I/O Intr")
}
```

### 3.6 Waveform (Array Data)

```
record(waveform, "$(P)$(R)Waveform_RBV") {
    field(DTYP, "asynFloat64ArrayIn")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))WAVEFORM")
    field(FTVL, "DOUBLE")
    field(NELM, "$(NELM=2048)")
    field(SCAN, "I/O Intr")
}
```

### 3.7 String Parameter

```
record(stringout, "$(P)$(R)FilePath") {
    field(DTYP, "asynOctetWrite")
    field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))FILE_PATH")
    field(PINI, "YES")
}

record(stringin, "$(P)$(R)FilePath_RBV") {
    field(DTYP, "asynOctetRead")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))FILE_PATH")
    field(SCAN, "I/O Intr")
}
```

For strings longer than 40 characters, use waveform with CHAR:

```
record(waveform, "$(P)$(R)FilePath") {
    field(DTYP, "asynOctetWrite")
    field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))FILE_PATH")
    field(FTVL, "CHAR")
    field(NELM, "256")
    field(PINI, "YES")
}
```

Or use lsi/lso for long strings (Base 3.15+):

```
record(lso, "$(P)$(R)FilePath") {
    field(DTYP, "asynOctetWrite")
    field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))FILE_PATH")
    field(SIZV, "256")
    field(PINI, "YES")
}
```

### 3.8 asynRecord for Diagnostics

```
record(asyn, "$(P)$(R)AsynIO") {
    field(DTYP, "asynRecordDevice")
    field(PORT, "$(PORT)")
    field(ADDR, "$(ADDR=0)")
    field(OMAX, "256")
    field(IMAX, "256")
}
```

The asynRecord provides a generic interface for interactive serial/IP communication, trace control, and port diagnostics via operator screens.

---

## 4. Multi-Address Devices

For drivers with `ASYN_MULTIDEVICE`, the `addr` in the link selects the sub-device:

```
record(ai, "$(P)$(R)Ch0:Value") {
    field(DTYP, "asynFloat64")
    field(INP,  "@asyn($(PORT),0,$(TIMEOUT=1))VALUE")
    field(SCAN, "I/O Intr")
}

record(ai, "$(P)$(R)Ch1:Value") {
    field(DTYP, "asynFloat64")
    field(INP,  "@asyn($(PORT),1,$(TIMEOUT=1))VALUE")
    field(SCAN, "I/O Intr")
}
```

Use substitutions for multiple channels:

```
file "db/channel.template" {
    pattern { P, R, PORT, ADDR }
    { "SYS:", "Dev:", "PORT1", "0" }
    { "SYS:", "Dev:", "PORT1", "1" }
    { "SYS:", "Dev:", "PORT1", "2" }
}
```

---

## 5. Key Rules and Pitfalls

1. **`SCAN = "I/O Intr"` on readback records** is the standard pattern. The driver calls `callParamCallbacks()` to trigger processing.

2. **Use `PINI = "YES"` on output records** to push initial values to the driver at IOC startup.

3. **The drvInfo string must match exactly** what was passed to `createParam()` in the driver. It is case-sensitive.

4. **`DTYP` must match the asyn interface the driver registers.** If the driver uses `asynParamFloat64`, use `"asynFloat64"`. If it uses `asynParamInt32`, use `"asynInt32"`.

5. **For analog records (ai/ao) with `"asynInt32"`**, the raw integer is placed in `RVAL` and converted via `LINR`/`ESLO`/`EOFF`. With `"asynFloat64"`, the value goes directly to `VAL` (no conversion).

6. **Array FTVL must match the array type.** `"asynFloat64ArrayIn"` requires `FTVL = "DOUBLE"`. `"asynInt32ArrayIn"` requires `FTVL = "LONG"`.

7. **`"asynInt32Average"` and `"asynFloat64Average"`** accumulate values between reads and return the average. Use with periodic scan (not I/O Intr).

8. **The `_RBV` suffix** is a widely-followed convention but not enforced. Output records write to the driver; `_RBV` records read back the current state.

9. **Port name and address are usually passed as macros** (`$(PORT)`, `$(ADDR=0)`, `$(TIMEOUT=1)`) to make templates reusable.

10. **For `asynUInt32Digital` records**, the mask is derived from the record's `MASK` field (bi/bo) or `NOBT`/`SHFT` fields (mbbi/mbbo). The link format does NOT include a mask.
