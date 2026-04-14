---
name: asyn-port-driver
description: Write asynPortDriver subclasses in C++ -- parameter library, virtual read/write methods, interface/interrupt masks, background threads, callbacks, and iocsh registration
---

# asynPortDriver Skill

You are an expert at writing EPICS device drivers that inherit from the `asynPortDriver` C++ base class. asynPortDriver provides a parameter library, automatic interface registration, and virtual methods for each data type, making it the standard way to write modern EPICS drivers.

---

## 1. Headers and Linking

```cpp
#include <asynPortDriver.h>

// For specific needs:
#include <epicsThread.h>     // epicsThreadCreate, epicsEventCreate
#include <epicsEvent.h>      // epicsEventSignal, epicsEventWait
```

```makefile
# In src/Makefile:
LIBRARY_IOC += myDriver
myDriver_SRCS += myDriver.cpp
myDriver_LIBS += asyn
myDriver_LIBS += $(EPICS_BASE_IOC_LIBS)

DBD += myDriver.dbd
```

---

## 2. Parameter Types

```cpp
// From asynParamType.h
enum asynParamType {
    asynParamNotDefined,
    asynParamInt32,
    asynParamInt64,
    asynParamUInt32Digital,
    asynParamFloat64,
    asynParamOctet,
    asynParamInt8Array,
    asynParamInt16Array,
    asynParamInt32Array,
    asynParamInt64Array,
    asynParamFloat32Array,
    asynParamFloat64Array,
    asynParamGenericPointer
};
```

---

## 3. Interface and Interrupt Masks

The constructor takes `interfaceMask` and `interruptMask` bitmasks that declare which asyn interfaces the driver supports and which can generate callbacks.

| Constant | Value | Interface |
|----------|-------|-----------|
| `asynCommonMask` | 0x0001 | asynCommon (always included) |
| `asynDrvUserMask` | 0x0002 | asynDrvUser (drvInfo string mapping) |
| `asynOptionMask` | 0x0004 | asynOption (key-value options) |
| `asynInt32Mask` | 0x0008 | asynInt32 (32-bit integer) |
| `asynUInt32DigitalMask` | 0x0010 | asynUInt32Digital (bitmask digital) |
| `asynFloat64Mask` | 0x0020 | asynFloat64 (double) |
| `asynOctetMask` | 0x0040 | asynOctet (string/binary) |
| `asynInt8ArrayMask` | 0x0080 | asynInt8Array |
| `asynInt16ArrayMask` | 0x0100 | asynInt16Array |
| `asynInt32ArrayMask` | 0x0200 | asynInt32Array |
| `asynFloat32ArrayMask` | 0x0400 | asynFloat32Array |
| `asynFloat64ArrayMask` | 0x0800 | asynFloat64Array |
| `asynGenericPointerMask` | 0x1000 | asynGenericPointer |
| `asynEnumMask` | 0x2000 | asynEnum |
| `asynInt64Mask` | 0x4000 | asynInt64 (64-bit integer) |
| `asynInt64ArrayMask` | 0x8000 | asynInt64Array |

**Rule:** The `interruptMask` should include masks for every interface where records use `SCAN = "I/O Intr"`. Typically it matches the `interfaceMask`.

---

## 4. Port Attribute Flags

| Flag | Value | Meaning |
|------|-------|---------|
| `ASYN_CANBLOCK` | 0x0002 | Driver may block (has a port thread for queued I/O) |
| `ASYN_MULTIDEVICE` | 0x0001 | Driver supports multiple addresses (addr > 0) |

Use `ASYN_CANBLOCK` for drivers that do real I/O (network, serial, file). Omit it for purely simulated or computed drivers. Use `ASYN_MULTIDEVICE` when a single port serves multiple logical devices addressed by `addr`.

---

## 5. Constructor Pattern

