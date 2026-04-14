---
name: epics-device-support
description: Write custom EPICS device support in C/C++ -- dset structures, init/read/write routines, async processing, I/O Intr scanning, iocsh command registration, and subroutine record functions
---

# EPICS Device Support Skill

You are an expert at writing EPICS device support code in C and C++. Device support is the primary mechanism for integrating hardware into EPICS. You write:

1. **Device support entry tables (dset)** -- Function pointer structures that connect record types to driver code.
2. **DBD declarations** -- `device()`, `registrar()`, `function()`, and `variable()` entries.
3. **IOC shell commands** -- Registering configuration commands for use in st.cmd.
4. **Subroutine record functions** -- C functions callable from sub and aSub records.

---

## 1. Device Support Entry Table (dset)

Every device support implementation defines a `dset` (device support entry table) structure. The first 4 function pointers are common to all record types; additional function pointers are record-type-specific.

### 1.1 Common dset Functions

```c
typedef struct typed_dset {
    long number;                    /* Total number of function pointers */
    long (*report)(int lvl);        /* Called from dbior() -- print report */
    long (*init)(int after);        /* Called twice: after=0 before init_record, after=1 after */
    long (*init_record)(struct dbCommon *prec);  /* Per-record initialization */
    long (*get_ioint_info)(int detach, struct dbCommon *prec, IOSCANPVT *pscan);
    /* Record-type-specific functions follow... */
} typed_dset;
```

### 1.2 Record-Type-Specific dset Structures

Each record type extends the common 4 functions with record-specific ones. The `number` field must equal the total count including the common 4.

| Record Type | number | Extra Functions | Typedef |
|------------|--------|-----------------|---------|
| ai | 6 | `read_ai`, `special_linconv` | `aidset` |
| ao | 6 | `write_ao`, `special_linconv` | `aodset` |
| bi | 5 | `read_bi` | `bidset` |
| bo | 5 | `write_bo` | `bodset` |
| longin | 5 | `read_longin` | `longindset` |
| longout | 5 | `write_longout` | `longoutdset` |
| int64in | 5 | `read_int64in` | `int64indset` |
| int64out | 5 | `write_int64out` | `int64outdset` |
| stringin | 5 | `read_stringin` | `stringindset` |
| stringout | 5 | `write_stringout` | `stringoutdset` |
| mbbi | 5 | `read_mbbi` | `mbbidset` |
| mbbo | 5 | `write_mbbo` | `mbbodset` |
| mbbiDirect | 5 | `read_mbbiDirect` | `mbbiDirectdset` |
| mbboDirect | 5 | `write_mbboDirect` | `mbboDirectdset` |
| waveform | 5 | `read_wf` | `waveformdset` |
| aai | 5 | `read_aai` | `aaidset` |
| aao | 5 | `write_aao` | `aaodset` |
| lsi | 5 | `read_string` | `lsidset` |
| lso | 5 | `write_string` | `lsodset` |
| calcout | 5 | `write` | `calcoutdset` |
| event | 5 | `read_event` | `eventdset` |

---

## 2. Writing Synchronous Device Support

### 2.1 Complete Example: Synchronous AI Device Support

```c
/* devMyAi.c */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "alarm.h"
#include "dbDefs.h"
#include "dbAccess.h"
#include "recGbl.h"
#include "devSup.h"
#include "link.h"
#include "aiRecord.h"
#include "epicsExport.h"   /* MUST be last EPICS include */

/* Private data stored in prec->dpvt */
typedef struct {
    int channel;
} devMyAiPvt;

static long init_record(dbCommon *pcommon)
{
    aiRecord *prec = (aiRecord *)pcommon;
    devMyAiPvt *pvt;

    /* Parse the INP link -- expects INST_IO format: @channel_number */
    if (prec->inp.type != INST_IO) {
        recGblRecordError(S_dev_badInpType, prec,
            "devMyAi (init_record) bad INP link type");
        return S_dev_badInpType;
    }

    pvt = (devMyAiPvt *)calloc(1, sizeof(*pvt));
    if (!pvt) {
        recGblRecordError(S_db_noMemory, prec,
            "devMyAi (init_record) calloc failed");
        return S_db_noMemory;
    }

    if (sscanf(prec->inp.value.instio.string, "%d", &pvt->channel) != 1) {
        recGblRecordError(S_dev_badSignal, prec,
            "devMyAi (init_record) bad channel in INP");
        free(pvt);
        return S_dev_badSignal;
    }

    prec->dpvt = pvt;
    return 0;   /* 0 = use RVAL with conversion; 2 = use VAL directly */
}

static long read_ai(aiRecord *prec)
{
    devMyAiPvt *pvt = (devMyAiPvt *)prec->dpvt;

    if (!pvt) {
        recGblSetSevr(prec, READ_ALARM, INVALID_ALARM);
        return -1;
    }

    /* Read from hardware -- replace with actual driver call */
    prec->val = myDriverReadChannel(pvt->channel);
    prec->udf = FALSE;

    return 2;   /* 2 = don't convert, VAL already set */
                /* 0 = convert RVAL using LINR/ESLO/EOFF */
}

/* Device support entry table */
aidset devMyAi = {
    {6, NULL, NULL, init_record, NULL},
    read_ai,
    NULL    /* special_linconv -- NULL if not needed */
};
epicsExportAddress(dset, devMyAi);
```

