---
name: asyn-port-config
description: Configure asyn ports in EPICS IOC startup scripts (st.cmd) -- IP, serial, and server ports, serial options, EOS settings, trace control, and diagnostic commands
---

# asyn Port Configuration Skill

You are an expert at configuring asyn communication ports in EPICS IOC startup scripts (st.cmd). You understand TCP/IP, serial, and server port drivers, serial port options, end-of-string handling, and asyn trace/debug facilities.

---

## 1. IP Port Configuration

### 1.1 TCP Client Port

```
drvAsynIPPortConfigure("PORT1", "192.168.1.100:5025", 0, 0, 0)
```

Parameters:
| # | Name | Description |
|---|------|-------------|
| 1 | portName | Unique asyn port name |
| 2 | hostInfo | `"host:port [protocol]"` |
| 3 | priority | Thread priority (0 = default) |
| 4 | noAutoConnect | 0 = auto-connect, 1 = manual connect |
| 5 | noProcessEos | 0 = process EOS, 1 = raw binary mode |

### 1.2 Protocol Specifiers

The `hostInfo` string format is `"hostname:port [protocol]"`:

| Example | Protocol |
|---------|----------|
| `"192.168.1.100:5025"` | TCP (default) |
| `"192.168.1.100:5025 TCP"` | TCP (explicit) |
| `"192.168.1.100:5025 UDP"` | UDP |
| `"192.168.1.100:5025 UDP*"` | UDP broadcast |
| `"192.168.1.100:5025 COM"` | UDP broadcast (alias) |
| `"192.168.1.100:80 HTTP"` | HTTP |

### 1.3 TCP Server Port

```
drvAsynIPServerPortConfigure("SERVER1", "0.0.0.0:9001", 5, 0, 0, 0)
```

Parameters:
| # | Name | Description |
|---|------|-------------|
| 1 | portName | Unique asyn port name |
| 2 | serverInfo | `"addr:port [protocol]"` |
| 3 | maxClients | Maximum simultaneous clients |
| 4 | priority | Thread priority (0 = default) |
| 5 | noAutoConnect | 0 = auto-connect |
| 6 | noProcessEos | 0 = process EOS |

---

## 2. Serial Port Configuration

### 2.1 Creating a Serial Port

```
drvAsynSerialPortConfigure("SERIAL1", "/dev/ttyS0", 0, 0, 0)
```

Parameters:
| # | Name | Description |
|---|------|-------------|
| 1 | portName | Unique asyn port name |
| 2 | ttyName | OS device name (e.g., `/dev/ttyS0`, `/dev/ttyUSB0`, `COM1`) |
| 3 | priority | Thread priority (0 = default) |
| 4 | noAutoConnect | 0 = auto-connect |
| 5 | noProcessEos | 0 = process EOS |

### 2.2 Serial Port Options

After creating the port, configure serial parameters with `asynSetOption`:

```
asynSetOption("SERIAL1", 0, "baud",    "9600")
asynSetOption("SERIAL1", 0, "bits",    "8")
asynSetOption("SERIAL1", 0, "parity",  "none")
asynSetOption("SERIAL1", 0, "stop",    "1")
asynSetOption("SERIAL1", 0, "clocal",  "Y")
asynSetOption("SERIAL1", 0, "crtscts", "N")
```

### 2.3 All Serial Option Keys

| Key | Values | Default | Description |
|-----|--------|---------|-------------|
| `baud` | 300, 600, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 576000, 921600, 1152000 | 9600 | Baud rate |
| `bits` | 5, 6, 7, 8 | 8 | Data bits |
| `parity` | `none`, `even`, `odd` | `none` | Parity |
| `stop` | 1, 2 | 1 | Stop bits |
| `clocal` | `Y`, `N` | `Y` | Ignore modem status lines |
| `crtscts` | `Y`, `N` | `N` | Hardware flow control (RTS/CTS) |
| `ixon` | `Y`, `N` | `N` | Software flow control (XON/XOFF on output) |
| `ixoff` | `Y`, `N` | `N` | Software flow control (XON/XOFF on input) |
| `ixany` | `Y`, `N` | `N` | Any character restarts output |
| `rs485_enable` | `Y`, `N` | `N` | RS-485 mode (Linux only) |
| `rs485_rts_on_send` | `Y`, `N` | -- | RTS high during send |
| `rs485_rts_after_send` | `Y`, `N` | -- | RTS high after send |
| `rs485_delay_rts_before_send` | milliseconds | -- | Delay before sending |
| `rs485_delay_rts_after_send` | milliseconds | -- | Delay after sending |

---

## 3. End-of-String (EOS) Configuration

### 3.1 Setting EOS

```
asynOctetSetInputEos("PORT1", 0, "\r\n")
asynOctetSetOutputEos("PORT1", 0, "\r\n")
```

