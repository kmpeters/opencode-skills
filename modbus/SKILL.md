---
name: modbus
description: Configure EPICS Modbus IOCs for PLC and device communication -- register map translation, drvModbusAsynConfigure, data types, function codes, database templates, substitution files, and TCP/serial/RTU/ASCII setup
---

# Modbus Skill

You are an expert at configuring EPICS Modbus IOCs. The EPICS modbus module provides generic Modbus protocol support that is used directly -- no custom C++ driver code is needed. Your task is to translate hardware register maps into the correct combination of communication port configuration, modbus port drivers, and database records.

---

## 1. Workflow Overview

Configuring a Modbus device for EPICS follows this sequence:

1. **Read the device register map** from the hardware documentation
2. **Create a communication port** (TCP/IP, UDP, serial RTU, or serial ASCII)
3. **Add the modbus interpose layer** for protocol framing
4. **Create modbus port drivers** -- one per contiguous address range and function code
5. **Write substitution files** selecting the right template for each register
6. **Write the st.cmd** tying everything together

---

## 2. Communication Port Setup

### 2.1 TCP/IP

```
drvAsynIPPortConfigure("PLC1", "192.168.1.100:502", 0, 0, 0)
asynSetOption("PLC1", 0, "disconnectOnReadTimeout", "Y")
modbusInterposeConfig("PLC1", 0, 5000, 0)
```

- Port 502 is the standard Modbus TCP port.
- `disconnectOnReadTimeout` = `"Y"` is recommended for TCP to detect connection loss.
- `modbusInterposeConfig` linkType `0` = TCP.

### 2.2 UDP/IP

```
drvAsynIPPortConfigure("DEV1", "192.168.1.100:502 UDP", 0, 0, 0)
modbusInterposeConfig("DEV1", 3, 5000, 0)
```

- Add `" UDP"` after the port number in the hostInfo string.
- `modbusInterposeConfig` linkType `3` = UDP.

### 2.3 Serial RTU

```
drvAsynSerialPortConfigure("PLC1", "/dev/ttyUSB0", 0, 0, 0)
asynSetOption("PLC1", 0, "baud", "9600")
asynSetOption("PLC1", 0, "bits", "8")
asynSetOption("PLC1", 0, "parity", "none")
asynSetOption("PLC1", 0, "stop", "1")
modbusInterposeConfig("PLC1", 1, 2000, 0)
```

- `modbusInterposeConfig` linkType `1` = RTU.
- The last argument (`writeDelayMsec`) may need to be non-zero for some serial devices.

### 2.4 Serial ASCII

```
drvAsynSerialPortConfigure("PLC1", "/dev/ttyUSB0", 0, 0, 0)
asynSetOption("PLC1", 0, "baud", "9600")
asynSetOption("PLC1", 0, "bits", "7")
asynSetOption("PLC1", 0, "parity", "even")
asynSetOption("PLC1", 0, "stop", "1")
asynOctetSetOutputEos("PLC1", 0, "\r\n")
asynOctetSetInputEos("PLC1", 0, "\r\n")
modbusInterposeConfig("PLC1", 2, 2000, 0)
```

- `modbusInterposeConfig` linkType `2` = ASCII.
- EOS must be set for ASCII framing.

---

## 3. modbusInterposeConfig

```
modbusInterposeConfig(portName, linkType, timeoutMsec, writeDelayMsec)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `portName` | string | Name of the asyn IP or serial port (NOT the modbus port) |
| `linkType` | int | `0` = TCP, `1` = RTU, `2` = ASCII, `3` = UDP |
| `timeoutMsec` | int | Read/write timeout in milliseconds (0 = default 2000ms) |
| `writeDelayMsec` | int | Delay before each write (typically 0; non-zero for some serial devices) |

---

## 4. drvModbusAsynConfigure -- Creating Modbus Port Drivers

```
drvModbusAsynConfigure(portName, tcpPortName, slaveAddress, modbusFunction,
                       modbusStartAddress, modbusLength, dataType, pollMsec, plcType)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `portName` | string | Unique name for this modbus port (used in database records) |