### 2.2 Return Value Conventions

**For `init_record()`:**
- Return `0` on success.
- Return non-zero error code on failure (e.g., `S_dev_badInpType`).
- For ai/ao: return `0` means use RVAL with conversion; return `2` means VAL is set directly (skip conversion).

**For `read_xxx()` (input records):**
- Return `0` for success (record processes normally; for ai, means convert RVAL).
- Return `2` for ai to indicate VAL is already set (skip RVAL->VAL conversion).
- Return non-zero error code to signal failure.

**For `write_xxx()` (output records):**
- Return `0` for success.
- Return non-zero error code on failure.

**For bi `read_bi()`:**
- Return `0` means RVAL was set, record converts via MASK.
- Return `2` means VAL was set directly (skip RVAL->VAL conversion).

---

## 3. Writing Asynchronous Device Support

Asynchronous device support allows I/O operations without blocking the scan thread. The key mechanism uses the record's `PACT` (processing active) field and callbacks.

### 3.1 Async Pattern Overview

1. First call to `read/write`: set `prec->pact = TRUE`, start async operation, return `0`.
2. When async operation completes (in callback): call `callbackRequestProcessCallback()` to re-process the record.
3. Second call to `read/write` (with `prec->pact == TRUE`): store results, return normally.

### 3.2 Complete Example: Asynchronous AI Device Support

```c
/* devMyAsyncAi.c */

#include <stdlib.h>
#include <stdio.h>

#include "alarm.h"
#include "callback.h"
#include "dbDefs.h"
#include "dbAccess.h"
#include "recGbl.h"
#include "recSup.h"
#include "devSup.h"
#include "link.h"
#include "aiRecord.h"
#include "epicsExport.h"   /* MUST be last */

typedef struct {
    int channel;
    epicsCallback callback;   /* MUST be zero-initialized */
    double value;
    int status;
} devMyAsyncAiPvt;

static long init_record(dbCommon *pcommon)
{
    aiRecord *prec = (aiRecord *)pcommon;
    devMyAsyncAiPvt *pvt;

    if (prec->inp.type != INST_IO) {
        recGblRecordError(S_dev_badInpType, prec,
            "devMyAsyncAi (init_record) bad INP link type");
        return S_dev_badInpType;
    }

    pvt = (devMyAsyncAiPvt *)calloc(1, sizeof(*pvt));
    if (!pvt) return S_db_noMemory;

    sscanf(prec->inp.value.instio.string, "%d", &pvt->channel);
    prec->dpvt = pvt;
    return 0;
}

static long read_ai(aiRecord *prec)
{
    devMyAsyncAiPvt *pvt = (devMyAsyncAiPvt *)prec->dpvt;

    if (!pvt) {
        recGblSetSevr(prec, READ_ALARM, INVALID_ALARM);
        return -1;
    }

    if (!prec->pact) {
        /* FIRST PASS: start async I/O */

        /* Start the async operation (your driver does the actual work).
         * When complete, call:
         *   callbackRequestProcessCallback(&pvt->callback, prec->prio, prec);
         * This will re-process the record (triggering second pass).
         */
        myDriverStartAsyncRead(pvt->channel, pvt);

        prec->pact = TRUE;
        return 0;   /* record stays active, no processing yet */
    }

    /* SECOND PASS: I/O is complete, store result */
    if (pvt->status != 0) {
        recGblSetSevr(prec, READ_ALARM, INVALID_ALARM);
        return pvt->status;
    }

    prec->val = pvt->value;
    prec->udf = FALSE;
    return 2;   /* VAL already set */
}

/* Callback function called from your driver when I/O completes.
 * This runs in the driver's thread context.
 */
void myDriverIOComplete(devMyAsyncAiPvt *pvt, double value, int status)
{
    pvt->value = value;
    pvt->status = status;
    /* Schedule record re-processing in the callback thread */
    callbackRequestProcessCallback(&pvt->callback,
        ((aiRecord *)pvt->callback.user)->prio,
        pvt->callback.user);
}

aidset devMyAsyncAi = {
    {6, NULL, NULL, init_record, NULL},
    read_ai,
    NULL
};
epicsExportAddress(dset, devMyAsyncAi);
```