Parameters: `(portName, addr, eosString)`

Common EOS settings:

| EOS | Escape | Typical Use |
|-----|--------|-------------|
| `"\n"` | Linefeed | Unix-style terminals |
| `"\r\n"` | CR+LF | SCPI instruments, Telnet |
| `"\r"` | Carriage return | Some serial devices |
| `"\003"` | ETX (0x03) | Some protocols |

### 3.2 Querying EOS

```
asynOctetGetInputEos("PORT1", 0)
asynOctetGetOutputEos("PORT1", 0)
```

---

## 4. Trace and Debug Control

### 4.1 Trace Masks

```
asynSetTraceMask("PORT1", 0, mask)
```

Trace mask values (OR together for multiple):

| Mask | Value | Hex | What It Shows |
|------|-------|-----|---------------|
| `ASYN_TRACE_ERROR` | 1 | 0x01 | Error messages (on by default) |
| `ASYN_TRACEIO_DEVICE` | 2 | 0x02 | Device-level I/O data |
| `ASYN_TRACEIO_FILTER` | 4 | 0x04 | Filter/interpose layer I/O |
| `ASYN_TRACEIO_DRIVER` | 8 | 0x08 | Low-level driver I/O |
| `ASYN_TRACE_FLOW` | 16 | 0x10 | Control flow/call trace |
| `ASYN_TRACE_WARNING` | 32 | 0x20 | Warnings |

Common combinations:

```
# Errors only (default)
asynSetTraceMask("PORT1", 0, 0x01)

# Errors + device I/O (most useful for debugging)
asynSetTraceMask("PORT1", 0, 0x03)

# Errors + warnings
asynSetTraceMask("PORT1", 0, 0x21)

# Everything
asynSetTraceMask("PORT1", 0, 0x3F)
```

### 4.2 Trace I/O Format

```
asynSetTraceIOMask("PORT1", 0, mask)
```

| Mask | Value | Description |
|------|-------|-------------|
| `ASYN_TRACEIO_NODATA` | 0 | Don't print I/O data |
| `ASYN_TRACEIO_ASCII` | 1 | Print as ASCII text |
| `ASYN_TRACEIO_ESCAPE` | 2 | Print with escape sequences for non-printable chars |
| `ASYN_TRACEIO_HEX` | 4 | Print as hex dump |

```
# ASCII (readable for text protocols)
asynSetTraceIOMask("PORT1", 0, 0x01)

# Escaped (shows \r\n etc.)
asynSetTraceIOMask("PORT1", 0, 0x02)

# Hex dump (for binary protocols)
asynSetTraceIOMask("PORT1", 0, 0x04)
```

### 4.3 Trace Info Mask

```
asynSetTraceInfoMask("PORT1", 0, mask)
```

| Mask | Value | Description |
|------|-------|-------------|
| `ASYN_TRACEINFO_TIME` | 1 | Include timestamp |
| `ASYN_TRACEINFO_PORT` | 2 | Include port name |
| `ASYN_TRACEINFO_SOURCE` | 4 | Include source file:line |
| `ASYN_TRACEINFO_THREAD` | 8 | Include thread name |

```
# Timestamp + port name (most useful)
asynSetTraceInfoMask("PORT1", 0, 0x03)

# All info
asynSetTraceInfoMask("PORT1", 0, 0x0F)
```

### 4.4 Trace to File

```
asynSetTraceFile("PORT1", 0, "/tmp/asyn_trace.log")
asynSetTraceFile("PORT1", 0, "")    # Reset to stderr
```

### 4.5 Truncation Size

```
asynSetTraceIOTruncateSize("PORT1", 0, 256)
```

---

## 5. Connection Management

```
# Wait for connection (with timeout in seconds)
asynWaitConnect("PORT1", 5.0)

# Enable/disable auto-connect
asynAutoConnect("PORT1", 0, 1)    # Enable
asynAutoConnect("PORT1", 0, 0)    # Disable

# Enable/disable the port
asynEnable("PORT1", 0, 1)         # Enable
asynEnable("PORT1", 0, 0)         # Disable
```

---

## 6. Interactive I/O (Diagnostics)

These commands are useful for testing communication from the IOC shell:

```
# Create a named connection
asynOctetConnect("conn1", "PORT1", 0, 1, 80, "")

# Write a string
asynOctetWrite("conn1", "*IDN?")

# Read a response
asynOctetRead("conn1", 200)

# Write then read (write-read)
asynOctetWriteRead("conn1", "*IDN?", 200)

# Flush
asynOctetFlush("conn1")

# Disconnect
asynOctetDisconnect("conn1")
```

---

## 7. Port Report

