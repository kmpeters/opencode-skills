---
name: epics-libcom
description: Use EPICS libCom OS-independent APIs for module development -- threading, mutexes, events, message queues, ring buffers, timers, time stamps, error logging, linked lists, and iocsh registration
---

# EPICS libCom Skill

You are an expert at using the EPICS libCom library, which provides OS-independent abstractions for threading, synchronization, data structures, timing, and error logging. libCom is the foundational library used by virtually every EPICS module.

---

## 1. Threading (epicsThread)

### 1.1 Creating Threads

```c
#include "epicsThread.h"

/* Thread function signature */
typedef void (*EPICSTHREADFUNC)(void *parm);

/* Simple thread creation (not joinable) */
epicsThreadId tid = epicsThreadCreate(
    "myThread",                                        /* Thread name */
    epicsThreadPriorityMedium,                         /* Priority */
    epicsThreadGetStackSize(epicsThreadStackMedium),    /* Stack size */
    myThreadFunc,                                      /* Entry function */
    pUserArg                                           /* User argument */
);

/* Must-succeed variant (calls cantProceed on failure) */
epicsThreadId tid = epicsThreadMustCreate(
    "myThread", epicsThreadPriorityMedium,
    epicsThreadGetStackSize(epicsThreadStackMedium),
    myThreadFunc, pUserArg
);
```

### 1.2 Joinable Threads (EPICS 7+)

```c
epicsThreadOpts opts = EPICS_THREAD_OPTS_INIT;
opts.priority = epicsThreadPriorityMedium;
opts.stackSize = epicsThreadGetStackSize(epicsThreadStackMedium);
opts.joinable = 1;

epicsThreadId tid = epicsThreadCreateOpt("myThread", myFunc, pArg, &opts);

/* ... later, wait for thread to finish ... */
epicsThreadMustJoin(tid);   /* Blocks until thread exits */
```

### 1.3 Priority Constants

| Constant | Value | Typical Use |
|----------|-------|-------------|
| `epicsThreadPriorityMin` | 0 | Background tasks |
| `epicsThreadPriorityLow` | 10 | Low-priority work |
| `epicsThreadPriorityCAServerLow` | 20 | CA server |
| `epicsThreadPriorityCAServerHigh` | 40 | CA server high |
| `epicsThreadPriorityMedium` | 50 | General purpose |
| `epicsThreadPriorityScanLow` | 60 | Slow scan rates |
| `epicsThreadPriorityScanHigh` | 70 | Fast scan rates |
| `epicsThreadPriorityHigh` | 90 | Critical tasks |
| `epicsThreadPriorityIocsh` | 91 | IOC shell |
| `epicsThreadPriorityMax` | 99 | Maximum |

### 1.4 Stack Size Classes

```c
epicsThreadGetStackSize(epicsThreadStackSmall)    /* Small stack */
epicsThreadGetStackSize(epicsThreadStackMedium)   /* Medium stack (default) */
epicsThreadGetStackSize(epicsThreadStackBig)      /* Large stack */
```

### 1.5 Thread Utilities

```c
epicsThreadSleep(1.5);                       /* Sleep for 1.5 seconds */
epicsThreadId self = epicsThreadGetIdSelf(); /* Get current thread ID */
const char *name = epicsThreadGetNameSelf(); /* Get current thread name */
epicsThreadSuspendSelf();                    /* Suspend current thread */
epicsThreadResume(tid);                      /* Resume a suspended thread */
int ncpus = epicsThreadGetCPUs();            /* Number of CPUs */
```

### 1.6 One-Time Initialization

```c
static epicsThreadOnceId onceFlag = EPICS_THREAD_ONCE_INIT;

static void myInitFunc(void *arg)
{
    /* Initialization code -- guaranteed to run exactly once */
}

void myFunction(void)
{
    epicsThreadOnce(&onceFlag, myInitFunc, NULL);
    /* ... initialization is complete ... */
}
```

### 1.7 Thread-Local Storage

```c
/* C API */
epicsThreadPrivateId key = epicsThreadPrivateCreate();
epicsThreadPrivateSet(key, myData);
void *data = epicsThreadPrivateGet(key);
epicsThreadPrivateDelete(key);
```

```cpp
/* C++ typed template */
epicsThreadPrivate<MyClass> tls;
tls.set(new MyClass());
MyClass *obj = tls.get();
```

### 1.8 C++ Thread Class