| `tcpPortName` | string | Name of the underlying asyn IP/serial port |
| `slaveAddress` | int | Modbus slave address (0-247; 0 for TCP unit identifier) |
| `modbusFunction` | int | Modbus function code (see Section 5) |
| `modbusStartAddress` | int | Starting Modbus address (0-65535, or -1 for absolute addressing) |
| `modbusLength` | int | Number of bits (FC 1,2,5,15) or 16-bit words (FC 3,4,6,16,23) to read/write |
| `dataType` | int/string | Default data type for this port (see Section 6). Use 0 for default (UINT16) |
| `pollMsec` | int | Polling period in ms for read functions. For write functions: non-zero = read once at startup for initial values |
| `plcType` | string | PLC type string (e.g., `"Koyo"`, `"Modicon"`, `"Wago"`, `"Simulator"`) |

### 4.1 Key Design Principle

Each `drvModbusAsynConfigure` call creates one modbus port that maps to one contiguous range of Modbus addresses with one function code. You typically need multiple ports per device:

- One port per register range (e.g., inputs at address 0, outputs at address 100)
- Separate read and write ports for read-write registers (e.g., FC3 to read, FC16 to write holding registers)
- Separate ports for bit access vs word access to the same addresses

### 4.2 Example: PLC with Discrete I/O and Holding Registers

```
# Read 32 discrete inputs starting at address 0 (FC2)
drvModbusAsynConfigure("DI_Bits", "PLC1", 1, 2, 0, 32, 0, 100, "MyPLC")

# Read 16 coils starting at address 0 (FC1) -- coil readback
drvModbusAsynConfigure("Coils_In", "PLC1", 1, 1, 0, 16, 0, 100, "MyPLC")

# Write single coils starting at address 0 (FC5)
drvModbusAsynConfigure("Coils_Out", "PLC1", 1, 5, 0, 16, 0, 1, "MyPLC")

# Read 20 holding registers starting at address 100 (FC3)
drvModbusAsynConfigure("HR_In", "PLC1", 1, 3, 100, 20, 0, 100, "MyPLC")

# Write holding registers starting at address 100 (FC16)
drvModbusAsynConfigure("HR_Out", "PLC1", 1, 16, 100, 20, 0, 1, "MyPLC")

# Read 10 input registers starting at address 0 (FC4)
drvModbusAsynConfigure("IR_In", "PLC1", 1, 4, 0, 10, 0, 100, "MyPLC")
```

---

## 5. Modbus Function Codes

| FC | Name | Access | Data Type | Read/Write | Notes |
|----|------|--------|-----------|------------|-------|
| 1 | Read Coils | Bit | Coils (read-write bits) | Read | Read back coil states |
| 2 | Read Discrete Inputs | Bit | Discrete inputs (read-only bits) | Read | Digital input status |
| 3 | Read Holding Registers | Word | Holding registers (read-write) | Read | Most common for PLC data |
| 4 | Read Input Registers | Word | Input registers (read-only) | Read | Sensor/ADC values |
| 5 | Write Single Coil | Bit | Coils | Write | Write one bit at a time |
| 6 | Write Single Register | Word | Holding registers | Write | Write one 16-bit word |
| 15 | Write Multiple Coils | Bit | Coils | Write | Write array of bits |
| 16 | Write Multiple Registers | Word | Holding registers | Write | Write array of words (atomic) |
| 17 | Report Slave ID | Byte | -- | Read | Device identification |
| 23 | Read/Write Multiple Registers | Word | Holding registers | Both | Simultaneous read and write |

**Pseudo function codes:**
- `123` = FC23 read-only (use when you only want to read with FC23)
- `223` = FC23 write-only (use when you only want to write with FC23)

### 5.1 Choosing Between FC6 and FC16 for Writes