### 3.3 Using callbackRequestProcessCallback

```c
#include "callback.h"

/* The epicsCallback (CALLBACK) struct must be zero-initialized before first use.
 * Typically it is part of the device private structure allocated with calloc().
 *
 * callbackRequestProcessCallback() initializes the callback AND queues it.
 * It sets up the callback to call dbProcess() on the record.
 */
callbackRequestProcessCallback(
    &pvt->callback,     /* Pointer to epicsCallback struct */
    prec->prio,         /* Priority: priorityLow, priorityMedium, priorityHigh */
    prec                /* Pointer to the record (dbCommon or specific type) */
);
```

### 3.4 Delayed Callback (Timed Async)

```c
/* Schedule a callback after a delay (in seconds) */
callbackRequestProcessCallbackDelayed(
    &pvt->callback,     /* epicsCallback -- must be zero-initialized */
    prec->prio,         /* Priority */
    prec,               /* Record pointer */
    1.0                 /* Delay in seconds */
);
```

---

## 4. I/O Interrupt Scanning

I/O Interrupt scanning allows a record to be processed when the driver signals new data, rather than on a periodic schedule. The record uses `SCAN = "I/O Intr"`.

### 4.1 Implementation Pattern

```c
#include "dbScan.h"   /* for IOSCANPVT, scanIoInit, scanIoRequest */

typedef struct {
    int channel;
    IOSCANPVT ioscanpvt;
} devMyPvt;

static long init_record(dbCommon *pcommon)
{
    aiRecord *prec = (aiRecord *)pcommon;
    devMyPvt *pvt;

    pvt = (devMyPvt *)calloc(1, sizeof(*pvt));
    /* ... parse INP, set channel ... */

    /* Initialize the I/O scan list */
    scanIoInit(&pvt->ioscanpvt);

    prec->dpvt = pvt;
    return 0;
}

/* get_ioint_info: called when SCAN is set to "I/O Intr" */
static long get_ioint_info(int detach, dbCommon *prec, IOSCANPVT *pscan)
{
    devMyPvt *pvt = (devMyPvt *)prec->dpvt;

    if (!pvt) return -1;

    *pscan = pvt->ioscanpvt;
    return 0;
}

/* This function is called from the driver/interrupt handler
 * when new data is available. It triggers processing of all
 * records registered on this scan list.
 */
void myDriverDataReady(devMyPvt *pvt)
{
    /* Trigger all I/O Intr-scanned records on this list */
    scanIoRequest(pvt->ioscanpvt);
}

/* Include get_ioint_info in the dset */
aidset devMyIoIntrAi = {
    {6, NULL, NULL, init_record, get_ioint_info},
    read_ai,
    NULL
};
epicsExportAddress(dset, devMyIoIntrAi);
```

### 4.2 get_ioint_info Arguments

- `detach`: 0 when adding the record to the scan list, 1 when removing it. If a record uses only one scan list, `detach` can be ignored.
- `prec`: pointer to the record.
- `pscan`: output -- set `*pscan` to the IOSCANPVT for this record's scan list.

---

## 5. Device Support for Different Record Types

### 5.1 AI Device Support

```c
/* number = 6: common(4) + read_ai + special_linconv */
aidset devMyAi = {
    {6, NULL, NULL, init_record, get_ioint_info},
    read_ai,       /* long (*read_ai)(aiRecord *prec) */
    NULL           /* long (*special_linconv)(aiRecord *prec, int after) */
};
epicsExportAddress(dset, devMyAi);
```