```cpp
#include "epicsThread.h"

class MyThread : public epicsThreadRunable {
    epicsThread thread;
    bool running;
public:
    MyThread()
        : thread(*this, "myThread",
                 epicsThreadGetStackSize(epicsThreadStackMedium),
                 epicsThreadPriorityMedium)
        , running(true)
    {
        thread.start();
    }

    ~MyThread() {
        running = false;
        thread.exitWait();
    }

    void run() override {
        while (running) {
            /* ... do work ... */
            epicsThreadSleep(1.0);
        }
    }
};
```

---

## 2. Mutual Exclusion (epicsMutex)

Recursive mutex with priority inheritance (where OS supports it).

### 2.1 C API

```c
#include "epicsMutex.h"

epicsMutexId lock = epicsMutexMustCreate();

epicsMutexLock(lock);       /* Block until acquired */
/* ... critical section ... */
epicsMutexUnlock(lock);

/* Or with must-succeed: */
epicsMutexMustLock(lock);   /* Asserts on failure */
/* ... critical section ... */
epicsMutexUnlock(lock);

/* Try without blocking */
if (epicsMutexTryLock(lock) == epicsMutexLockOK) {
    /* ... got the lock ... */
    epicsMutexUnlock(lock);
}

epicsMutexDestroy(lock);
```

### 2.2 C++ RAII Guard (Recommended)

```cpp
#include "epicsMutex.h"

epicsMutex myLock;

{
    epicsMutex::guard_t G(myLock);   /* Acquires lock */
    /* ... critical section ... */
}   /* Lock automatically released */
```

### 2.3 Temporary Lock Release

```cpp
epicsMutex myLock;

{
    epicsMutex::guard_t G(myLock);     /* Lock acquired */
    /* ... work with lock held ... */

    {
        epicsMutex::release_t R(G);    /* Temporarily releases lock */
        /* ... do I/O without holding lock ... */
    }   /* Lock re-acquired */

    /* ... continue with lock held ... */
}   /* Lock released */
```

---

## 3. Event Semaphore (epicsEvent)

Binary semaphore for thread synchronization (producer/consumer pattern).

### 3.1 C API

```c
#include "epicsEvent.h"

epicsEventId evt = epicsEventMustCreate(epicsEventEmpty);

/* Producer thread: */
epicsEventSignal(evt);              /* Signal the event (idempotent) */

/* Consumer thread: */
epicsEventMustWait(evt);            /* Block until signaled */

/* With timeout: */
if (epicsEventWaitWithTimeout(evt, 5.0) == epicsEventOK) {
    /* Signaled within 5 seconds */
} else {
    /* Timeout */
}

/* Non-blocking check: */
if (epicsEventTryWait(evt) == epicsEventOK) {
    /* Was signaled */
}

epicsEventDestroy(evt);
```

### 3.2 C++ API

```cpp
#include "epicsEvent.h"

epicsEvent event;

/* Producer: */
event.signal();

/* Consumer: */
event.wait();                    /* Block until signaled */
bool ok = event.wait(5.0);      /* Timeout variant, returns false on timeout */
bool ok = event.tryWait();       /* Non-blocking */
```

### 3.3 Initial States

| State | Description |
|-------|-------------|
| `epicsEventEmpty` | Not signaled (consumer will block immediately) |
| `epicsEventFull` | Pre-signaled (first wait returns immediately) |

---

## 4. Message Queue (epicsMessageQueue)

Thread-safe FIFO message passing between threads.

### 4.1 C API

```c
#include "epicsMessageQueue.h"

/* Create queue: 10 messages, max 256 bytes each */
epicsMessageQueueId queue = epicsMessageQueueCreate(10, 256);

/* Producer: send a message */
typedef struct { int id; double value; } MyMessage;
MyMessage msg = {1, 42.0};

int status = epicsMessageQueueTrySend(queue, &msg, sizeof(msg));
if (status != 0) { /* Queue full */ }

/* Or blocking send: */
epicsMessageQueueSend(queue, &msg, sizeof(msg));

/* Consumer: receive a message */
MyMessage received;
int nbytes = epicsMessageQueueReceive(queue, &received, sizeof(received));
if (nbytes > 0) {
    printf("Received: id=%d value=%f\n", received.id, received.value);
}

/* With timeout: */
nbytes = epicsMessageQueueReceiveWithTimeout(queue, &received, sizeof(received), 5.0);

/* Check pending count: */
int pending = epicsMessageQueuePending(queue);

epicsMessageQueueDestroy(queue);
```

### 4.2 C++ API

