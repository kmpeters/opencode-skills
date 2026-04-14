---
name: epics-ca-client
description: Write EPICS Channel Access client programs in C/C++ -- context management, channel creation, get/put/monitor operations, callbacks, DBR types, and error handling
---

# EPICS Channel Access Client Skill

You are an expert at writing EPICS Channel Access (CA) client programs in C. Channel Access is the classic EPICS network protocol for reading, writing, and monitoring Process Variables (PVs). You understand the full CA client API, callback patterns, DBR type system, and common pitfalls.

---

## 1. Headers and Linking

### 1.1 Required Header

```c
#include "cadef.h"    /* includes caerr.h, db_access.h, caeventmask.h */
```

### 1.2 Makefile

```makefile
PROD_HOST += myClient
myClient_SRCS += myClient.c
myClient_LIBS += $(EPICS_BASE_HOST_LIBS)
```

Use `PROD_HOST` (not `PROD_IOC`) for standalone client programs. Link with `$(EPICS_BASE_HOST_LIBS)` which includes `ca` and `Com`.

---

## 2. Context Management

Every CA client must create a context before using any CA functions.

### 2.1 Preemptive vs. Non-Preemptive Modes

| Mode | When to Use | Threading |
|------|-------------|-----------|
| `ca_disable_preemptive_callback` | Simple single-threaded programs | Callbacks only fire inside `ca_pend_event()` or `ca_poll()` |
| `ca_enable_preemptive_callback` | Multi-threaded apps, GUIs, servers | Callbacks fire from CA internal threads at any time; user must protect shared data with mutexes |

### 2.2 Context Lifecycle

```c
/* Create context -- MUST be first CA call in a thread */
int status = ca_context_create(ca_enable_preemptive_callback);

/* ... use CA ... */

/* Destroy context -- cleans up all channels and subscriptions */
ca_context_destroy();
```

### 2.3 Multi-threaded Context Sharing

```c
/* In the main thread: */
struct ca_client_context *ctx = ca_current_context();

/* In a worker thread: */
ca_attach_context(ctx);    /* Attach to existing context */
/* ... use CA ... */
ca_detach_context();       /* Detach when done */
```

Only one thread should call `ca_context_destroy()`. All other threads must detach first.

---

## 3. Channel Creation and Connection

### 3.1 Creating Channels

```c
chid myChannel;

/* With connection callback (asynchronous connection) */
int status = ca_create_channel(
    "PV:NAME",              /* PV name */
    connectionCallback,     /* Connection state callback (or NULL) */
    pUserData,              /* User data pointer, retrievable via ca_puser() */
    CA_PRIORITY_DEFAULT,    /* Priority 0-99 */
    &myChannel              /* Output: channel identifier */
);

/* Without connection callback (synchronous via ca_pend_io) */
status = ca_create_channel("PV:NAME", NULL, NULL, CA_PRIORITY_DEFAULT, &myChannel);
SEVCHK(status, "ca_create_channel");
status = ca_pend_io(5.0);  /* Block until connected or timeout */
if (status != ECA_NORMAL) {
    fprintf(stderr, "Channel not found\n");
}
```

### 3.2 Connection Callback

```c
void connectionCallback(struct connection_handler_args args)
{
    chid chan = args.chid;

    if (args.op == CA_OP_CONN_UP) {
        printf("Connected: %s (%s, %ld elements)\n",
            ca_name(chan),
            dbr_type_to_text(ca_field_type(chan)),
            ca_element_count(chan));
    } else {  /* CA_OP_CONN_DOWN */
        printf("Disconnected: %s\n", ca_name(chan));
    }
}
```

**IMPORTANT:** When a connection callback is provided, `ca_pend_io()` does NOT wait for connection. Use `ca_pend_event()` or check `ca_state(chan) == cs_conn` instead.

### 3.3 Channel Query Functions

```c
const char *name = ca_name(chan);              /* PV name */
short type       = ca_field_type(chan);        /* Native DBF type (TYPENOTCONN=-1 if disconnected) */
unsigned long n  = ca_element_count(chan);     /* Array size (0 if disconnected) */
const char *host = ca_host_name(chan);         /* Server hostname (not thread-safe) */
unsigned rAccess = ca_read_access(chan);       /* 1 if readable */
unsigned wAccess = ca_write_access(chan);      /* 1 if writable */

enum channel_state state = ca_state(chan);
/* cs_never_conn, cs_prev_conn, cs_conn, cs_closed */

void *userData = ca_puser(chan);               /* Get user pointer */
ca_set_puser(chan, newPtr);                    /* Set user pointer */
```

