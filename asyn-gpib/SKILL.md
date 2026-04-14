---
name: asyn-gpib
description: Write GPIB/SCPI instrument device support using the asyn devGpib framework -- gpibCmd command tables, DSET macros, EFAST tables, custom conversion routines, and DBD declarations
---

# asyn devGpib Skill

You are an expert at writing EPICS device support for GPIB and SCPI instruments using the asyn devGpib framework. This framework uses a command table (`gpibCmd[]`) to declaratively map EPICS record types to GPIB/SCPI commands.

---

## 1. File Structure

A devGpib instrument driver consists of:

1. **`devMyInstr.c`** -- C source with the command table, DSET defines, and `init_ai()`
2. **`devMyInstr.dbd`** -- DBD declarations binding record types to the driver
3. **Database files** -- `.db` records referencing the command table by parameter index

---

## 2. Source File Template

```c
/* devMyInstrument.c */
#include <epicsStdio.h>
#include <devCommonGpib.h>

/************************************************************
 * DSET name definitions -- define BEFORE including devGpib.h
 *
 * DSET_AI is always required. Define additional DSETs for
 * each record type your instrument uses.
 ************************************************************/
#define DSET_AI     devAiMyInstrument
#define DSET_AO     devAoMyInstrument
#define DSET_BI     devBiMyInstrument
#define DSET_BO     devBoMyInstrument
#define DSET_LI     devLiMyInstrument
#define DSET_LO     devLoMyInstrument
#define DSET_MBBI   devMbbiMyInstrument
#define DSET_MBBO   devMbboMyInstrument
#define DSET_SI     devSiMyInstrument
#define DSET_SO     devSoMyInstrument
#define DSET_WF     devWfMyInstrument

#include <devGpib.h>   /* MUST be included AFTER DSET defines */

#define TIMEOUT     1.0    /* Default I/O timeout (seconds) */
#define TIMEWINDOW  2.0    /* Quiet period after timeout (seconds) */

/* ... name lists, EFAST tables, command table, init_ai ... */
```

### Available DSET Macros

| Macro | Record Type | Notes |
|-------|-------------|-------|
| `DSET_AI` | ai | **Always required** even if unused |
| `DSET_AIRAW` | ai | AI with raw conversion (special_linconv) |
| `DSET_AO` | ao | |
| `DSET_AORAW` | ao | AO with raw conversion |
| `DSET_BI` | bi | |
| `DSET_BO` | bo | |
| `DSET_LI` | longin | |
| `DSET_LO` | longout | |
| `DSET_MBBI` | mbbi | |
| `DSET_MBBO` | mbbo | |
| `DSET_MBBID` | mbbiDirect | |
| `DSET_MBBOD` | mbboDirect | |
| `DSET_SI` | stringin | |
| `DSET_SO` | stringout | |
| `DSET_WF` | waveform | |
| `DSET_EV` | event | |

---

## 3. Name Lists (BI/BO/MBBI/MBBO)

Name lists populate the state string fields (ZNAM/ONAM for bi/bo, ZRST-FFST for mbbi/mbbo) automatically.

### 3.1 BI/BO Names (exactly 2 entries)

```c
static char *offOnList[] = {"Off", "On"};
static struct devGpibNames offOn = {2, offOnList, 0, 1};
/*                                  ^  ^          ^  ^
 *                            count-+  items     val nobt
 *                            (ignored for bi/bo)
 */
```

### 3.2 MBBI/MBBO Names (up to 16 entries)

```c
static char *modeList[] = {"Single", "Continuous", "Burst", "External"};
static unsigned long modeVals[] = {0, 1, 2, 3};
static struct devGpibNames modeNames = {4, modeList, modeVals, 2};
/*                                       ^  ^         ^         ^
 *                                 count-+  items    values   nobt
 */
```

The `devGpibNames` structure:

| Field | Type | Description |
|-------|------|-------------|
| `count` | int | Number of entries |
| `item` | char** | Array of display strings |
| `value` | unsigned long* | Array of raw values (NULL for bi/bo) |
| `nobt` | short | Number of bits (for mbbi/mbbo NOBT field) |

---

## 4. EFAST Tables

EFAST (Enumerated Fast) tables provide direct string-to-enum mapping for bi/bo and mbbi/mbbo records.

### 4.1 EFAST Output (GPIBEFASTO)