```cpp
epicsMessageQueue queue(10, 256);

queue.send(&msg, sizeof(msg));           /* Blocking send */
queue.trySend(&msg, sizeof(msg));        /* Non-blocking */

int n = queue.receive(&msg, sizeof(msg));         /* Blocking receive */
int n = queue.receive(&msg, sizeof(msg), 5.0);    /* With timeout */
int n = queue.tryReceive(&msg, sizeof(msg));       /* Non-blocking */

int pending = queue.pending();
```

---

## 5. Ring Buffers

Lock-free (single-producer/single-consumer) or spinlock-protected circular buffers.

### 5.1 Ring Pointer (for pointer-sized items)

```cpp
#include "epicsRingPointer.h"

/* C++ template API */
epicsRingPointer<MyStruct> ring(100, true);  /* size=100, locked=true */

MyStruct *item = new MyStruct();
bool ok = ring.push(item);     /* Returns false if full */
MyStruct *got = ring.pop();    /* Returns NULL if empty */

int free = ring.getFree();
int used = ring.getUsed();
bool empty = ring.isEmpty();
bool full = ring.isFull();
ring.flush();                  /* Discard all items */
```

```c
/* C API */
epicsRingPointerId ring = epicsRingPointerLockedCreate(100);
epicsRingPointerPush(ring, item);
void *item = epicsRingPointerPop(ring);
epicsRingPointerDelete(ring);
```

### 5.2 Ring Bytes (for raw byte streams)

```c
#include "epicsRingBytes.h"

epicsRingBytesId ring = epicsRingBytesCreate(4096);

/* Write data */
int nWritten = epicsRingBytesPut(ring, buffer, nbytes);

/* Read data */
int nRead = epicsRingBytesGet(ring, buffer, maxBytes);

int freeBytes = epicsRingBytesFreeBytes(ring);
int usedBytes = epicsRingBytesUsedBytes(ring);

epicsRingBytesDelete(ring);
```

---

## 6. Timers (epicsTimer)

### 6.1 C++ Callback Interface (Recommended)

```cpp
#include "epicsTimer.h"

class MyTimerNotify : public epicsTimerNotify {
public:
    expireStatus expire(const epicsTime &currentTime) override {
        /* Timer fired -- do periodic work */
        printf("Timer expired at %s\n", currentTime.strftime("%H:%M:%S"));

        /* Return restart to re-fire, or noRestart to stop */
        return expireStatus(restart, 1.0);  /* Re-fire in 1.0 seconds */
    }
};

/* Create a timer queue (shared, thread-managed) */
epicsTimerQueueActive &queue =
    epicsTimerQueueActive::allocate(true, epicsThreadPriorityMedium);

/* Create and start a timer */
MyTimerNotify notify;
epicsTimer &timer = queue.createTimer();
timer.start(notify, 1.0);   /* First fire in 1.0 seconds */

/* Cancel the timer */
timer.cancel();

/* Cleanup */
timer.destroy();
queue.release();
```

### 6.2 C API

```c
#include "epicsTimer.h"

void myCallback(void *pPrivate) {
    printf("Timer fired!\n");
}

/* Create a timer queue */
epicsTimerQueueId queue = epicsTimerQueueAllocate(1, epicsThreadPriorityMedium);

/* Create and start a timer */
epicsTimerId timer = epicsTimerQueueCreateTimer(queue, myCallback, myArg);
epicsTimerStartDelay(timer, 2.0);   /* Fire in 2.0 seconds */

/* Cancel */
epicsTimerCancel(timer);

/* Cleanup */
epicsTimerQueueDestroyTimer(queue, timer);
epicsTimerQueueRelease(queue);
```

---

## 7. Time (epicsTime)

### 7.1 EPICS Time Stamp

```c
#include "epicsTime.h"

/* EPICS epoch: January 1, 1990 00:00:00 UTC */
/* POSIX_TIME_AT_EPICS_EPOCH = 631152000 */

epicsTimeStamp ts;
epicsTimeGetCurrent(&ts);   /* Get current time */

/* Convert to string */
char buf[64];
epicsTimeToStrftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S.%06f", &ts);
printf("Time: %s\n", buf);

/* Difference in seconds */
epicsTimeStamp ts2;
epicsTimeGetCurrent(&ts2);
double diff = epicsTimeDiffInSeconds(&ts2, &ts);
```

### 7.2 C++ Time Class