### 3.4 Clearing Channels

```c
ca_clear_channel(myChannel);
```

---

## 4. Read Operations

### 4.1 Synchronous Get

```c
double value;
SEVCHK(ca_get(DBR_DOUBLE, myChannel, &value), "ca_get");
SEVCHK(ca_pend_io(5.0), "ca_pend_io");
/* value is now valid */
printf("Value = %f\n", value);
```

**CRITICAL:** The value written by `ca_get()` is NOT valid until `ca_pend_io()` returns `ECA_NORMAL`. This is the most common CA client bug.

### 4.2 Synchronous Get with Status and Timestamp

```c
struct dbr_time_double result;
SEVCHK(ca_get(DBR_TIME_DOUBLE, myChannel, &result), "ca_get");
SEVCHK(ca_pend_io(5.0), "ca_pend_io");
printf("Value=%f Status=%d Severity=%d\n",
    result.value, result.status, result.severity);
```

### 4.3 Array Get

```c
double data[100];
SEVCHK(ca_array_get(DBR_DOUBLE, 100, myChannel, data), "ca_array_get");
SEVCHK(ca_pend_io(5.0), "ca_pend_io");
```

### 4.4 Asynchronous Get (Callback)

```c
void getCallback(struct event_handler_args args)
{
    if (args.status != ECA_NORMAL) {
        fprintf(stderr, "Get failed: %s\n", ca_message(args.status));
        return;
    }
    double value = *(const double *)args.dbr;
    printf("%s = %f\n", ca_name(args.chid), value);
}

SEVCHK(ca_get_callback(DBR_DOUBLE, myChannel, getCallback, NULL), "ca_get_callback");
ca_flush_io();  /* Send the request */
```

---

## 5. Write Operations

### 5.1 Fire-and-Forget Put

```c
double value = 42.0;
SEVCHK(ca_put(DBR_DOUBLE, myChannel, &value), "ca_put");
SEVCHK(ca_flush_io(), "ca_flush_io");  /* Send the request */
```

### 5.2 Put with Completion Callback

```c
void putCallback(struct event_handler_args args)
{
    if (args.status != ECA_NORMAL) {
        fprintf(stderr, "Put failed: %s\n", ca_message(args.status));
    } else {
        printf("Put complete: %s\n", ca_name(args.chid));
    }
}

double value = 42.0;
SEVCHK(ca_put_callback(DBR_DOUBLE, myChannel, &value, putCallback, NULL),
    "ca_put_callback");
ca_flush_io();
```

### 5.3 String Put

```c
dbr_string_t value;
strncpy(value, "Hello", sizeof(value) - 1);
value[sizeof(value) - 1] = '\0';
SEVCHK(ca_put(DBR_STRING, myChannel, &value), "ca_put");
ca_flush_io();
```

### 5.4 Array Put

```c
double data[100];
/* ... fill data ... */
SEVCHK(ca_array_put(DBR_DOUBLE, 100, myChannel, data), "ca_array_put");
ca_flush_io();
```

---

## 6. Subscriptions (Monitors)

### 6.1 Creating a Subscription

```c
void monitorCallback(struct event_handler_args args)
{
    if (args.status != ECA_NORMAL) {
        fprintf(stderr, "Monitor error: %s\n", ca_message(args.status));
        return;
    }

    const struct dbr_time_double *pdata =
        (const struct dbr_time_double *)args.dbr;

    printf("%s = %f (severity=%d)\n",
        ca_name(args.chid), pdata->value, pdata->severity);
}

evid mySubscription;
SEVCHK(ca_create_subscription(
    DBR_TIME_DOUBLE,         /* Data type to receive */
    1,                       /* Element count (0 = native count) */
    myChannel,
    DBE_VALUE | DBE_ALARM,   /* Event mask */
    monitorCallback,
    NULL,                    /* User argument */
    &mySubscription          /* Output: subscription ID (can be NULL) */
), "ca_create_subscription");

ca_flush_io();
```

### 6.2 Event Masks

| Mask | Description |
|------|-------------|
| `DBE_VALUE` | Value exceeds monitor deadband (MDEL) |
| `DBE_ALARM` | Alarm state changes |
| `DBE_LOG` / `DBE_ARCHIVE` | Value exceeds archive deadband (ADEL) |
| `DBE_PROPERTY` | Property (metadata) changes |

Common combinations:
- `DBE_VALUE | DBE_ALARM` -- most common, tracks value and alarm changes
- `DBE_VALUE | DBE_ALARM | DBE_PROPERTY` -- includes metadata changes