Sends the string at index `VAL` directly to the instrument:

```c
/* Array must end with 0 (NULL) */
static char *outputModeStrings[] = {"MODE SINGLE\n", "MODE CONT\n", 0};
```

When `VAL=0`, sends `"MODE SINGLE\n"`. When `VAL=1`, sends `"MODE CONT\n"`.

### 4.2 EFAST Input (GPIBEFASTI)

Sends `cmd`, reads response, matches against the string table:

```c
static char *statusStrings[] = {"OFF", "ON", "ERROR", 0};
```

If the response starts with `"ON"`, `VAL` is set to 1.

**Note:** Matching is prefix-based -- only as many characters as in the table entry are compared.

---

## 5. The gpibCmd Command Table

The command table is the heart of devGpib support. Each entry maps a parameter index to a record type, command type, and SCPI/GPIB command.

### 5.1 gpibCmd Structure

```c
struct gpibCmd {
    gDset *dset;        /* Pointer to the DSET (selects record type) */
    int type;           /* Command type (GPIBREAD, GPIBWRITE, etc.) */
    short pri;          /* Queue priority: IB_Q_LOW, IB_Q_MEDIUM, IB_Q_HIGH */
    char *cmd;          /* Command string to send */
    char *format;       /* scanf/printf format for value conversion */
    int rspLen;         /* Response buffer size (for respond2Writes) */
    int msgLen;         /* Message buffer size */
    int (*convert)();   /* Custom conversion function (or NULL) */
    int P1;             /* User parameter 1 (also EFAST table size, set internally) */
    int P2;             /* User parameter 2 */
    char **P3;          /* User parameter 3 (also EFAST table pointer) */
    devGpibNames *pdevGpibNames; /* Name list pointer (or NULL) */
    char *eos;          /* Per-command input EOS (or NULL for port default) */
};
```

### 5.2 Command Types

| Type | Constant | Behavior |
|------|----------|----------|
| `GPIBREAD` | 0x0001 | Send `cmd`, read response, parse with `format` |
| `GPIBWRITE` | 0x0002 | Format value with `format` into message, send |
| `GPIBCMD` | 0x0008 | Send `cmd` string only (no read, no format) |
| `GPIBACMD` | 0x0010 | Send `cmd` with ATN asserted |
| `GPIBSOFT` | 0x0020 | No I/O -- software-only processing |
| `GPIBREADW` | 0x0040 | Send `cmd`, wait for SRQ, then read |
| `GPIBRAWREAD` | 0x0080 | Read without sending a command first |
| `GPIBEFASTO` | 0x0100 | Send string from EFAST table (output enum) |
| `GPIBEFASTI` | 0x0200 | Send `cmd`, read response, match EFAST table (input enum) |
| `GPIBEFASTIW` | 0x0400 | Like GPIBEFASTI but wait for SRQ first |
| `GPIBSRQHANDLER` | 0x20000 | Register SRQ handler (longin only) |

### 5.3 Format Strings

Format strings follow `scanf` conventions for reads and `printf` conventions for writes:

| Record Type | Read Format | Write Format | Notes |
|-------------|-------------|--------------|-------|
| ai | `"%lf"` | -- | Parse as double |
| ao | -- | `"VOLT %lf"` | Format with double |
| longin | `"%d"` or `"%ld"` | -- | Parse as integer |
| longout | -- | `"COUNT %d"` | Format with integer |
| stringin | `"%39[^\r\n]"` | -- | Read up to 39 chars, stop at CR/LF |
| stringout | -- | (cmd field used) | |

---

## 6. Complete Command Table Example