```cpp
epicsTime now = epicsTime::getCurrent();

/* Format with fractional seconds (%0nf extension) */
char buf[64];
now.strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S.%06f");

/* Arithmetic */
epicsTime later = now + 5.0;      /* Add 5 seconds */
double elapsed = later - now;      /* Difference in seconds */

/* Comparisons */
if (now < later) { /* ... */ }

/* Convert to/from POSIX */
time_t posix = time_t_wrapper(now);
```

### 7.3 Monotonic Clock

```c
/* High-resolution monotonic clock (not wall-clock) */
epicsUInt64 ticks = epicsMonotonicGet();
double resolution = epicsMonotonicResolution();  /* Seconds per tick */
```

### 7.4 Special Timestamp Events

| Constant | Value | Purpose |
|----------|-------|---------|
| `epicsTimeEventCurrentTime` | 0 | Use current time |
| `epicsTimeEventBestTime` | -1 | Best available time source |
| `epicsTimeEventDeviceTime` | -2 | Device support provides timestamp |

---

## 8. Error Logging (errlog)

### 8.1 Basic Logging

```c
#include "errlog.h"

/* Printf-style logging (routed through errlog system) */
errlogPrintf("Processing channel %s\n", channelName);

/* Severity-tagged logging */
errlogSevPrintf(errlogInfo, "Initialized port %s\n", portName);
errlogSevPrintf(errlogMinor, "Retrying connection to %s\n", host);
errlogSevPrintf(errlogMajor, "Lost connection to %s\n", host);
errlogSevPrintf(errlogFatal, "Cannot allocate memory\n");
```

### 8.2 Severity Levels

| Level | Constant | Use |
|-------|----------|-----|
| Info | `errlogInfo` | Normal operational messages |
| Minor | `errlogMinor` | Recoverable issues |
| Major | `errlogMajor` | Significant problems |
| Fatal | `errlogFatal` | Unrecoverable errors |

### 8.3 Controlling Log Output

```c
/* Set minimum severity to log (suppress Info messages) */
errlogSetSevToLog(errlogMinor);

/* Enable/disable console output */
eltc(0);    /* Disable console */
eltc(1);    /* Enable console */

/* Flush log buffer (wait for all messages to be processed) */
errlogFlush();

/* Initialize with custom buffer size */
errlogInit2(8192, 256);   /* 8KB buffer, 256 byte max message */
```

### 8.4 Log Listeners

```c
void myListener(void *pPrivate, const char *message)
{
    FILE *logFile = (FILE *)pPrivate;
    fprintf(logFile, "%s", message);
}

FILE *fp = fopen("mylog.txt", "a");
errlogAddListener(myListener, fp);

/* Remove listener */
errlogRemoveListeners(myListener, fp);
```

---

## 9. Linked Lists (ellLib)

Doubly-linked list implementation. The `ELLNODE` must be the first member of any structure placed on the list.

### 9.1 Basic Usage

```c
#include "ellLib.h"

typedef struct myItem {
    ELLNODE node;       /* MUST be first member */
    int data;
    char name[40];
} myItem;

/* Initialize list */
ELLLIST myList = ELLLIST_INIT;
/* or: */
ELLLIST myList;
ellInit(&myList);

/* Add items */
myItem *item = calloc(1, sizeof(myItem));
item->data = 42;
ellAdd(&myList, &item->node);     /* Add to end */

/* Iterate */
myItem *p;
for (p = (myItem *)ellFirst(&myList);
     p != NULL;
     p = (myItem *)ellNext(&p->node))
{
    printf("data = %d\n", p->data);
}

/* Count */
int n = ellCount(&myList);

/* Remove first */
myItem *first = (myItem *)ellGet(&myList);   /* Remove and return first */

/* Remove last */
myItem *last = (myItem *)ellPop(&myList);    /* Remove and return last */

/* Remove specific */
ellDelete(&myList, &item->node);

/* Find nth (1-based) */
myItem *third = (myItem *)ellNth(&myList, 3);

/* Free all (frees nodes only, not containing structures) */
ellFree(&myList);

/* Free all with custom destructor */
ellFree2(&myList, free);
```

### 9.2 Inserting

```c
/* Insert after a specific node (NULL = prepend) */
ellInsert(&myList, &afterThisNode->node, &newItem->node);
```

### 9.3 Sorting

```c
int myCmp(const ELLNODE *a, const ELLNODE *b)
{
    myItem *ia = (myItem *)a;
    myItem *ib = (myItem *)b;
    return ia->data - ib->data;
}

ellSortStable(&myList, myCmp);
```

---

## 10. Thread Pool (epicsThreadPool)

### 10.1 Creating and Using a Thread Pool