`read_ai` return values:
- `0` = success, record uses RVAL with LINR conversion.
- `2` = success, VAL was set directly (skip conversion).
- Negative = error.

### 5.2 AO Device Support

```c
aodset devMyAo = {
    {6, NULL, NULL, init_record, get_ioint_info},
    write_ao,       /* long (*write_ao)(aoRecord *prec) */
    NULL            /* long (*special_linconv)(aoRecord *prec, int after) */
};
epicsExportAddress(dset, devMyAo);
```

`write_ao`: read OVAL or RVAL from the record, write to hardware.

### 5.3 BI Device Support

```c
bidset devMyBi = {
    {5, NULL, NULL, init_record, get_ioint_info},
    read_bi          /* long (*read_bi)(biRecord *prec) */
};
epicsExportAddress(dset, devMyBi);
```

`read_bi` return values:
- `0` = RVAL was set, record applies MASK and converts to VAL.
- `2` = VAL was set directly.

### 5.4 BO Device Support

```c
bodset devMyBo = {
    {5, NULL, NULL, init_record, get_ioint_info},
    write_bo         /* long (*write_bo)(boRecord *prec) */
};
epicsExportAddress(dset, devMyBo);
```

### 5.5 Longin Device Support

```c
longindset devMyLi = {
    {5, NULL, NULL, init_record, get_ioint_info},
    read_longin      /* long (*read_longin)(longinRecord *prec) */
};
epicsExportAddress(dset, devMyLi);
```

### 5.6 Longout Device Support

```c
longoutdset devMyLo = {
    {5, NULL, NULL, init_record, get_ioint_info},
    write_longout    /* long (*write_longout)(longoutRecord *prec) */
};
epicsExportAddress(dset, devMyLo);
```

### 5.7 Stringin Device Support

```c
stringindset devMySi = {
    {5, NULL, NULL, init_record, get_ioint_info},
    read_stringin    /* long (*read_stringin)(stringinRecord *prec) */
};
epicsExportAddress(dset, devMySi);
```

### 5.8 Stringout Device Support

```c
stringoutdset devMySo = {
    {5, NULL, NULL, init_record, get_ioint_info},
    write_stringout  /* long (*write_stringout)(stringoutRecord *prec) */
};
epicsExportAddress(dset, devMySo);
```

### 5.9 Waveform Device Support

```c
waveformdset devMyWf = {
    {5, NULL, NULL, init_record, get_ioint_info},
    read_wf          /* long (*read_wf)(waveformRecord *prec) */
};
epicsExportAddress(dset, devMyWf);
```

For waveform, the `read_wf` function typically:
1. Gets a pointer to the array: `void *bptr = prec->bptr;`
2. Checks element type: `prec->ftvl` (e.g., `menuFtypeDOUBLE`)
3. Fills the array and sets `prec->nord` to the actual element count.

---

## 6. DBD Declarations

### 6.1 Device Support Declaration

```
device(recordType, linkType, dsetName, "Choice String")
```

Examples:
```
device(ai, INST_IO, devMyAi, "My AI Driver")
device(ao, INST_IO, devMyAo, "My AO Driver")
device(bi, INST_IO, devMyBi, "My BI Driver")
device(bo, INST_IO, devMyBo, "My BO Driver")
device(longin, INST_IO, devMyLi, "My Longin Driver")
device(longout, INST_IO, devMyLo, "My Longout Driver")
device(stringin, INST_IO, devMySi, "My Stringin Driver")
device(stringout, INST_IO, devMySo, "My Stringout Driver")
device(waveform, INST_IO, devMyWf, "My Waveform Driver")
```

The "Choice String" appears as the DTYP menu option in the database record.

### 6.2 Complete Support Module DBD

```
# mySupport.dbd
device(ai, INST_IO, devMyAi, "My AI Driver")
device(ao, INST_IO, devMyAo, "My AO Driver")
device(bi, INST_IO, devMyBi, "My BI Driver")
device(bo, INST_IO, devMyBo, "My BO Driver")
registrar(myCommandsRegister)
```

---

## 7. IOC Shell Command Registration

IOC shell commands allow users to configure drivers from st.cmd.

### 7.1 Complete Pattern