```cpp
#include <asynPortDriver.h>

// drvInfo parameter name strings (conventions: UPPERCASE_WITH_UNDERSCORES)
#define P_ValueString       "MY_VALUE"
#define P_StatusString      "MY_STATUS"
#define P_WaveformString    "MY_WAVEFORM"
#define P_MessageString     "MY_MESSAGE"

class myDriver : public asynPortDriver {
public:
    myDriver(const char *portName, int maxAddr);
    virtual ~myDriver();

    // Override virtual methods for the types you support
    virtual asynStatus writeInt32(asynUser *pasynUser, epicsInt32 value);
    virtual asynStatus readFloat64(asynUser *pasynUser, epicsFloat64 *value);
    virtual asynStatus readFloat64Array(asynUser *pasynUser,
                                        epicsFloat64 *value, size_t nElements,
                                        size_t *nIn);
    virtual asynStatus readEnum(asynUser *pasynUser, char *strings[],
                                int values[], int severities[],
                                size_t nElements, size_t *nIn);

    // Background task (if needed)
    void pollingTask();

protected:
    // Parameter indices -- set by createParam()
    int P_Value;
    int P_Status;
    int P_Waveform;
    int P_Message;

private:
    epicsEventId pollEventId_;
    double *waveformData_;
    int waveformSize_;
    bool running_;
};
```

### Constructor Implementation

```cpp
myDriver::myDriver(const char *portName, int maxAddr)
    : asynPortDriver(
        portName,                    // Port name
        maxAddr,                     // Max address (1 for single device)
        asynInt32Mask | asynFloat64Mask | asynFloat64ArrayMask |
            asynOctetMask | asynEnumMask | asynDrvUserMask,   // interfaceMask
        asynInt32Mask | asynFloat64Mask | asynFloat64ArrayMask |
            asynOctetMask | asynEnumMask,                     // interruptMask
        ASYN_CANBLOCK,               // asynFlags (ASYN_CANBLOCK, ASYN_MULTIDEVICE)
        1,                           // autoConnect (1 = yes)
        0,                           // priority (0 = default)
        0)                           // stackSize (0 = default)
    , pollEventId_(epicsEventCreate(epicsEventEmpty))
    , waveformData_(NULL)
    , waveformSize_(1024)
    , running_(true)
{
    // Create parameters
    createParam(P_ValueString,    asynParamFloat64,      &P_Value);
    createParam(P_StatusString,   asynParamInt32,         &P_Status);
    createParam(P_WaveformString, asynParamFloat64Array,  &P_Waveform);
    createParam(P_MessageString,  asynParamOctet,         &P_Message);

    // Set initial values
    setDoubleParam(P_Value, 0.0);
    setIntegerParam(P_Status, 0);
    setStringParam(P_Message, "Initialized");

    // Allocate waveform buffer
    waveformData_ = (double *)calloc(waveformSize_, sizeof(double));

    // Spawn background polling thread (if needed)
    epicsThreadCreate("myPolling",
        epicsThreadPriorityMedium,
        epicsThreadGetStackSize(epicsThreadStackMedium),
        (EPICSTHREADFUNC)pollingTaskC, this);
}
```

---

## 6. Parameter Library Methods

### 6.1 Creating Parameters

```cpp
// createParam(drvInfoString, type, &index)
createParam("MY_PARAM", asynParamInt32, &P_MyParam);
```

The `drvInfoString` is what database records use in their INP/OUT link to identify this parameter. The `index` (reason) is set by `createParam` and used internally.

### 6.2 Setting Parameter Values

```cpp
// Scalar types (single address, addr=0 implied)
setIntegerParam(P_MyInt, 42);
setInteger64Param(P_MyInt64, 123456789LL);
setDoubleParam(P_MyDouble, 3.14);
setStringParam(P_MyString, "Hello");
setUIntDigitalParam(P_MyDigital, 0xFF, 0xFF);  // value, mask

// Multi-address variant
setIntegerParam(addr, P_MyInt, 42);
setDoubleParam(addr, P_MyDouble, 3.14);
```

### 6.3 Getting Parameter Values

```cpp
int ival;
getIntegerParam(P_MyInt, &ival);

double dval;
getDoubleParam(P_MyDouble, &dval);

// String -- C string buffer
char sval[256];
getStringParam(P_MyString, sizeof(sval), sval);

// String -- std::string
std::string str;
getStringParam(P_MyString, str);
```

### 6.4 Publishing Updates (Callbacks)

```cpp
// After setting parameter values, call callParamCallbacks to notify
// all registered listeners (records with SCAN = "I/O Intr")
callParamCallbacks();

// Multi-address variant
callParamCallbacks(addr);

// Array callbacks must be called explicitly
doCallbacksFloat64Array(waveformData_, nElements, P_Waveform, addr);
doCallbacksInt32Array(intArrayData, nElements, P_IntArray, addr);
```