### 6.3 Clearing a Subscription

```c
ca_clear_subscription(mySubscription);
```

---

## 7. I/O Completion Functions

### 7.1 ca_pend_io vs. ca_pend_event

| Function | Purpose | Returns |
|----------|---------|---------|
| `ca_pend_io(timeout)` | Wait for `ca_get()` and NULL-callback `ca_create_channel()` to complete | `ECA_NORMAL` on success, `ECA_TIMEOUT` on timeout |
| `ca_pend_event(timeout)` | Process callbacks for `timeout` seconds | **Always returns `ECA_TIMEOUT`** (this is normal!) |
| `ca_flush_io()` | Send buffered requests immediately | `ECA_NORMAL` |
| `ca_poll()` | Quick non-blocking event poll (= `ca_pend_event(1e-12)`) | `ECA_TIMEOUT` |
| `ca_test_io()` | Non-blocking check if pending I/O is done | `ECA_IODONE` or `ECA_IOINPROGRESS` |

**CRITICAL:** `ca_pend_event()` returning `ECA_TIMEOUT` is NORMAL and expected. It means the timeout expired, which is the intended behavior (it always waits the full duration).

### 7.2 Buffering

All CA requests are buffered internally. They are NOT sent to the server until one of these functions is called:
- `ca_flush_io()`
- `ca_pend_io()`
- `ca_pend_event()`
- `ca_poll()`

Always call one of these after issuing requests.

---

## 8. DBR Type System

### 8.1 Type Categories

| Category | Types | What's Included |
|----------|-------|-----------------|
| Plain | `DBR_STRING`..`DBR_DOUBLE` (0-6) | Value only |
| Status | `DBR_STS_STRING`..`DBR_STS_DOUBLE` (7-13) | Value + status + severity |
| Time | `DBR_TIME_STRING`..`DBR_TIME_DOUBLE` (14-20) | Value + status + severity + timestamp |
| Graphic | `DBR_GR_STRING`..`DBR_GR_DOUBLE` (21-27) | Value + status + severity + units + display/alarm limits |
| Control | `DBR_CTRL_STRING`..`DBR_CTRL_DOUBLE` (28-34) | Value + all of graphic + control limits |

### 8.2 C Type Mapping

| DBR Type | C Value Type | Notes |
|----------|-------------|-------|
| `DBR_STRING` | `dbr_string_t` (char[40]) | Max 40 characters |
| `DBR_SHORT` / `DBR_INT` | `dbr_short_t` (int16) | |
| `DBR_FLOAT` | `dbr_float_t` (float32) | |
| `DBR_ENUM` | `dbr_enum_t` (uint16) | Index value |
| `DBR_CHAR` | `dbr_char_t` (uint8) | |
| `DBR_LONG` | `dbr_long_t` (int32) | Note: 32-bit, not 64-bit |
| `DBR_DOUBLE` | `dbr_double_t` (float64) | |

### 8.3 Commonly Used Structures

```c
/* DBR_TIME_DOUBLE -- value with timestamp */
struct dbr_time_double {
    dbr_short_t    status;
    dbr_short_t    severity;
    epicsTimeStamp stamp;
    dbr_long_t     RISC_pad;
    dbr_double_t   value;
};

/* DBR_CTRL_DOUBLE -- value with full metadata */
struct dbr_ctrl_double {
    dbr_short_t    status;
    dbr_short_t    severity;
    dbr_short_t    precision;
    dbr_short_t    RISC_pad;
    char           units[MAX_UNITS_SIZE];        /* 8 bytes */
    dbr_double_t   upper_disp_limit;
    dbr_double_t   lower_disp_limit;
    dbr_double_t   upper_alarm_limit;
    dbr_double_t   upper_warning_limit;
    dbr_double_t   lower_warning_limit;
    dbr_double_t   lower_alarm_limit;
    dbr_double_t   upper_ctrl_limit;
    dbr_double_t   lower_ctrl_limit;
    dbr_double_t   value;
};

/* DBR_CTRL_ENUM -- enumeration with string labels */
struct dbr_ctrl_enum {
    dbr_short_t    status;
    dbr_short_t    severity;
    dbr_short_t    no_str;                       /* Number of enum strings */
    char           strs[MAX_ENUM_STATES][MAX_ENUM_STRING_SIZE]; /* 16 x 26 */
    dbr_enum_t     value;
};
```

### 8.4 Type Conversion Macros