```c
/* myCommands.c */

#include <stdio.h>
#include <string.h>

#include <iocsh.h>
#include <epicsExport.h>   /* MUST be last */

/* ---- The actual command function ---- */
void myDriverConfigure(const char *portName, const char *ipAddress, int channel)
{
    if (!portName || !ipAddress) {
        printf("Usage: myDriverConfigure portName ipAddress channel\n");
        return;
    }
    /* ... create and configure driver instance ... */
    printf("Configured port %s: %s channel %d\n", portName, ipAddress, channel);
}

/* ---- iocsh registration boilerplate ---- */

/* Define argument descriptors */
static const iocshArg arg0 = {"portName",   iocshArgString};
static const iocshArg arg1 = {"ipAddress",  iocshArgString};
static const iocshArg arg2 = {"channel",    iocshArgInt};

/* Array of argument pointers */
static const iocshArg *args[] = {&arg0, &arg1, &arg2};

/* Function definition (name, arg count, arg array, optional usage string) */
static const iocshFuncDef myDriverConfigureFuncDef = {
    "myDriverConfigure",  /* command name */
    3,                    /* number of arguments */
    args,                 /* argument descriptors */
#ifdef IOCSHFUNCDEF_HAS_USAGE
    "Configure a myDriver port.\n"
    "  portName  - unique port name\n"
    "  ipAddress - device IP address (e.g., \"192.168.1.100:5025\")\n"
    "  channel   - channel number (0-7)\n\n"
    "Example: myDriverConfigure PORT1 192.168.1.100:5025 0\n",
#endif
};

/* Wrapper that extracts typed arguments from iocshArgBuf */
static void myDriverConfigureCallFunc(const iocshArgBuf *args)
{
    myDriverConfigure(args[0].sval, args[1].sval, args[2].ival);
}

/* Registrar function -- called at IOC startup */
static void myDriverRegistrar(void)
{
    iocshRegister(&myDriverConfigureFuncDef, myDriverConfigureCallFunc);
}
epicsExportRegistrar(myDriverRegistrar);
```

### 7.2 Argument Types

| Type | C Access | Description |
|------|----------|-------------|
| `iocshArgString` | `args[n].sval` (char *) | String argument |
| `iocshArgInt` | `args[n].ival` (int) | Integer argument |
| `iocshArgDouble` | `args[n].dval` (double) | Double argument |
| `iocshArgPdbbase` | `args[n].vval` (void *) | pdbbase pointer |
| `iocshArgArgv` | `args[n].aval` (struct) | argc/argv style |

### 7.3 DBD Declaration

```
registrar(myDriverRegistrar)
```

### 7.4 Multiple Commands

Register multiple commands in a single registrar:

```c
static void myRegistrar(void)
{
    iocshRegister(&configureFuncDef, configureCallFunc);
    iocshRegister(&reportFuncDef, reportCallFunc);
    iocshRegister(&debugFuncDef, debugCallFunc);
}
epicsExportRegistrar(myRegistrar);
```

---

## 8. IOC Shell Variables

Export a global variable accessible from the IOC shell via `var variableName value`:

```c
/* In C source */
int myDriverDebug = 0;
epicsExportAddress(int, myDriverDebug);
```

```
# In DBD
variable(myDriverDebug, int)
```

Usage in st.cmd: `var myDriverDebug 1`

---

## 9. Subroutine and aSub Record Functions

### 9.1 Sub Record Functions

```c
/* mySubFuncs.c */
#include <stdio.h>
#include <registryFunction.h>
#include <subRecord.h>
#include <epicsExport.h>   /* MUST be last */

static long mySubInit(subRecord *prec)
{
    /* Called once during record initialization */
    printf("mySubInit: record %s\n", prec->name);
    return 0;   /* 0 = success */
}

static long mySubProcess(subRecord *prec)
{
    /* Called every time the record processes.
     * Input values are in prec->a through prec->u.
     * Set prec->val to the output value.
     */
    prec->val = prec->a + prec->b;
    return 0;   /* 0 = success; non-zero sets BRSV alarm */
}

/* Register functions */
epicsRegisterFunction(mySubInit);
epicsRegisterFunction(mySubProcess);
```

### 9.2 aSub Record Functions