```c
static struct gpibCmd gpibCmds[] = {
    /* Param 0: Read identification string (stringin) */
    {&DSET_SI, GPIBREAD, IB_Q_HIGH,
     "*IDN?", "%39[^\r\n]", 0, 200,
     NULL, 0, 0, NULL, NULL, NULL},

    /* Param 1: Reset instrument (bo) */
    {&DSET_BO, GPIBCMD, IB_Q_HIGH,
     "*RST", NULL, 0, 80,
     NULL, 0, 0, NULL, &resetNames, NULL},

    /* Param 2: Clear status (bo) */
    {&DSET_BO, GPIBCMD, IB_Q_HIGH,
     "*CLS", NULL, 0, 80,
     NULL, 0, 0, NULL, &clearNames, NULL},

    /* Param 3: Read status byte (longin) */
    {&DSET_LI, GPIBREAD, IB_Q_HIGH,
     "*STB?", "%d", 0, 80,
     NULL, 0, 0, NULL, NULL, NULL},

    /* Param 4: Read event status register (longin) */
    {&DSET_LI, GPIBREAD, IB_Q_HIGH,
     "*ESR?", "%d", 0, 80,
     NULL, 0, 0, NULL, NULL, NULL},

    /* Param 5: Set event status enable (longout) */
    {&DSET_LO, GPIBWRITE, IB_Q_HIGH,
     NULL, "*ESE %d", 0, 80,
     NULL, 0, 0, NULL, NULL, NULL},

    /* Param 6: Read voltage (ai) */
    {&DSET_AI, GPIBREAD, IB_Q_LOW,
     "MEAS:VOLT?", "%lf", 0, 80,
     NULL, 0, 0, NULL, NULL, NULL},

    /* Param 7: Set voltage (ao) */
    {&DSET_AO, GPIBWRITE, IB_Q_HIGH,
     NULL, "VOLT %lf", 0, 80,
     NULL, 0, 0, NULL, NULL, NULL},

    /* Param 8: Output mode select (mbbo via EFAST) */
    {&DSET_BO, GPIBEFASTO, IB_Q_HIGH,
     NULL, NULL, 0, 80,
     NULL, 0, 0, outputModeStrings, &outputModeNames, NULL},

    /* Param 9: Input status (bi via EFAST) */
    {&DSET_BI, GPIBEFASTI, IB_Q_HIGH,
     "STAT?", NULL, 0, 80,
     NULL, 0, 0, statusStrings, &statusNames, NULL},

    /* Param 10: Read with custom conversion (ai) */
    {&DSET_AI, GPIBREAD, IB_Q_LOW,
     "MEAS:CURR?", NULL, 0, 80,
     myConvertCurrent, 0, 0, NULL, NULL, NULL},
};

#define NUMPARAMS sizeof(gpibCmds)/sizeof(struct gpibCmd)
```

---

## 7. Custom Conversion Routines

```c
static int myConvertCurrent(gpibDpvt *pgpibDpvt, int P1, int P2, char **P3)
{
    aiRecord *prec = (aiRecord *)pgpibDpvt->precord;

    if (pgpibDpvt->msgInputLen <= 0) {
        recGblSetSevr(prec, READ_ALARM, INVALID_ALARM);
        return -1;
    }

    /* Parse the response from pgpibDpvt->msg */
    double value;
    if (sscanf(pgpibDpvt->msg, "%lf", &value) != 1) {
        recGblSetSevr(prec, READ_ALARM, INVALID_ALARM);
        return -1;
    }

    /* Set the record value directly */
    prec->val = value * 1000.0;  /* Convert A to mA */
    prec->udf = FALSE;

    return 0;  /* 0 = success, -1 = error */
}
```

---

## 8. init_ai Function

Every devGpib source file must implement `init_ai`:

```c
static long init_ai(int parm)
{
    if (parm == 0) {
        devSupParms.name = "devMyInstrument";
        devSupParms.gpibCmds = gpibCmds;
        devSupParms.numparams = NUMPARAMS;
        devSupParms.timeout = TIMEOUT;
        devSupParms.timeWindow = TIMEWINDOW;
        devSupParms.respond2Writes = -1;  /* -1 = no response to writes */
    }
    return 0;
}
```

### devGpibParmBlock Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | char* | Device support name |
| `gpibCmds` | gpibCmd* | Pointer to command table |
| `numparams` | int | Number of entries in command table |
| `timeout` | double | Default I/O timeout (seconds) |
| `timeWindow` | double | Quiet period after timeout (seconds) |
| `respond2Writes` | double | Response delay after write (-1 = no response, >=0 = seconds to wait before reading) |

---

## 9. DBD File