```c
dbr_type_to_text(type)           /* DBR code -> "DBR_DOUBLE" etc. */
dbf_type_to_DBR(type)            /* DBF -> corresponding plain DBR */
dbf_type_to_DBR_TIME(type)       /* DBF -> DBR_TIME_xxx */
dbf_type_to_DBR_CTRL(type)       /* DBF -> DBR_CTRL_xxx */
dbr_size_n(TYPE, COUNT)          /* Byte size for TYPE with COUNT elements */
dbr_value_ptr(PDBR, DBR_TYPE)   /* Pointer to value within a DBR struct */
VALID_DB_REQ(type)               /* Is it a valid DBR type? */
```

---

## 9. Error Handling

### 9.1 SEVCHK Macro

```c
/* Checks status; if failure, prints message with file/line and aborts for severe errors */
SEVCHK(ca_get(DBR_DOUBLE, chan, &val), "Reading temperature");
```

### 9.2 Manual Error Checking

```c
int status = ca_create_channel("PV:NAME", NULL, NULL, 0, &chan);
if (status != ECA_NORMAL) {
    fprintf(stderr, "Error: %s\n", ca_message(status));
    return -1;
}
```

### 9.3 Exception Handler

```c
void exceptionHandler(struct exception_handler_args args)
{
    const char *name = args.chid ? ca_name(args.chid) : "unknown";
    fprintf(stderr, "CA Exception: %s context=%s channel=%s\n",
        ca_message(args.stat), args.ctx, name);
}

ca_add_exception_event(exceptionHandler, NULL);
```

### 9.4 Key Status Codes

| Code | Severity | Meaning |
|------|----------|---------|
| `ECA_NORMAL` | SUCCESS | Normal completion |
| `ECA_TIMEOUT` | WARNING | I/O timeout expired |
| `ECA_DISCONN` | WARNING | Channel disconnected |
| `ECA_BADTYPE` | ERROR | Invalid DBR type |
| `ECA_ALLOCMEM` | WARNING | Memory allocation failed |
| `ECA_NORDACCESS` | WARNING | Read access denied |
| `ECA_NOWTACCESS` | WARNING | Write access denied |
| `ECA_BADCHID` | ERROR | Corrupted channel ID |
| `ECA_EVDISALLOW` | ERROR | Inappropriate call within callback |
| `ECA_IODONE` | INFO | All I/O completed (from `ca_test_io()`) |
| `ECA_IOINPROGRESS` | INFO | I/O still in progress (from `ca_test_io()`) |

---

## 10. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EPICS_CA_ADDR_LIST` | (empty) | Space-separated server addresses for PV search |
| `EPICS_CA_AUTO_ADDR_LIST` | `YES` | Auto-detect broadcast addresses |
| `EPICS_CA_SERVER_PORT` | `5064` | CA server TCP/UDP port |
| `EPICS_CA_REPEATER_PORT` | `5065` | CA repeater UDP port |
| `EPICS_CA_CONN_TMO` | `30.0` | Connection timeout (seconds) |
| `EPICS_CA_BEACON_PERIOD` | `15.0` | Server beacon interval (seconds) |
| `EPICS_CA_MAX_ARRAY_BYTES` | `16384` | Maximum array transfer size in bytes |

Set `EPICS_CA_MAX_ARRAY_BYTES` to a large value for large waveform transfers.

---

## 11. Complete Examples

### 11.1 Simple Synchronous Get

```c
#include <stdio.h>
#include <stdlib.h>
#include "cadef.h"

int main(int argc, char **argv)
{
    double value;
    chid chan;

    if (argc != 2) {
        fprintf(stderr, "Usage: %s pvname\n", argv[0]);
        return 1;
    }

    SEVCHK(ca_context_create(ca_disable_preemptive_callback),
        "ca_context_create");
    SEVCHK(ca_create_channel(argv[1], NULL, NULL, CA_PRIORITY_DEFAULT, &chan),
        "ca_create_channel");
    SEVCHK(ca_pend_io(5.0), "ca_pend_io (connect)");

    SEVCHK(ca_get(DBR_DOUBLE, chan, &value), "ca_get");
    SEVCHK(ca_pend_io(5.0), "ca_pend_io (get)");

    printf("%s = %f\n", argv[1], value);

    ca_clear_channel(chan);
    ca_context_destroy();
    return 0;
}
```

### 11.2 Monitor with Connection Handler