```c
/* myASubFuncs.c */
#include <stdio.h>
#include <string.h>
#include <registryFunction.h>
#include <aSubRecord.h>
#include <epicsExport.h>   /* MUST be last */

static long myASubInit(aSubRecord *prec)
{
    printf("myASubInit: record %s\n", prec->name);
    return 0;
}

static long myASubProcess(aSubRecord *prec)
{
    /* Access input arrays through void pointers.
     * Cast based on FTA..FTU field settings.
     * prec->a through prec->u are void* to input data.
     * prec->noa through prec->nou are max element counts.
     * prec->nea through prec->neu are actual element counts.
     *
     * prec->vala through prec->valu are void* to output data.
     * prec->nova through prec->novu are max output elements.
     * prec->neva through prec->nevu are actual output elements.
     */

    double *input  = (double *)prec->a;     /* FTA must be "DOUBLE" */
    double *output = (double *)prec->vala;  /* FTVA must be "DOUBLE" */
    long nElements = prec->noa;
    long i;
    double sum = 0.0;

    for (i = 0; i < nElements && i < (long)prec->nea; i++) {
        output[i] = input[i] * 2.0;
        sum += input[i];
    }

    /* Set actual output element count */
    prec->neva = prec->nea;

    /* Can also set a scalar output in prec->val */
    prec->val = (long)sum;

    return 0;   /* 0 = success; non-zero sets BRSV alarm */
}

epicsRegisterFunction(myASubInit);
epicsRegisterFunction(myASubProcess);
```

### 9.3 DBD Declarations for Subroutines

```
function(mySubInit)
function(mySubProcess)
function(myASubInit)
function(myASubProcess)
```

### 9.4 Database Records for Subroutines

```
record(sub, "$(P):myCalc") {
    field(INAM, "mySubInit")
    field(SNAM, "mySubProcess")
    field(INPA, "$(P):Input1 CPP")
    field(INPB, "$(P):Input2 CPP")
}

record(aSub, "$(P):myArrayCalc") {
    field(INAM, "myASubInit")
    field(SNAM, "myASubProcess")
    field(FTA,  "DOUBLE")
    field(NOA,  "1024")
    field(INPA, "$(P):Waveform CPP")
    field(FTVA, "DOUBLE")
    field(NOVA, "1024")
    field(OUTA, "$(P):Result PP")
    field(EFLG, "ON CHANGE")
}
```

---

## 10. Init Hooks

Register a function to be called at specific IOC lifecycle stages:

```c
/* myInitHook.c */
#include <stdio.h>
#include "initHooks.h"
#include "epicsExport.h"
#include "iocsh.h"

static void myHookFunc(initHookState state)
{
    switch (state) {
    case initHookAfterInitDatabase:
        printf("Database initialized\n");
        break;
    case initHookAfterIocRunning:
        printf("IOC is running\n");
        break;
    case initHookAtShutdown:
        printf("IOC shutting down\n");
        break;
    default:
        break;
    }
}

static void myInitHookRegister(void)
{
    initHookRegister(myHookFunc);
}
epicsExportRegistrar(myInitHookRegister);
```

DBD:
```
registrar(myInitHookRegister)
```

Key lifecycle states (in order):
- `initHookAtIocBuild`
- `initHookAtBeginning`
- `initHookAfterCallbackInit`
- `initHookAfterInitDrvSup`
- `initHookAfterInitRecSup`
- `initHookAfterInitDevSup`
- `initHookAfterInitDatabase`
- `initHookAfterFinishDevSup`
- `initHookAfterScanInit`
- `initHookAfterInitialProcess` (PINI records processed)
- `initHookAfterIocBuilt`
- `initHookAtIocRun`
- `initHookAfterDatabaseRunning`
- `initHookAfterIocRunning`
- `initHookAtIocPause`
- `initHookAtShutdown`

---

## 11. Makefile Integration

### 11.1 Support Library Makefile

```makefile
LIBRARY_IOC += mySupport

DBD += mySupport.dbd

mySupport_SRCS += devMyAi.c
mySupport_SRCS += devMyAo.c
mySupport_SRCS += myCommands.c
mySupport_SRCS += mySubFuncs.c
mySupport_SRCS += myInitHook.c

mySupport_LIBS += $(EPICS_BASE_IOC_LIBS)
```

### 11.2 IOC Application Using the Support Library