```c
#include "epicsThreadPool.h"

/* Configure pool */
epicsThreadPoolConfig cfg;
epicsThreadPoolConfigDefaults(&cfg);
cfg.initialThreads = 2;
cfg.maxThreads = 8;

/* Create pool */
epicsThreadPool *pool = NULL;
epicsThreadPoolCreate(&pool, &cfg);

/* Define a job function */
void myJobFunc(void *arg, epicsJobMode mode)
{
    if (mode == epicsJobModeCleanup) {
        /* Pool is shutting down -- clean up */
        return;
    }
    /* ... do work ... */
}

/* Create and queue a job */
epicsJob *job = NULL;
epicsJobCreate(pool, myJobFunc, myArg, &job);
epicsJobQueue(job);     /* Queue for execution */

/* Wait for all jobs to complete */
epicsThreadPoolWait(pool, -1.0);   /* -1 = wait forever */

/* Cleanup */
epicsJobDestroy(job);
epicsThreadPoolDestroy(pool);
```

### 10.2 Shared Pool

```c
/* Get a shared pool (reuse across modules) */
epicsThreadPool *pool = NULL;
epicsThreadPoolGetShared(&pool);

/* ... use pool ... */

epicsThreadPoolReleaseShared(pool);
```

---

## 11. IOC Shell Command Registration

### 11.1 Complete Pattern

```c
#include <iocsh.h>
#include <epicsExport.h>   /* MUST be last */

/* The command function */
void myCommand(const char *name, int count, double rate)
{
    printf("name=%s count=%d rate=%f\n", name, count, rate);
}

/* Argument descriptors */
static const iocshArg arg0 = {"name", iocshArgString};
static const iocshArg arg1 = {"count", iocshArgInt};
static const iocshArg arg2 = {"rate", iocshArgDouble};
static const iocshArg *args[] = {&arg0, &arg1, &arg2};

/* Function definition */
static const iocshFuncDef myCommandDef = {"myCommand", 3, args};

/* Wrapper that extracts typed arguments */
static void myCommandCall(const iocshArgBuf *args)
{
    myCommand(args[0].sval, args[1].ival, args[2].dval);
}

/* Registrar function */
static void myRegistrar(void)
{
    iocshRegister(&myCommandDef, myCommandCall);
}
epicsExportRegistrar(myRegistrar);
```

### 11.2 Argument Types

| Type | Field | C Type |
|------|-------|--------|
| `iocshArgString` | `args[n].sval` | `char *` |
| `iocshArgInt` | `args[n].ival` | `int` |
| `iocshArgDouble` | `args[n].dval` | `double` |
| `iocshArgPdbbase` | `args[n].vval` | `void *` |

### 11.3 DBD Declaration

```
registrar(myRegistrar)
```

### 11.4 Exported Variables

```c
int myDebugLevel = 0;
epicsExportAddress(int, myDebugLevel);
```

```
variable(myDebugLevel, int)
```

Usage in st.cmd: `var myDebugLevel 1`

---

## 12. Init Hooks

Register functions to be called at specific IOC lifecycle stages.

```c
#include "initHooks.h"
#include "epicsExport.h"

static void myHook(initHookState state)
{
    switch (state) {
    case initHookAfterInitDatabase:
        /* Database is initialized -- set up connections */
        break;
    case initHookAfterIocRunning:
        /* IOC is fully running */
        break;
    case initHookAtShutdown:
        /* IOC is shutting down -- clean up */
        break;
    default:
        break;
    }
}

static void myHookRegistrar(void)
{
    initHookRegister(myHook);
}
epicsExportRegistrar(myHookRegistrar);
```

### 12.1 Lifecycle States (in order)

**Build phase:**
`initHookAtIocBuild` -> `initHookAtBeginning` -> `initHookAfterCallbackInit` -> `initHookAfterCaLinkInit` -> `initHookAfterInitDrvSup` -> `initHookAfterInitRecSup` -> `initHookAfterInitDevSup` -> `initHookAfterInitDatabase` -> `initHookAfterFinishDevSup` -> `initHookAfterScanInit` -> `initHookAfterInitialProcess` -> `initHookAfterCaServerInit` -> `initHookAfterIocBuilt`

**Run phase:**
`initHookAtIocRun` -> `initHookAfterDatabaseRunning` -> `initHookAfterCaServerRunning` -> `initHookAfterIocRunning`

**Pause phase:**
`initHookAtIocPause` -> `initHookAfterCaServerPaused` -> `initHookAfterDatabasePaused` -> `initHookAfterIocPaused`