**CRITICAL:** `callParamCallbacks()` must be called after any `setXxxParam()` calls for the changes to be seen by I/O Intr-scanned records. Forgetting this is the most common asynPortDriver bug.

### 6.5 Parameter Status and Alarms

```cpp
// Set parameter status (propagates to record alarm)
setParamStatus(P_Value, asynError);       // Sets UDF alarm
setParamStatus(P_Value, asynSuccess);     // Clears alarm

// Set alarm status and severity explicitly
setParamAlarmStatus(P_Value, asynStatus);
setParamAlarmSeverity(P_Value, epicsSevMinor);
```

---

## 7. Virtual Methods to Override

### 7.1 Integer Read/Write

```cpp
asynStatus myDriver::writeInt32(asynUser *pasynUser, epicsInt32 value)
{
    int function = pasynUser->reason;   // Parameter index

    // Call base class first (stores value in parameter library)
    asynStatus status = asynPortDriver::writeInt32(pasynUser, value);

    if (function == P_Run) {
        if (value) epicsEventSignal(pollEventId_);
    }
    else if (function == P_Reset) {
        // ... handle reset ...
    }

    callParamCallbacks();
    return status;
}

asynStatus myDriver::readInt32(asynUser *pasynUser, epicsInt32 *value)
{
    int function = pasynUser->reason;

    if (function == P_LiveCounter) {
        *value = readHardwareCounter();
        setIntegerParam(P_LiveCounter, *value);
    }

    return asynPortDriver::readInt32(pasynUser, value);
}
```

### 7.2 Float64 Read/Write

```cpp
asynStatus myDriver::writeFloat64(asynUser *pasynUser, epicsFloat64 value)
{
    int function = pasynUser->reason;

    if (function == P_UpdateTime) {
        if (value < 0.01) value = 0.01;  // Enforce minimum
    }

    asynStatus status = asynPortDriver::writeFloat64(pasynUser, value);
    callParamCallbacks();
    return status;
}
```

### 7.3 Array Read

```cpp
asynStatus myDriver::readFloat64Array(asynUser *pasynUser,
    epicsFloat64 *value, size_t nElements, size_t *nIn)
{
    int function = pasynUser->reason;

    if (function == P_Waveform) {
        size_t ncopy = (nElements < waveformSize_) ? nElements : waveformSize_;
        memcpy(value, waveformData_, ncopy * sizeof(double));
        *nIn = ncopy;
    }
    return asynSuccess;
}
```

### 7.4 Octet (String) Read/Write

```cpp
asynStatus myDriver::writeOctet(asynUser *pasynUser, const char *value,
    size_t nChars, size_t *nActual)
{
    int function = pasynUser->reason;

    asynStatus status = asynPortDriver::writeOctet(pasynUser, value, nChars, nActual);

    if (function == P_Command) {
        // Process command string
        processCommand(value);
    }

    callParamCallbacks();
    return status;
}
```

### 7.5 Enum Read (Dynamic Enumerations)

```cpp
asynStatus myDriver::readEnum(asynUser *pasynUser, char *strings[],
    int values[], int severities[], size_t nElements, size_t *nIn)
{
    int function = pasynUser->reason;

    if (function == P_GainSelect) {
        const char *gainStrings[] = {"1x", "2x", "5x", "10x"};
        size_t n = sizeof(gainStrings) / sizeof(gainStrings[0]);
        if (n > nElements) n = nElements;
        for (size_t i = 0; i < n; i++) {
            strings[i] = epicsStrDup(gainStrings[i]);
            values[i] = (int)i;
            severities[i] = 0;
        }
        *nIn = n;
        return asynSuccess;
    }
    return asynPortDriver::readEnum(pasynUser, strings, values, severities,
                                     nElements, nIn);
}
```

### 7.6 Connect/Disconnect

```cpp
asynStatus myDriver::connect(asynUser *pasynUser)
{
    asynPrint(pasynUser, ASYN_TRACE_FLOW, "connect\n");
    // Open hardware connection
    return asynPortDriver::connect(pasynUser);
}

asynStatus myDriver::disconnect(asynUser *pasynUser)
{
    asynPrint(pasynUser, ASYN_TRACE_FLOW, "disconnect\n");
    // Close hardware connection
    return asynPortDriver::disconnect(pasynUser);
}
```

### 7.7 Report