```makefile
PROD_IOC = myApp

DBD += myApp.dbd
myApp_DBD += base.dbd
myApp_DBD += mySupport.dbd

myApp_SRCS += myApp_registerRecordDeviceDriver.cpp
myApp_SRCS_DEFAULT += myAppMain.cpp
myApp_SRCS_vxWorks += -nil-

myApp_LIBS += mySupport
myApp_LIBS += $(EPICS_BASE_IOC_LIBS)
```

### 11.3 Recommended Build Flags

```makefile
# Use type-safe dset and rset (recommended for EPICS 7)
USR_CPPFLAGS += -DUSE_TYPED_RSET -DUSE_TYPED_DSET
```

---

## 12. Include File Ordering

The `epicsExport.h` header redefines the `epicsExportSharedSymbols` macro and MUST be the last EPICS include. The canonical ordering is:

```c
/* Standard C headers */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/* EPICS headers (any order among themselves) */
#include "alarm.h"
#include "callback.h"
#include "dbDefs.h"
#include "dbAccess.h"
#include "dbScan.h"
#include "recGbl.h"
#include "recSup.h"
#include "devSup.h"
#include "link.h"
#include "aiRecord.h"      /* or other record type header */

/* epicsExport.h MUST be last */
#include "epicsExport.h"
```

---

## 13. Error Handling Utilities

```c
#include "recGbl.h"
#include "alarm.h"

/* Set alarm status and severity on a record */
recGblSetSevr(prec, READ_ALARM, INVALID_ALARM);

/* Report an error during init_record */
recGblRecordError(S_dev_badInpType, prec, "devMyDriver: bad INP link");

/* Common status codes (from errMdef.h via devSup.h) */
S_dev_badInpType      /* Bad INP link type */
S_dev_badOutType      /* Bad OUT link type */
S_dev_badSignal       /* Illegal signal */
S_dev_noDeviceFound   /* No device at address */
S_db_noMemory         /* Memory allocation failed */

/* Alarm statuses (from alarm.h) */
READ_ALARM, WRITE_ALARM, HIHI_ALARM, HIGH_ALARM,
LOW_ALARM, LOLO_ALARM, STATE_ALARM, COS_ALARM,
COMM_ALARM, TIMEOUT_ALARM, HW_LIMIT_ALARM, CALC_ALARM,
SCAN_ALARM, LINK_ALARM, SOFT_ALARM, BAD_SUB_ALARM,
UDF_ALARM, DISABLE_ALARM, SIMM_ALARM

/* Alarm severities */
NO_ALARM, MINOR_ALARM, MAJOR_ALARM, INVALID_ALARM
```

---

## 14. Key Rules and Pitfalls

1. **`epicsExport.h` must be the LAST EPICS include** in any file that uses `epicsExportAddress()`, `epicsExportRegistrar()`, or `epicsRegisterFunction()`. Placing it earlier causes symbol visibility issues on shared library builds.

2. **The `number` field in dset must be correct** -- it is the total count of ALL function pointers (common + record-specific). AI/AO have 6, most others have 5.

3. **`dpvt` must be allocated with `calloc()`** (not `malloc()`) to ensure zero-initialization, especially for the `epicsCallback` struct which must be zeroed before first use.

4. **Async device support must NOT block** in the read/write function. Start the I/O and return immediately with `prec->pact = TRUE`. The record system handles re-processing when the callback fires.

5. **`callbackRequestProcessCallback()` schedules re-processing** in a callback thread. It is safe to call from any thread context (driver threads, interrupt handlers via `scanIoRequest()`).

6. **The dset variable name must match the DBD declaration.** If `device(ai, INST_IO, devMyAi, ...)` then the C variable must be `aidset devMyAi = {...};` and exported as `epicsExportAddress(dset, devMyAi);`.

7. **For output records**, `init_record()` should read the initial hardware state and set VAL/RVAL so the record starts with the correct value. This prevents output records from writing a stale value on first process.

8. **Use `recGblInitConstantLink()`** in `init_record()` for soft device support that reads a constant value from the INP/OUT link.

9. **`scanIoRequest()` is safe to call from interrupt context** on real-time OSs. It queues the I/O event and returns immediately.

10. **The `init()` function in dset** is called twice: first with `after=0` (before `init_record`), then with `after=1` (after all records are initialized). Use `after=0` for one-time driver initialization like `devExtend()`.