**Shutdown phase (7.0.3.1+):**
`initHookAtShutdown` -> `initHookAfterCloseLinks` -> `initHookAfterStopScan` -> `initHookAfterStopCallback` -> `initHookAfterStopLinks` -> `initHookBeforeFree` -> `initHookAfterShutdown`

---

## 13. Exit Handlers

```c
#include "epicsExit.h"

void myCleanup(void *arg)
{
    /* Clean up resources */
}

/* Register exit handler (called in reverse order of registration) */
epicsAtExit(myCleanup, myArg);

/* Register per-thread exit handler */
epicsAtThreadExit(myThreadCleanup, myArg);

/* Proper IOC exit (calls all handlers, then OS exit) */
epicsExit(0);
```

---

## 14. Subroutine/aSub Function Registration

```c
#include <registryFunction.h>
#include <subRecord.h>
#include <aSubRecord.h>
#include <epicsExport.h>

static long mySubProcess(subRecord *prec) {
    prec->val = prec->a + prec->b;
    return 0;
}

static long myASubProcess(aSubRecord *prec) {
    double *input = (double *)prec->a;
    double *output = (double *)prec->vala;
    /* ... process arrays ... */
    prec->neva = prec->nea;
    return 0;
}

epicsRegisterFunction(mySubProcess);
epicsRegisterFunction(myASubProcess);
```

DBD:
```
function(mySubProcess)
function(myASubProcess)
```

---

## 15. Socket Abstraction (osiSock)

```c
#include "osiSock.h"

/* Initialize sockets (required on Windows) */
osiSockAttach();

/* Create a TCP socket */
SOCKET sock = epicsSocketCreate(AF_INET, SOCK_STREAM, 0);
if (sock == INVALID_SOCKET) { /* error */ }

/* Enable address reuse */
epicsSocketEnableAddressReuseDuringTimeWaitState(sock);

/* Convert address */
char addrBuf[64];
struct sockaddr_in addr;
aToIPAddr("192.168.1.100:5025", 0, &addr.sin_addr);
addr.sin_family = AF_INET;
addr.sin_port = htons(5025);
sockAddrToDottedIP((struct sockaddr *)&addr, addrBuf, sizeof(addrBuf));

/* Cleanup */
epicsSocketDestroy(sock);
osiSockRelease();
```

---

## 16. Export Macros (epicsExport.h)

**CRITICAL: `epicsExport.h` must be the LAST EPICS include in any file that uses these macros.**

```c
#include "epicsExport.h"   /* LAST include */

/* Export device support entry table */
epicsExportAddress(dset, devMyDriver);

/* Export registrar function */
epicsExportRegistrar(myRegistrar);

/* Export subroutine function */
epicsRegisterFunction(mySubroutine);

/* Export a variable */
epicsExportAddress(int, myDebugFlag);
```

---

## 17. Key Rules and Pitfalls

1. **`epicsExport.h` must be the last EPICS include.** It redefines symbol visibility macros. Including other EPICS headers after it causes symbol visibility problems on shared library builds.

2. **Use `epicsMutex` (not OS mutexes)** for any lock shared between EPICS threads. `epicsMutex` provides priority inheritance on supported platforms.

3. **Always use RAII guards** (`epicsMutex::guard_t`) in C++ code. Manual lock/unlock is error-prone in the presence of exceptions.

4. **`ELLNODE` must be the first member** of any structure placed on an `ELLLIST`. The list macros cast between `ELLNODE*` and the containing structure pointer.

5. **`epicsThreadOnce` is the correct way to do lazy initialization.** Do not use double-checked locking or other patterns. The `onceFlag` must be `static` and initialized to `EPICS_THREAD_ONCE_INIT`.

6. **`epicsCallback` (CALLBACK) structures must be zero-initialized** before first use. Always allocate with `calloc()` or zero-initialize in C++.

7. **Ring buffers without the "Locked" suffix** are only safe for single-producer/single-consumer. Use `epicsRingPointerLockedCreate()` for multi-producer or multi-consumer scenarios.

8. **`errlogPrintf` is thread-safe** and buffers messages. Use it instead of `printf` in EPICS code. Messages are processed asynchronously by the errlog task.

9. **`epicsThreadMustJoin()` must be called** for joinable threads before the thread ID goes out of scope. Failing to join leaks resources.

10. **Timer callback functions run in the timer queue thread.** Keep them short. For long-running work, signal an event or queue a job.