- **FC6** writes a single 16-bit register per transaction. For 32-bit or 64-bit data types, it requires multiple transactions, creating a brief period of inconsistent data.
- **FC16** writes multiple registers atomically in one transaction. **Always prefer FC16** for multi-register data types (INT32, FLOAT32, INT64, FLOAT64).
- FC6 is fine for single 16-bit values (INT16, UINT16, BCD).

### 5.2 Choosing Between FC1 and FC2 for Bit Reads

- **FC1** reads coils (read-write bits). Use to read back the state of outputs.
- **FC2** reads discrete inputs (read-only bits). Use for input-only digital signals.

---

## 6. Data Types

The `dataType` parameter in `drvModbusAsynConfigure` sets the default for the port. Individual records can override it via the drvUser field in their link.

### 6.1 16-bit Types (1 register)

| Data Type | String | Description |
|-----------|--------|-------------|
| 0 | `UINT16` | Unsigned 16-bit integer (default) |
| 1 | `INT16SM` | Sign + magnitude 16-bit (bit 15 = sign, bits 0-14 = magnitude) |
| 2 | `BCD_UNSIGNED` | 4-digit unsigned BCD (0-9999) |
| 3 | `BCD_SIGNED` | 4-digit signed BCD (sign in high nibble) |
| 4 | `INT16` | Signed 16-bit integer (two's complement) |
| 5 | `UINT16` | Unsigned 16-bit integer |

### 6.2 32-bit Types (2 registers)

| Data Type | String | Word Order | Byte Order |
|-----------|--------|------------|------------|
| 5 | `INT32_LE` | Low word first | Bytes swapped within each word |
| 6 | `INT32_LE_BS` | Low word first | Natural little-endian byte order |
| 7 | `INT32_BE` | High word first | Natural big-endian byte order |
| 8 | `INT32_BE_BS` | High word first | Bytes swapped within each word |
| 9 | `UINT32_LE` | Low word first | Bytes swapped within each word |
| 10 | `UINT32_LE_BS` | Low word first | Natural little-endian byte order |
| 11 | `UINT32_BE` | High word first | Natural big-endian byte order |
| 12 | `UINT32_BE_BS` | High word first | Bytes swapped within each word |
| 17 | `FLOAT32_LE` | Low word first | Bytes swapped within each word |
| 18 | `FLOAT32_LE_BS` | Low word first | Natural little-endian byte order |
| 19 | `FLOAT32_BE` | High word first | Natural big-endian byte order |
| 20 | `FLOAT32_BE_BS` | High word first | Bytes swapped within each word |

### 6.3 64-bit Types (4 registers)

| Data Type | String | Word Order | Byte Order |
|-----------|--------|------------|------------|
| 13 | `INT64_LE` | Low word first | Bytes swapped within each word |
| 14 | `INT64_LE_BS` | Low word first | Natural little-endian byte order |
| 15 | `INT64_BE` | High word first | Natural big-endian byte order |
| 16 | `INT64_BE_BS` | High word first | Bytes swapped within each word |
| 21 | `FLOAT64_LE` | Low word first | Bytes swapped within each word |
| 22 | `FLOAT64_LE_BS` | Low word first | Natural little-endian byte order |
| 23 | `FLOAT64_BE` | High word first | Natural big-endian byte order |
| 24 | `FLOAT64_BE_BS` | High word first | Bytes swapped within each word |

UINT64 variants follow the same pattern.

### 6.4 String Types (N registers)

| Data Type | String | Description |
|-----------|--------|-------------|
| 25 | `STRING_HIGH` | 1 char per register (high byte) |
| 26 | `STRING_LOW` | 1 char per register (low byte) |
| 27 | `STRING_HIGH_LOW` | 2 chars per register (high byte first) |
| 28 | `STRING_LOW_HIGH` | 2 chars per register (low byte first) |
| 29 | `ZSTRING_HIGH` | Like STRING_HIGH but writes null terminator |
| 30 | `ZSTRING_LOW` | Like STRING_LOW but writes null terminator |
| 31 | `ZSTRING_HIGH_LOW` | Like STRING_HIGH_LOW but writes null terminator |
| 32 | `ZSTRING_LOW_HIGH` | Like STRING_LOW_HIGH but writes null terminator |

Use `ZSTRING_*` variants for output records. Use `STRING_*` for input records.

### 6.5 Determining the Correct Byte Order

Most PLCs use big-endian byte order (`_BE`). If a 32-bit float register reads as a garbage value, try the other byte orders. Common conventions:

- **Modicon/Schneider**: Big-endian (`_BE`)
- **Allen-Bradley/Rockwell**: Big-endian (`_BE`)
- **Siemens S7**: Big-endian (`_BE`)
- **Wago**: Little-endian (`_LE`)
- **Many FPGA-based devices**: Little-endian (`_LE_BS`)

When unsure, read a known value (e.g., 1.0 as FLOAT32) and try all four variants until the value reads correctly.

---

## 7. Database Template Reference

### 7.1 Template Selection Guide

**For discrete (bit) access -- FC 1, 2, 5, 15:**

| Register Type | Direction | Template | Key Macros |
|---------------|-----------|----------|------------|
| Single coil/input bit | Read | `bi_bit.template` | PORT, OFFSET, ZNAM, ONAM, ZSV, OSV, SCAN |
| Single coil bit | Write | `bo_bit.template` | PORT, OFFSET, ZNAM, ONAM |
| 16-bit word of bits | Read | `mbbiDirect.template` | PORT, OFFSET, MASK, SCAN |
| 16-bit word of bits | Write | `mbboDirect.template` | PORT, OFFSET, MASK |
| Array of bits | Read | `intarray_in.template` | PORT, NELM, SCAN |
| Array of bits | Write | `intarray_out.template` | PORT, NELM |

**For register (word) access -- FC 3, 4, 6, 16, 23:**

| Register Type | Direction | Template | Key Macros |
|---------------|-----------|----------|------------|
| 16-bit integer (raw) | Read | `longin.template` | PORT, OFFSET, SCAN |
| 16-bit integer (raw) | Write | `longout.template` | PORT, OFFSET |
| Any integer with DATA_TYPE | Read | `longinInt32.template` | PORT, OFFSET, DATA_TYPE, SCAN |
| Any integer with DATA_TYPE | Write | `longoutInt32.template` | PORT, OFFSET, DATA_TYPE, PINI |
| 64-bit integer | Read | `int64in.template` | PORT, OFFSET, DATA_TYPE, SCAN |
| 64-bit integer | Write | `int64out.template` | PORT, OFFSET, DATA_TYPE |
| Analog with LINEAR conversion | Read | `ai.template` | PORT, OFFSET, BITS, EGUL, EGUF, PREC, SCAN |
| Analog with LINEAR conversion | Write | `ao.template` | PORT, OFFSET, BITS, EGUL, EGUF, PREC |
| Analog averaging | Read | `ai_average.template` | PORT, OFFSET, BITS, EGUL, EGUF, PREC, SCAN |
| Float/any via Float64 | Read | `aiFloat64.template` | PORT, OFFSET, DATA_TYPE, HOPR, LOPR, PREC, SCAN |
| Float/any via Float64 | Write | `aoFloat64.template` | PORT, OFFSET, DATA_TYPE, HOPR, LOPR, PREC |
| Bit within word | Read | `bi_word.template` | PORT, OFFSET, MASK, ZNAM, ONAM, ZSV, OSV, SCAN |
| Bit within word | Write | `bo_word.template` | PORT, OFFSET, MASK, ZNAM, ONAM |
| String | Read | `stringin.template` | PORT, OFFSET, DATA_TYPE, SCAN |
| String | Write | `stringout.template` | PORT, OFFSET, DATA_TYPE, INITIAL_READBACK |
| Long string | Read | `stringWaveformIn.template` | PORT, OFFSET, DATA_TYPE, NELM, SCAN |
| Long string | Write | `stringWaveformOut.template` | PORT, OFFSET, DATA_TYPE, NELM, INITIAL_READBACK |
| Int32 array | Read | `intarray_in.template` | PORT, NELM, SCAN |
| Int32 array | Write | `intarray_out.template` | PORT, NELM |
| Float64 array | Read | `floatarray_in.template` | PORT, NELM, SCAN |
| Float64 array | Write | `floatarray_out.template` | PORT, NELM |

**Auxiliary templates:**

| Template | Purpose | Key Macros |
|----------|---------|------------|
| `statistics.template` | I/O stats: ReadOK, WriteOK, IOErrors, histogram | P, R, PORT, SCAN |
| `poll_delay.template` | Control poller thread delay | P, R, PORT |
| `poll_trigger.template` | Trigger a single poll cycle | P, R, PORT |
| `asynRecord.template` | asyn debugging/trace interface | P, R, PORT, ADDR, TMOD, IFACE |

### 7.2 Common Macro Parameters

| Macro | Description |
|-------|-------------|
| `P` | PV prefix (e.g., `"PLC1:"`) |
| `R` | Record name suffix. Full PV name = `$(P)$(R)` |
| `PORT` | Modbus port name (from `drvModbusAsynConfigure`) |
| `OFFSET` | Register offset relative to `modbusStartAddress` (0-based) |
| `SCAN` | Scan rate: `"I/O Intr"` for polled inputs, `"1 second"` for averaging |
| `BITS` | Number of bits for analog conversion. Positive = unipolar, negative = bipolar (e.g., `12` = 0-4095, `-12` = -2048 to 2047) |
| `EGUL` | Engineering units low value (maps to raw 0 or -2^(BITS-1)) |
| `EGUF` | Engineering units full-scale value (maps to raw 2^BITS-1 or 2^(BITS-1)-1) |
| `PREC` | Display precision (decimal places) |
| `DATA_TYPE` | Modbus data type string (e.g., `"FLOAT32_BE"`, `"INT32_LE"`) |
| `MASK` | Bit mask for `bi_word`/`bo_word` (e.g., `0x0001` for bit 0, `0x0080` for bit 7) |
| `ZNAM` / `ONAM` | State names for bi/bo records |
| `ZSV` / `OSV` | Alarm severities for bi zero/one states |
| `NELM` | Number of elements for waveform/array records |
| `INITIAL_READBACK` | `0` or `1` -- whether to read current value from device at startup for output string records |
| `PINI` | `"YES"` or `"NO"` -- process at init for output records |

---

## 8. OFFSET Semantics

The `OFFSET` macro in database records specifies the position within the address range defined by `drvModbusAsynConfigure`.

### 8.1 Bit Access (FC 1, 2, 5, 15)

`OFFSET` is in **bits** relative to `modbusStartAddress`:

```
# Port reads 32 coils starting at address 100
drvModbusAsynConfigure("Coils", "PLC1", 1, 1, 100, 32, 0, 100, "MyPLC")

# OFFSET=0 → Modbus address 100 (first coil)
# OFFSET=7 → Modbus address 107 (eighth coil)
# OFFSET=31 → Modbus address 131 (last coil)
```

### 8.2 Word Access (FC 3, 4, 6, 16, 23)

`OFFSET` is in **16-bit words** relative to `modbusStartAddress`:

```
# Port reads 20 registers starting at address 100
drvModbusAsynConfigure("HR", "PLC1", 1, 3, 100, 20, 0, 100, "MyPLC")

# OFFSET=0 → Modbus address 100 (first register)
# OFFSET=5 → Modbus address 105 (sixth register)
```

For 32-bit data types, the value occupies `OFFSET` and `OFFSET+1`. For 64-bit, it occupies `OFFSET` through `OFFSET+3`. Ensure the port's `modbusLength` is large enough.

### 8.3 Absolute Addressing

Set `modbusStartAddress = -1` to use absolute Modbus addresses in OFFSET:

```
drvModbusAsynConfigure("AbsPort", "PLC1", 1, 3, -1, 100, 0, 100, "MyPLC")
# Now OFFSET=400 reads Modbus address 400 directly
```

### 8.4 Octal Addresses

Addresses can be specified in octal (leading zero), decimal, or hex. Octal is common in PLC documentation:

```
# Octal: 04000 = decimal 2048
drvModbusAsynConfigure("Bits", "PLC1", 0, 2, 04000, 040, 0, 100, "Koyo")
```

---

## 9. Link Format

### 9.1 asynUInt32Digital (for bi_bit, bo_bit, bi_word, bo_word, mbbiDirect, mbboDirect, longin, longout)

```
field(INP, "@asynMask($(PORT) $(OFFSET) $(MASK))")
field(OUT, "@asynMask($(PORT) $(OFFSET) $(MASK))")
```

The mask determines which bits are relevant. For `bi_bit`/`bo_bit`, mask is `0x1`. For `longin`/`longout`, mask is `0xFFFF`.

### 9.2 asynInt32 / asynInt64 / asynFloat64 (for longinInt32, longoutInt32, int64in, int64out, aiFloat64, aoFloat64)

```
field(INP, "@asyn($(PORT) $(OFFSET))$(DATA_TYPE)")
field(OUT, "@asyn($(PORT) $(OFFSET))$(DATA_TYPE)")
```

The `DATA_TYPE` string (e.g., `FLOAT32_BE`) overrides the port's default data type.

### 9.3 asynInt32 with asynMask (for ai, ao with LINEAR conversion)

```
field(INP, "@asynMask($(PORT) $(OFFSET) $(BITS))MODBUS_DATA")
field(OUT, "@asynMask($(PORT) $(OFFSET) $(BITS))MODBUS_DATA")
```

`BITS` specifies the ADC/DAC resolution for the LINEAR conversion. Positive = unipolar, negative = bipolar.

---

## 10. Complete st.cmd Example

```bash
< envPaths

dbLoadDatabase("../../dbd/myModbusApp.dbd")
myModbusApp_registerRecordDeviceDriver(pdbbase)

# ---- Communication Port ----
drvAsynIPPortConfigure("PLC1", "192.168.1.100:502", 0, 0, 0)
asynSetOption("PLC1", 0, "disconnectOnReadTimeout", "Y")
modbusInterposeConfig("PLC1", 0, 5000, 0)

# ---- Modbus Port Drivers ----
# Discrete inputs: 32 bits at address 0 (FC2)
drvModbusAsynConfigure("DI",   "PLC1", 1, 2,  0,  32, 0, 100, "MyPLC")

# Coils: read 16 bits at address 0 (FC1), write single (FC5)
drvModbusAsynConfigure("DO_R", "PLC1", 1, 1,  0,  16, 0, 100, "MyPLC")
drvModbusAsynConfigure("DO_W", "PLC1", 1, 5,  0,  16, 0,   1, "MyPLC")

# Holding registers: read 40 words at address 100 (FC3), write (FC16)
drvModbusAsynConfigure("HR_R", "PLC1", 1, 3,  100, 40, 0, 100, "MyPLC")
drvModbusAsynConfigure("HR_W", "PLC1", 1, 16, 100, 40, 0,   1, "MyPLC")

# Input registers: read 10 words at address 0 (FC4), 32-bit float big-endian
drvModbusAsynConfigure("IR",   "PLC1", 1, 4,  0,  20, 19, 100, "MyPLC")

# ---- Trace (optional, for debugging) ----
asynSetTraceIOMask("PLC1", 0, 4)

# ---- Load Records ----
dbLoadTemplate("myPLC.substitutions")

iocInit
```

---

## 11. Complete Substitution File Example

```
# Discrete inputs (DI0-DI7)
file "$(MODBUS)/db/bi_bit.template" { pattern
{P,       R,       PORT,  OFFSET,  ZNAM,    ONAM,   ZSV,        OSV,     SCAN}
{PLC1:,   DI0,     DI,    0,       Off,     On,     NO_ALARM,   MAJOR,   "I/O Intr"}
{PLC1:,   DI1,     DI,    1,       Off,     On,     NO_ALARM,   MAJOR,   "I/O Intr"}
{PLC1:,   DI2,     DI,    2,       Off,     On,     NO_ALARM,   MAJOR,   "I/O Intr"}
{PLC1:,   DI3,     DI,    3,       Off,     On,     NO_ALARM,   MAJOR,   "I/O Intr"}
}

# Coil outputs (DO0-DO3)
file "$(MODBUS)/db/bo_bit.template" { pattern
{P,       R,       PORT,  OFFSET,  ZNAM,    ONAM}
{PLC1:,   DO0,     DO_W,  0,       Off,     On}
{PLC1:,   DO1,     DO_W,  1,       Off,     On}
{PLC1:,   DO2,     DO_W,  2,       Off,     On}
{PLC1:,   DO3,     DO_W,  3,       Off,     On}
}

# Coil readback
file "$(MODBUS)/db/bi_bit.template" { pattern
{P,       R,         PORT,  OFFSET,  ZNAM,   ONAM,  ZSV,       OSV,     SCAN}
{PLC1:,   DO0_RBV,   DO_R,  0,       Off,    On,    NO_ALARM,  NO_ALARM, "I/O Intr"}
{PLC1:,   DO1_RBV,   DO_R,  1,       Off,    On,    NO_ALARM,  NO_ALARM, "I/O Intr"}
}

# Holding register -- 16-bit integer setpoint + readback
file "$(MODBUS)/db/longoutInt32.template" { pattern
{P,       R,            PORT,  OFFSET,  DATA_TYPE,  PINI}
{PLC1:,   Setpoint1,    HR_W,  0,       INT16,      YES}
}
file "$(MODBUS)/db/longinInt32.template" { pattern
{P,       R,              PORT,  OFFSET,  DATA_TYPE,  SCAN}
{PLC1:,   Setpoint1_RBV,  HR_R,  0,       INT16,      "I/O Intr"}
}

# Holding register -- 32-bit float setpoint + readback
file "$(MODBUS)/db/aoFloat64.template" { pattern
{P,       R,            PORT,  OFFSET,  DATA_TYPE,    PREC}
{PLC1:,   TempSP,       HR_W,  10,      FLOAT32_BE,   2}
}
file "$(MODBUS)/db/aiFloat64.template" { pattern
{P,       R,              PORT,  OFFSET,  DATA_TYPE,    PREC,  SCAN}
{PLC1:,   TempSP_RBV,    HR_R,  10,      FLOAT32_BE,   2,     "I/O Intr"}
}

# Input register -- analog with LINEAR conversion (12-bit bipolar ADC)
file "$(MODBUS)/db/ai.template" { pattern
{P,       R,         PORT,  OFFSET,  BITS,  EGUL,    EGUF,   PREC,  SCAN}
{PLC1:,   ADC1,      IR,    0,       -12,   -10.0,   10.0,   3,     "I/O Intr"}
{PLC1:,   ADC2,      IR,    1,       -12,   -10.0,   10.0,   3,     "I/O Intr"}
}

# Input register -- 32-bit float read (using Float64 interface)
file "$(MODBUS)/db/aiFloat64.template" { pattern
{P,       R,           PORT,  OFFSET,  DATA_TYPE,    PREC,  SCAN}
{PLC1:,   Pressure,    IR,    4,       FLOAT32_BE,   4,     "I/O Intr"}
{PLC1:,   Flow,        IR,    6,       FLOAT32_BE,   2,     "I/O Intr"}
}

# Bit within a holding register word
file "$(MODBUS)/db/bi_word.template" { pattern
{P,       R,           PORT,  OFFSET,  MASK,    ZNAM,     ONAM,     ZSV,       OSV,     SCAN}
{PLC1:,   Status0,     HR_R,  20,      0x0001,  Normal,   Fault,    NO_ALARM,  MAJOR,   "I/O Intr"}
{PLC1:,   Status1,     HR_R,  20,      0x0002,  Normal,   Fault,    NO_ALARM,  MAJOR,   "I/O Intr"}
{PLC1:,   Status2,     HR_R,  20,      0x0004,  Normal,   Fault,    NO_ALARM,  MINOR,   "I/O Intr"}
}

# Diagnostics
file "$(MODBUS)/db/statistics.template" { pattern
{P,       R,       PORT,   SCAN}
{PLC1:,   DI_,     DI,     "10 second"}
{PLC1:,   HR_,     HR_R,   "10 second"}
}
file "$(MODBUS)/db/poll_delay.template" { pattern
{P,       R,              PORT}
{PLC1:,   DIPollDelay,    DI}
{PLC1:,   HRPollDelay,    HR_R}
}
file "$(ASYN)/db/asynRecord.db" { pattern
{P,       R,           PORT,   ADDR,  IMAX,  OMAX}
{PLC1:,   OctetAsyn,   PLC1,   0,     80,    80}
}
```

---

## 12. Makefile for a Modbus IOC

```makefile
# In src/Makefile:
PROD_IOC = myModbusApp

DBD += myModbusApp.dbd
myModbusApp_DBD += base.dbd
myModbusApp_DBD += modbusSupport.dbd
myModbusApp_DBD += asyn.dbd
myModbusApp_DBD += drvAsynIPPort.dbd
myModbusApp_DBD += drvAsynSerialPort.dbd

myModbusApp_SRCS += myModbusApp_registerRecordDeviceDriver.cpp
myModbusApp_SRCS_DEFAULT += myModbusAppMain.cpp
myModbusApp_SRCS_vxWorks += -nil-

myModbusApp_LIBS += modbus
myModbusApp_LIBS += asyn
myModbusApp_LIBS += $(EPICS_BASE_IOC_LIBS)
```

```makefile
# In configure/RELEASE:
MODBUS = /path/to/modbus
ASYN   = /path/to/asyn
EPICS_BASE = /path/to/base
```

---

## 13. Key Rules and Pitfalls

1. **Read and write ports must share the same TCP socket** (same `tcpPortName`). Write-only ports that don't share a socket will time out because the PLC closes idle TCP connections.

2. **Use FC16 (not FC6) for multi-register writes.** FC6 writes one register at a time, creating transient incorrect values for 32-bit and 64-bit types.

3. **OFFSET is relative** to `modbusStartAddress`, not an absolute Modbus address (unless `modbusStartAddress = -1`).

4. **For 32-bit data types, OFFSET points to the first of two registers.** Ensure `modbusLength` covers both registers (e.g., if OFFSET=10 for FLOAT32, `modbusLength` must be at least 12).

5. **`pollMsec` for write ports** should be non-zero (e.g., 1) if you want initial readback of current values at IOC startup. Set to 0 to disable polling entirely for write-only ports.

6. **Input records should use `SCAN = "I/O Intr"`** for polled registers. The modbus poller thread automatically triggers I/O Intr processing after each poll cycle.

7. **The `BITS` macro in `ai.template` / `ao.template`** controls the LINEAR conversion range. `BITS=12` means unipolar 12-bit (0-4095). `BITS=-12` means bipolar 12-bit (-2048 to 2047). The LINR field is set to LINEAR, and EGUL/EGUF map to the raw range limits.

8. **Byte order is the most common source of errors** for multi-register types. If a FLOAT32 reads as garbage, try all four variants (`_BE`, `_BE_BS`, `_LE`, `_LE_BS`) until the value is correct.

9. **`asynUInt32Digital` does NOT apply data type conversions.** It always treats registers as unsigned 16-bit integers. Use `asynInt32` or `asynFloat64` interfaces for data type conversion.

10. **Wago PLCs** require `plcType` containing `"Wago"` (case-sensitive). This adds a 0x200 offset for readback addresses on write function codes.

11. **String data types** specify how characters are packed into 16-bit registers. `STRING_HIGH_LOW` = 2 chars per register, high byte first (most common). Try different variants if strings appear garbled.

12. **One modbus port per contiguous address range.** Do not create a single port spanning addresses 0-1000 if you only need registers at 0-10 and 500-510 -- this would waste bandwidth reading 490 unused registers every poll cycle.