```c
#include <stdio.h>
#include <stdlib.h>
#include "cadef.h"

typedef struct {
    chid chan;
    evid sub;
} MyPV;

static void eventCB(struct event_handler_args args)
{
    if (args.status != ECA_NORMAL) {
        fprintf(stderr, "%s: %s\n", ca_name(args.chid), ca_message(args.status));
        return;
    }
    const struct dbr_time_double *p = (const struct dbr_time_double *)args.dbr;
    printf("%s = %f (sev=%d)\n", ca_name(args.chid), p->value, p->severity);
}

static void connCB(struct connection_handler_args args)
{
    MyPV *pv = (MyPV *)ca_puser(args.chid);

    if (args.op == CA_OP_CONN_UP) {
        printf("Connected: %s\n", ca_name(args.chid));

        /* Create or re-create subscription on connect */
        if (pv->sub) {
            ca_clear_subscription(pv->sub);
            pv->sub = NULL;
        }
        SEVCHK(ca_create_subscription(
            DBR_TIME_DOUBLE, 0, args.chid,
            DBE_VALUE | DBE_ALARM,
            eventCB, pv, &pv->sub
        ), "ca_create_subscription");
        ca_flush_io();
    } else {
        printf("Disconnected: %s\n", ca_name(args.chid));
    }
}

int main(int argc, char **argv)
{
    MyPV pv = {0};

    if (argc != 2) {
        fprintf(stderr, "Usage: %s pvname\n", argv[0]);
        return 1;
    }

    SEVCHK(ca_context_create(ca_disable_preemptive_callback),
        "ca_context_create");
    SEVCHK(ca_add_exception_event(NULL, NULL), "exception handler");
    SEVCHK(ca_create_channel(argv[1], connCB, &pv, CA_PRIORITY_DEFAULT, &pv.chan),
        "ca_create_channel");

    /* Block forever processing callbacks */
    ca_pend_event(0.0);

    ca_context_destroy();
    return 0;
}
```

### 11.3 Put with Completion

```c
#include <stdio.h>
#include "cadef.h"
#include "epicsEvent.h"

static epicsEventId done;

static void putCB(struct event_handler_args args)
{
    if (args.status != ECA_NORMAL)
        fprintf(stderr, "Put failed: %s\n", ca_message(args.status));
    else
        printf("Put completed: %s\n", ca_name(args.chid));
    epicsEventSignal(done);
}

int main(int argc, char **argv)
{
    chid chan;
    double value;

    if (argc != 3) { fprintf(stderr, "Usage: %s pv value\n", argv[0]); return 1; }
    value = atof(argv[2]);
    done = epicsEventMustCreate(epicsEventEmpty);

    SEVCHK(ca_context_create(ca_enable_preemptive_callback), "context");
    SEVCHK(ca_create_channel(argv[1], NULL, NULL, 0, &chan), "channel");
    SEVCHK(ca_pend_io(5.0), "connect");

    SEVCHK(ca_put_callback(DBR_DOUBLE, chan, &value, putCB, NULL), "put_cb");
    ca_flush_io();

    epicsEventMustWait(done);

    ca_clear_channel(chan);
    ca_context_destroy();
    epicsEventDestroy(done);
    return 0;
}
```

---

## 12. Key Rules and Pitfalls

1. **`ca_get()` data is NOT valid until `ca_pend_io()` completes.** The value buffer is written asynchronously. Reading it before `ca_pend_io()` returns is undefined behavior.

2. **`ca_pend_event()` returning `ECA_TIMEOUT` is normal.** It means the timeout expired. This is the expected return value, not an error.

3. **All requests are buffered.** Nothing is sent to the server until `ca_flush_io()`, `ca_pend_io()`, or `ca_pend_event()` is called.

4. **When a connection callback is provided, `ca_pend_io()` does NOT wait for connection.** Use `ca_pend_event()` or poll `ca_state()` instead.

5. **`ca_host_name()` is NOT thread-safe.** Use `ca_get_host_name()` (with a user-supplied buffer) in multi-threaded code.

6. **In non-preemptive mode, callbacks only fire inside `ca_pend_event()` or `ca_poll()`.** You must call these periodically.

7. **In preemptive mode, callbacks fire from CA threads.** Protect shared data with `epicsMutex`.

8. **`dbr_long_t` is 32-bit**, not 64-bit. This is a historical naming issue.

9. **Do not call `ca_clear_channel()` or `ca_clear_subscription()` from within a callback** for the same channel. This can cause deadlocks or use-after-free. Use `ECA_EVDISALLOW` to detect this.

10. **Set `EPICS_CA_MAX_ARRAY_BYTES`** before creating the context if you need to transfer arrays larger than 16KB.

11. **`ca_create_subscription()` with `count=0`** uses the server's native element count. The count may vary between callbacks (variable-length arrays).

12. **Always install an exception handler** via `ca_add_exception_event()` for production code. The default handler prints to stderr and may abort on severe errors.