```
device(ai,        GPIB_IO, devAiMyInstrument,    "MyInstrument")
device(ao,        GPIB_IO, devAoMyInstrument,    "MyInstrument")
device(bi,        GPIB_IO, devBiMyInstrument,    "MyInstrument")
device(bo,        GPIB_IO, devBoMyInstrument,    "MyInstrument")
device(longin,    GPIB_IO, devLiMyInstrument,    "MyInstrument")
device(longout,   GPIB_IO, devLoMyInstrument,    "MyInstrument")
device(mbbi,      GPIB_IO, devMbbiMyInstrument,  "MyInstrument")
device(mbbo,      GPIB_IO, devMbboMyInstrument,  "MyInstrument")
device(stringin,  GPIB_IO, devSiMyInstrument,    "MyInstrument")
device(stringout, GPIB_IO, devSoMyInstrument,    "MyInstrument")
device(waveform,  GPIB_IO, devWfMyInstrument,    "MyInstrument")
```

The link type is `GPIB_IO`, NOT `INST_IO`. The DTYP choice string (e.g., `"MyInstrument"`) is what database records use.

---

## 10. Database Records

Records using devGpib use `GPIB_IO` link format with the parameter index:

```
field(INP, "#L$(L) A$(A) @param_index")
```

Where `L` is the GPIB link number, `A` is the GPIB address, and `param_index` is the command table index.

```
record(stringin, "$(P):IDN") {
    field(DTYP, "MyInstrument")
    field(INP,  "#L$(L) A$(A) @0")
    field(SCAN, "Passive")
    field(PINI, "YES")
}

record(bo, "$(P):Reset") {
    field(DTYP, "MyInstrument")
    field(OUT,  "#L$(L) A$(A) @1")
    field(ZNAM, "Reset")
    field(ONAM, "Reset")
}

record(ai, "$(P):Voltage") {
    field(DTYP, "MyInstrument")
    field(INP,  "#L$(L) A$(A) @6")
    field(EGU,  "V")
    field(PREC, "3")
    field(SCAN, "1 second")
}

record(ao, "$(P):SetVoltage") {
    field(DTYP, "MyInstrument")
    field(OUT,  "#L$(L) A$(A) @7")
    field(EGU,  "V")
    field(PREC, "3")
    field(DRVH, "100")
    field(DRVL, "0")
}
```

---

## 11. Makefile Integration

```makefile
LIBRARY_IOC += devMyInstrument

devMyInstrument_SRCS += devMyInstrument.c
devMyInstrument_LIBS += asyn
devMyInstrument_LIBS += $(EPICS_BASE_IOC_LIBS)

DBD += devMyInstrument.dbd
```

---

## 12. VXI-11 Configuration (LAN/GPIB Gateways)

For instruments connected through LAN/GPIB gateways (e.g., Agilent E5810):

```
# In st.cmd:
vxi11Configure("GPIB1", "192.168.1.200", 0, 0.0, "gpib0")
```

Parameters:
| # | Name | Description |
|---|------|-------------|
| 1 | portName | Asyn port name |
| 2 | hostName | Gateway IP or hostname |
| 3 | flags | 0 (reserved) |
| 4 | timeout | Lock timeout (0 = default) |
| 5 | vxiName | VXI device name (`"gpib0"`, `"inst0"`, etc.) |

---

## 13. Key Rules and Pitfalls

1. **`DSET_AI` must always be defined** even if the instrument has no analog inputs. The `init_ai` function is the entry point for all initialization.

2. **`#include <devGpib.h>` MUST come AFTER all DSET defines.** The header file generates the dset structures based on which macros are defined.

3. **EFAST output tables must end with `0` (NULL).** Omitting this causes crashes.

4. **The `format` field** uses standard C scanf/printf format strings. For reads (GPIBREAD), it's scanf. For writes (GPIBWRITE), it's printf.

5. **The `msgLen` field** sets the read buffer size. Make it large enough for the longest expected response. If too small, data is silently truncated.

6. **For GPIBWRITE, `cmd` is NULL.** The formatted output is sent directly. For GPIBREAD, `cmd` is the query command and `format` parses the response.

7. **The `respond2Writes` field** in `devGpibParmBlock`: set to `-1` for instruments that do NOT send a response after write commands. Set to `0` or a positive delay (seconds) if the instrument sends a response that must be read.

8. **Parameter index in the database `@n`** is zero-based and corresponds to the array index in `gpibCmds[]`.

9. **GPIB_IO link format** is `#Ln An @param` where `L=link_number`, `A=gpib_address`. This is different from asyn INST_IO format.

10. **`timeWindow`** suppresses I/O for a period after a timeout occurs. This prevents flooding a non-responsive instrument with requests.