```cpp
void myDriver::report(FILE *fp, int details)
{
    fprintf(fp, "myDriver: port=%s\n", portName);
    if (details > 0) {
        fprintf(fp, "  waveformSize=%d\n", waveformSize_);
    }
    asynPortDriver::report(fp, details);
}
```

---

## 8. Background Thread Pattern

```cpp
// C callback wrapper (static or free function)
static void pollingTaskC(void *drvPvt)
{
    myDriver *pPvt = (myDriver *)drvPvt;
    pPvt->pollingTask();
}

void myDriver::pollingTask()
{
    while (running_) {
        // Wait for a signal or timeout
        epicsEventWaitWithTimeout(pollEventId_, 1.0);

        // Lock the driver (required before accessing parameters)
        lock();

        int run;
        getIntegerParam(P_Run, &run);
        if (run) {
            // Read hardware, compute data, etc.
            double value = readFromHardware();
            setDoubleParam(P_Value, value);

            // Update waveform
            computeWaveform(waveformData_, waveformSize_);
            doCallbacksFloat64Array(waveformData_, waveformSize_, P_Waveform, 0);

            callParamCallbacks();
        }

        unlock();
    }
}
```

**CRITICAL:** Always call `lock()` before and `unlock()` after accessing the parameter library from a background thread. The write/read virtual methods are called with the lock already held.

---

## 9. Trace/Debug Logging

```cpp
// asynPrint -- conditional printf-style logging
asynPrint(pasynUser, ASYN_TRACE_ERROR,
    "%s: error reading channel %d\n", portName, channel);

asynPrint(pasynUser, ASYN_TRACE_FLOW,
    "%s: writeInt32 function=%d value=%d\n", portName, function, value);

asynPrint(pasynUser, ASYN_TRACE_WARNING,
    "%s: value %f out of range, clamped\n", portName, value);

// asynPrintIO -- log binary/hex data
asynPrintIO(pasynUser, ASYN_TRACEIO_DRIVER,
    buffer, nbytes, "%s: read %d bytes\n", portName, nbytes);

// From background thread, use pasynUserSelf (protected member)
asynPrint(pasynUserSelf, ASYN_TRACE_FLOW,
    "%s: polling task iteration\n", portName);
```

### Trace Mask Values

| Mask | Value | Use |
|------|-------|-----|
| `ASYN_TRACE_ERROR` | 0x01 | Error messages (always on by default) |
| `ASYN_TRACEIO_DEVICE` | 0x02 | Device-level I/O data |
| `ASYN_TRACEIO_FILTER` | 0x04 | Filter/interpose layer I/O |
| `ASYN_TRACEIO_DRIVER` | 0x08 | Low-level driver I/O data |
| `ASYN_TRACE_FLOW` | 0x10 | Control flow messages |
| `ASYN_TRACE_WARNING` | 0x20 | Warning messages |

---

## 10. asynStatus Return Values

```cpp
enum asynStatus {
    asynSuccess,        // Operation completed successfully
    asynTimeout,        // Operation timed out
    asynOverflow,       // Buffer overflow
    asynError,          // General error
    asynDisconnected,   // Port is disconnected
    asynDisabled        // Port is disabled
};
```

---

## 11. IOC Shell Registration

```cpp
// At the bottom of myDriver.cpp:

extern "C" {

static const iocshArg initArg0 = {"portName", iocshArgString};
static const iocshArg initArg1 = {"maxAddr", iocshArgInt};
static const iocshArg *initArgs[] = {&initArg0, &initArg1};
static const iocshFuncDef initDef = {"myDriverConfigure", 2, initArgs};

static void initCallFunc(const iocshArgBuf *args)
{
    new myDriver(args[0].sval, args[1].ival);
}

static void myDriverRegister(void)
{
    iocshRegister(&initDef, initCallFunc);
}

epicsExportRegistrar(myDriverRegister);

} // extern "C"
```

**Note:** The driver is allocated with `new` and never explicitly deleted. The asynManager takes ownership. For EPICS 7+ use `ASYN_DESTRUCTIBLE` flag and implement `shutdownPortDriver()` for clean shutdown.

### DBD File

```
registrar(myDriverRegister)
```

---

## 12. Destructor and Shutdown

```cpp
myDriver::~myDriver()
{
    running_ = false;
    epicsEventSignal(pollEventId_);
    // Wait for thread to exit (if joinable) or sleep briefly
    epicsThreadSleep(1.0);
    free(waveformData_);
    epicsEventDestroy(pollEventId_);
}
```