```
# Report all ports
asynReport(level)

# Report a specific port
asynReport(level, "PORT1")
```

Levels: 0 = summary, 1-2 = increasing detail.

---

## 8. Complete st.cmd Examples

### 8.1 TCP/IP Instrument

```bash
< envPaths
cd "${TOP}"
dbLoadDatabase "dbd/myApp.dbd"
myApp_registerRecordDeviceDriver pdbbase

# Configure TCP port to SCPI instrument
drvAsynIPPortConfigure("INST1", "192.168.1.100:5025", 0, 0, 0)
asynOctetSetInputEos("INST1", 0, "\n")
asynOctetSetOutputEos("INST1", 0, "\n")

# Configure the application driver
myDriverConfigure("DRV1", "INST1")

# Load records
dbLoadRecords("db/myRecords.db", "P=SYS:,R=Dev:,PORT=DRV1")
dbLoadRecords("db/asynRecord.db", "P=SYS:,R=Dev:Asyn,PORT=INST1,ADDR=0,OMAX=256,IMAX=256")

cd "${TOP}/iocBoot/${IOC}"
iocInit
```

### 8.2 Serial Instrument

```bash
< envPaths
cd "${TOP}"
dbLoadDatabase "dbd/myApp.dbd"
myApp_registerRecordDeviceDriver pdbbase

# Configure serial port
drvAsynSerialPortConfigure("SERIAL1", "/dev/ttyUSB0", 0, 0, 0)
asynSetOption("SERIAL1", 0, "baud", "19200")
asynSetOption("SERIAL1", 0, "bits", "8")
asynSetOption("SERIAL1", 0, "parity", "none")
asynSetOption("SERIAL1", 0, "stop", "1")
asynOctetSetInputEos("SERIAL1", 0, "\r\n")
asynOctetSetOutputEos("SERIAL1", 0, "\r\n")

# Enable trace for debugging (comment out for production)
#asynSetTraceMask("SERIAL1", 0, 0x03)
#asynSetTraceIOMask("SERIAL1", 0, 0x02)

# Load records
dbLoadRecords("db/myRecords.db", "P=SYS:,R=Dev:,PORT=SERIAL1,ADDR=0")
dbLoadRecords("db/asynRecord.db", "P=SYS:,R=Dev:Asyn,PORT=SERIAL1,ADDR=0,OMAX=256,IMAX=256")

cd "${TOP}/iocBoot/${IOC}"
iocInit
```

### 8.3 asynPortDriver-Based IOC

```bash
< envPaths
cd "${TOP}"
dbLoadDatabase "dbd/myApp.dbd"
myApp_registerRecordDeviceDriver pdbbase

# Create the port driver instance
myDriverConfigure("DRV1", 1024)

# Load records
dbLoadRecords("db/myDriver.template", "P=SYS:,R=Dev:,PORT=DRV1,ADDR=0,TIMEOUT=1")

cd "${TOP}/iocBoot/${IOC}"
iocInit
```

---

## 9. Makefile Integration

```makefile
# In src/Makefile:
myApp_DBD += asyn.dbd
myApp_DBD += drvAsynIPPort.dbd
myApp_DBD += drvAsynSerialPort.dbd

myApp_LIBS += asyn
```

For GPIB instruments, also add:
```makefile
myApp_DBD += devGpib.dbd
myApp_DBD += drvVxi11.dbd          # For LAN/GPIB gateways
```

---

## 10. Key Rules and Pitfalls

1. **Port configuration must come before `dbLoadRecords`** in st.cmd. Records connect to ports during initialization.

2. **Always set EOS** for text-based protocols. Without it, reads will timeout waiting for the full buffer.

3. **`noProcessEos = 1`** disables the interpose EOS layer. Use this for binary protocols where EOS processing would corrupt data.

4. **`noAutoConnect = 1`** means you must manually connect with `asynAutoConnect` or from the asynRecord. Use this for instruments that should not be connected at startup.

5. **Trace output goes to stderr by default.** Use `asynSetTraceFile` to redirect to a file. Remember to reset it (`""`) when done.

6. **Trace masks are per-port, per-address.** Address -1 applies to all addresses on a port.

7. **The asynRecord is invaluable for debugging.** Load one for each port to enable interactive communication and trace control from operator screens.

8. **For instruments that respond to writes**, the port driver handles the response automatically if the driver is configured for it. You don't typically need `respond2Writes` unless using the devGpib framework.

9. **UDP ports are connectionless.** `auto-connect` and connection callbacks still work but represent the port's readiness, not a physical connection.

10. **VXI-11 configuration** for LAN/GPIB gateways uses `vxi11Configure("portName", "hostname", flags, timeout, "device_name")` where `device_name` is typically `"gpib0"` and `flags` is 0 or the `lock` flag.