For clean shutdown with EPICS 7+, use the `ASYN_DESTRUCTIBLE` flag and override `shutdownPortDriver()`:

```cpp
// In constructor: pass ASYN_CANBLOCK | ASYN_DESTRUCTIBLE as asynFlags
// Override:
void myDriver::shutdownPortDriver()
{
    running_ = false;
    epicsEventSignal(pollEventId_);
    // Join or wait for polling thread
}
```

---

## 13. Complete Minimal Example

```cpp
/* myDriver.cpp */
#include <epicsThread.h>
#include <epicsEvent.h>
#include <asynPortDriver.h>

#define P_ValueString "MY_VALUE"
#define P_CountString "MY_COUNT"

class myDriver : public asynPortDriver {
public:
    myDriver(const char *portName);
    virtual asynStatus writeInt32(asynUser *pasynUser, epicsInt32 value);
    void pollingTask();
protected:
    int P_Value;
    int P_Count;
private:
    epicsEventId pollEvent_;
    bool running_;
};

static void pollingTaskC(void *p) { ((myDriver *)p)->pollingTask(); }

myDriver::myDriver(const char *portName)
    : asynPortDriver(portName, 1,
        asynInt32Mask | asynFloat64Mask | asynDrvUserMask,
        asynInt32Mask | asynFloat64Mask,
        ASYN_CANBLOCK, 1, 0, 0)
    , pollEvent_(epicsEventCreate(epicsEventEmpty))
    , running_(true)
{
    createParam(P_ValueString, asynParamFloat64, &P_Value);
    createParam(P_CountString, asynParamInt32,   &P_Count);
    setDoubleParam(P_Value, 0.0);
    setIntegerParam(P_Count, 0);
    epicsThreadCreate("myPoll", epicsThreadPriorityMedium,
        epicsThreadGetStackSize(epicsThreadStackMedium), pollingTaskC, this);
}

asynStatus myDriver::writeInt32(asynUser *pasynUser, epicsInt32 value)
{
    asynStatus status = asynPortDriver::writeInt32(pasynUser, value);
    if (pasynUser->reason == P_Count) {
        epicsEventSignal(pollEvent_);
    }
    callParamCallbacks();
    return status;
}

void myDriver::pollingTask()
{
    while (running_) {
        epicsEventWaitWithTimeout(pollEvent_, 1.0);
        lock();
        int count;
        getIntegerParam(P_Count, &count);
        setDoubleParam(P_Value, (double)count * 1.1);
        callParamCallbacks();
        unlock();
    }
}

extern "C" {
static const iocshArg arg0 = {"portName", iocshArgString};
static const iocshArg *args[] = {&arg0};
static const iocshFuncDef configDef = {"myDriverConfigure", 1, args};
static void configFunc(const iocshArgBuf *a) { new myDriver(a[0].sval); }
static void myDriverRegister(void) { iocshRegister(&configDef, configFunc); }
epicsExportRegistrar(myDriverRegister);
}
```

---

## 14. Key Rules and Pitfalls

1. **Always call `callParamCallbacks()`** after `setXxxParam()` for changes to propagate to I/O Intr records. This is the single most common mistake.

2. **Array data requires explicit `doCallbacksXxxArray()`** -- `callParamCallbacks()` only handles scalars and strings.

3. **The driver mutex is held** when write/read virtual methods are called. Do NOT call `lock()` inside them -- it would deadlock (the mutex is recursive, but nested locking is unnecessary).

4. **In background threads, you MUST call `lock()`/`unlock()`** around parameter library access.

5. **`interfaceMask` must include `asynDrvUserMask`** if records use drvInfo strings (which they almost always do).

6. **`interruptMask` must include masks** for any interface where records use `SCAN = "I/O Intr"`.

7. **Use `ASYN_CANBLOCK`** for any driver that performs real I/O. Without it, the port has no thread and all I/O happens synchronously in the record processing thread.

8. **Use `pasynUserSelf`** (protected member) for `asynPrint` calls from background threads where you don't have a `pasynUser` from a record.

9. **The `reason` field** in `pasynUser` is the parameter index set by `createParam()`. Use it to identify which parameter is being read/written.

10. **Driver objects are never deleted** in the traditional pattern (allocated with `new` in the iocsh configure function). For EPICS 7+ clean shutdown, use the `ASYN_DESTRUCTIBLE` flag.
