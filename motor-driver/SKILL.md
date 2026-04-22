---
name: motor-driver
description: Write EPICS model-3 asyn motor drivers -- asynMotorController and asynMotorAxis subclasses with move, home, stop, poll, convenience I/O, status bits, and iocsh registration
---

# Motor Driver Skill

You are an expert at writing EPICS model-3 motor drivers. A model-3 motor driver consists of two C++ classes:

1. **Controller class** -- inherits from `asynMotorController` (which inherits from `asynPortDriver`). One instance per physical controller. Manages axes, poller thread, and hardware communication.
2. **Axis class** -- inherits from `asynMotorAxis`. One instance per motor axis. Implements motion commands and status polling.

Motor driver modules are designed to build either as a submodule of motor or as a standalone module.

---

## 1. Creating a New Motor Driver Module

### 1.1 Using createMotorDriverModule (Recommended)

The `createMotorDriverModule.py` script creates a new module from the `motorExample` template:

```bash
# Install the script
git clone https://github.com/epics-motor/createMotorDriverModule.git

# Simple: module name = driver name = class name
python createMotorDriverModule/createMotorDriverModule.py Vendor
# Creates: motorVendor/

# Two-name: separate module and driver names
python createMotorDriverModule/createMotorDriverModule.py AcsMotion --driver SPiiPlus
# Creates: motorAcsMotion/ with SPiiPlusDriver.cpp, SPiiPlusDriver.h

# Three-name: separate module, driver filename, and C++ class names
python createMotorDriverModule/createMotorDriverModule.py VMC --driver vmc --class VirtualMotor
# Creates: motorVMC/ with vmcDriver.cpp, vmcDriver.h,
#          C++ classes: VirtualMotorController, VirtualMotorAxis
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `ModuleName` | Yes | Module name. Output directory is `motor<ModuleName>`. |
| `--driver Name` | No | Controls source filenames (`.cpp`, `.h`, `.dbd`). Defaults to ModuleName. |
| `--class Name` | No | Controls C++ class names and iocsh function names. Defaults to `--driver` value. |
| `--url URL` | No | Git URL for motorExample template. Defaults to GitHub. |

### 1.2 Name Derivation

The script uses CamelCase-aware lowering for module names (only first character lowered):

| Input | lowercase | title-case | UPPERCASE |
|-------|-----------|------------|-----------|
| `Vendor` | `vendor` | `Vendor` | `VENDOR` |
| `AcsMotion` | `acsMotion` | `AcsMotion` | `ACSMOTION` |
| `VMC` | `vmc` | `VMC` | `VMC` |

### 1.3 Resulting Module Structure

```
motorVendor/
  configure/
    RELEASE                     # Dual-mode: works inside motor or standalone
    CONFIG_SITE                 # BUILD_IOCS = NO by default
    EXAMPLE_RELEASE.local       # Copy to RELEASE.local, set MOTOR path
    EXAMPLE_CONFIG_SITE.local   # Copy to CONFIG_SITE.local, set BUILD_IOCS = YES
  vendorApp/
    src/
      VendorDriver.h            # Controller and axis class declarations
      VendorDriver.cpp          # Driver implementation (edit this)
      Vendor.dbd                # registrar(VendorMotorRegister)
      Makefile                  # Builds library "Vendor", links motor + asyn
    Db/
      Makefile                  # Add driver-specific .db/.template files here
    iocsh/
      motorVendor.iocsh         # Reusable iocsh snippet for loading the driver
      EXAMPLE_motorVendor.substitutions  # Example motor substitutions
      Makefile
  iocs/
    vendorIOC/                  # Example IOC for testing
      configure/
        RELEASE                 # Dual-mode RELEASE for the IOC
        EXAMPLE_RELEASE.local   # Copy and configure for standalone build
      vendorApp/src/
        Makefile                # Links Vendor + motor + asyn libraries
      iocBoot/iocVendor/
        st.cmd                  # Example startup script
        vendor.iocsh            # Loads motorVendor.iocsh with defaults
        settings.iocsh          # PREFIX definition
```

### 1.4 Dual-Build Mode (Standalone vs Motor Submodule)

Motor driver modules support two build modes through a special `configure/RELEASE` pattern:

```makefile
# configure/RELEASE
# Use motor/module's generated release file when building inside motor
-include $(TOP)/../RELEASE.$(EPICS_HOST_ARCH).local
# Use motorVendor's RELEASE.local when building outside motor
-include $(TOP)/configure/RELEASE.local
```

**As a motor submodule:** Place the module directory under `motor/modules/`. The motor build system provides RELEASE paths automatically via `RELEASE.$(EPICS_HOST_ARCH).local`.

**As a standalone module:** Copy `EXAMPLE_RELEASE.local` to `RELEASE.local` and set the paths:

```makefile
# configure/RELEASE.local
MOTOR=/path/to/motor
-include $(MOTOR)/modules/RELEASE.$(EPICS_HOST_ARCH).local
MOTOR_VENDOR=/path/to/motorVendor
```

To build the example IOC, also copy `EXAMPLE_CONFIG_SITE.local` to `CONFIG_SITE.local`:

```makefile
# configure/CONFIG_SITE.local
-include $(MOTOR)/configure/CONFIG_SITE
CHECK_RELEASE = WARN
BUILD_IOCS = YES
```

### 1.5 The iocsh Snippet

Each motor driver module includes a reusable `.iocsh` file that configures the driver with macro parameters:

```bash
# motorVendor.iocsh -- loaded from an IOC's st.cmd
# Macros: INSTANCE, IP_ADDR, TCP_PORT, NUM_AXES, MOVING_POLL, IDLE_POLL, SUB, etc.

drvAsynIPPortConfigure("$(INSTANCE)_ETH","$(IP_ADDR=127.0.0.1):$(TCP_PORT=12345)", 0, 0, 0)
asynSetTraceMask("$(INSTANCE)_ETH", 0, $(TRACE_MASK=ERROR))
asynSetTraceIOMask("$(INSTANCE)_ETH", 0, $(TRACEIO_MASK=ASCII))
asynOctetSetInputEos("$(INSTANCE)_ETH",0,"\r\n")
asynOctetSetOutputEos("$(INSTANCE)_ETH",0,"\r")

VendorMotorCreateController("$(INSTANCE)", "$(INSTANCE)_ETH", $(NUM_AXES=8), $(MOVING_POLL=100), $(IDLE_POLL=1000))

dbLoadTemplate("$(SUB=$(MOTOR_VENDOR)/iocsh/EXAMPLE_motorVendor.substitutions)", "P=$(PREFIX),PORT=$(INSTANCE)")
dbLoadRecords("$(ASYN)/db/asynRecord.db","P=$(PREFIX),R=$(ASYN_RECORD=asyn_1),PORT=$(INSTANCE)_ETH,ADDR=0,OMAX=0,IMAX=0")
```

### 1.6 After Module Creation

1. Edit the driver source files (`VendorDriver.h`, `VendorDriver.cpp`) to implement your hardware protocol
2. Update the `.iocsh` file with the correct communication parameters (TCP port, EOS strings, etc.)
3. Update the example `.substitutions` file with appropriate motor parameters
4. Add any driver-specific database templates to `vendorApp/Db/`
5. Configure `RELEASE.local` and `CONFIG_SITE.local` from the EXAMPLE files
6. Build with `make`

---

## 2. Headers and Linking (src/Makefile)

```cpp
#include "asynMotorController.h"
#include "asynMotorAxis.h"
```

```makefile
# In src/Makefile:
LIBRARY_IOC += myMotor

myMotor_SRCS += myMotorDriver.cpp
myMotor_LIBS += motor
myMotor_LIBS += asyn
myMotor_LIBS += $(EPICS_BASE_IOC_LIBS)

DBD += myMotorSupport.dbd
```

DBD file:
```
registrar(myMotorRegister)
```

No `device()` declaration is needed -- the base class provides `device(motor, INST_IO, devMotorAsyn, "asynMotor")` via `motorSupport.dbd`.

---

## 3. Axis Class

### 3.1 Class Declaration

```cpp
class myMotorAxis : public asynMotorAxis {
public:
    myMotorAxis(class myMotorController *pC, int axisNo);

    /* Pure virtual methods that MUST be implemented */
    asynStatus move(double position, int relative,
                    double minVelocity, double maxVelocity, double acceleration);
    asynStatus moveVelocity(double minVelocity, double maxVelocity,
                            double acceleration);
    asynStatus home(double minVelocity, double maxVelocity,
                    double acceleration, int forwards);
    asynStatus stop(double acceleration);
    asynStatus poll(bool *moving);

    /* Optional overrides */
    asynStatus setPosition(double position);
    asynStatus setClosedLoop(bool closedLoop);
    asynStatus setHighLimit(double highLimit);
    asynStatus setLowLimit(double lowLimit);
    asynStatus setPGain(double pGain);
    asynStatus setIGain(double iGain);
    asynStatus setDGain(double dGain);
    asynStatus setEncoderRatio(double ratio);

private:
    myMotorController *pC_;   /* Shortcut to controller (avoids casting pC_) */

    /* Driver-specific state */
    double encoderPosition_;
    double commandedPosition_;
    bool   homed_;

    friend class myMotorController;
};
```

### 3.2 Axis Constructor

```cpp
myMotorAxis::myMotorAxis(myMotorController *pC, int axisNo)
    : asynMotorAxis(pC, axisNo)
    , pC_(pC)
    , encoderPosition_(0.0)
    , commandedPosition_(0.0)
    , homed_(false)
{
    /* Perform per-axis initialization here.
     * The axis number is available as axisNo_ (protected member).
     * The asynUser for trace output is pasynUser_ (protected member).
     */
}
```

### 3.3 move() -- Absolute and Relative Moves

```cpp
asynStatus myMotorAxis::move(double position, int relative,
                              double minVelocity, double maxVelocity,
                              double acceleration)
{
    asynStatus status;

    /* position is in motor record steps (after MRES conversion).
     * relative: 0 = absolute, 1 = relative.
     * Velocities and acceleration are in steps/sec and steps/sec^2.
     */

    if (relative) {
        sprintf(pC_->outString_, "AXIS%d:MOVEREL %f VEL=%f ACC=%f",
                axisNo_ + 1, position, maxVelocity, acceleration);
    } else {
        sprintf(pC_->outString_, "AXIS%d:MOVEABS %f VEL=%f ACC=%f",
                axisNo_ + 1, position, maxVelocity, acceleration);
    }
    status = pC_->writeController();

    return status;
}
```

### 3.4 home() -- Home Search

```cpp
asynStatus myMotorAxis::home(double minVelocity, double maxVelocity,
                              double acceleration, int forwards)
{
    /* forwards: 1 = positive direction, 0 = negative direction */
    sprintf(pC_->outString_, "AXIS%d:HOME %s VEL=%f",
            axisNo_ + 1, forwards ? "+" : "-", maxVelocity);
    return pC_->writeController();
}
```

### 3.5 stop() -- Stop Motion

```cpp
asynStatus myMotorAxis::stop(double acceleration)
{
    sprintf(pC_->outString_, "AXIS%d:STOP", axisNo_ + 1);
    return pC_->writeController();
}
```

### 3.6 moveVelocity() -- Jog

```cpp
asynStatus myMotorAxis::moveVelocity(double minVelocity, double maxVelocity,
                                      double acceleration)
{
    /* maxVelocity sign indicates direction: positive = forward, negative = reverse */
    sprintf(pC_->outString_, "AXIS%d:JOG %f ACC=%f",
            axisNo_ + 1, maxVelocity, acceleration);
    return pC_->writeController();
}
```

### 3.7 poll() -- Status Polling (CRITICAL)

This is the most important method. It is called periodically by the poller thread. It must query hardware status and update all motor status parameters.

```cpp
asynStatus myMotorAxis::poll(bool *moving)
{
    asynStatus status;
    int done;
    double position;
    double encoderPosition;
    int highLimit, lowLimit, homeSwitch;
    int error;

    /* Query position from hardware */
    sprintf(pC_->outString_, "AXIS%d:POS?", axisNo_ + 1);
    status = pC_->writeReadController();
    if (status) {
        /* Communication error -- set COMMS error bit and return */
        setIntegerParam(pC_->motorStatusCommsError_, 1);
        callParamCallbacks();
        *moving = false;
        return status;
    }
    position = atof(pC_->inString_);

    /* Query encoder position */
    sprintf(pC_->outString_, "AXIS%d:ENC?", axisNo_ + 1);
    status = pC_->writeReadController();
    if (status == asynSuccess) {
        encoderPosition = atof(pC_->inString_);
    } else {
        encoderPosition = position;
    }

    /* Query motion status */
    sprintf(pC_->outString_, "AXIS%d:MOVING?", axisNo_ + 1);
    status = pC_->writeReadController();
    done = (status == asynSuccess) ? !atoi(pC_->inString_) : 1;

    /* Query limit switches */
    sprintf(pC_->outString_, "AXIS%d:LIMITS?", axisNo_ + 1);
    status = pC_->writeReadController();
    if (status == asynSuccess) {
        sscanf(pC_->inString_, "%d %d %d", &highLimit, &lowLimit, &homeSwitch);
    } else {
        highLimit = lowLimit = homeSwitch = 0;
    }

    /* Set motor status parameters */
    setDoubleParam(pC_->motorPosition_, position);
    setDoubleParam(pC_->motorEncoderPosition_, encoderPosition);
    setIntegerParam(pC_->motorStatusDone_, done);
    setIntegerParam(pC_->motorStatusMoving_, !done);
    setIntegerParam(pC_->motorStatusHighLimit_, highLimit);
    setIntegerParam(pC_->motorStatusLowLimit_, lowLimit);
    setIntegerParam(pC_->motorStatusHome_, homeSwitch);
    setIntegerParam(pC_->motorStatusHomed_, homed_ ? 1 : 0);
    setIntegerParam(pC_->motorStatusDirection_, (position > commandedPosition_) ? 1 : 0);
    setIntegerParam(pC_->motorStatusHasEncoder_, 1);
    setIntegerParam(pC_->motorStatusCommsError_, 0);
    setIntegerParam(pC_->motorStatusProblem_, 0);

    /* Tell the caller whether we are moving */
    *moving = !done;

    /* Publish updates to records */
    callParamCallbacks();

    return asynSuccess;
}
```

### 3.8 setPosition() -- Define Current Position

```cpp
asynStatus myMotorAxis::setPosition(double position)
{
    sprintf(pC_->outString_, "AXIS%d:SETPOS %f", axisNo_ + 1, position);
    return pC_->writeController();
}
```

### 3.9 setClosedLoop() -- Enable/Disable Servo

```cpp
asynStatus myMotorAxis::setClosedLoop(bool closedLoop)
{
    sprintf(pC_->outString_, "AXIS%d:SERVO %s",
            axisNo_ + 1, closedLoop ? "ON" : "OFF");
    return pC_->writeController();
}
```

---

## 4. Controller Class

### 4.1 Class Declaration

```cpp
class myMotorController : public asynMotorController {
public:
    myMotorController(const char *portName, const char *commPortName,
                      int numAxes, double movingPollPeriod,
                      double idlePollPeriod);

    /* Override writeInt32 for driver-specific commands */
    asynStatus writeInt32(asynUser *pasynUser, epicsInt32 value);

    /* Axis accessor (covariant return type) */
    myMotorAxis* getAxis(asynUser *pasynUser);
    myMotorAxis* getAxis(int axisNo);

    void report(FILE *fp, int level);

    /* Driver-specific methods */
    asynStatus sendCommand(const char *cmd);

protected:
    /* Indices for driver-specific parameters (beyond the motor base set) */
    int myParam1_;
    #define FIRST_MY_PARAM myParam1_
    int myParam2_;
    #define LAST_MY_PARAM myParam2_
    #define NUM_MY_PARAMS (&LAST_MY_PARAM - &FIRST_MY_PARAM + 1)

    friend class myMotorAxis;
};
```

### 4.2 Controller Constructor

```cpp
myMotorController::myMotorController(const char *portName,
                                      const char *commPortName,
                                      int numAxes,
                                      double movingPollPeriod,
                                      double idlePollPeriod)
    : asynMotorController(
        portName,           /* Motor port name */
        numAxes,            /* Number of axes */
        NUM_MY_PARAMS,      /* Number of additional parameters beyond base */
        0,                  /* Additional interface mask bits (0 if none) */
        0,                  /* Additional interrupt mask bits (0 if none) */
        ASYN_CANBLOCK | ASYN_MULTIDEVICE,  /* asyn flags */
        1,                  /* autoConnect = yes */
        0, 0)               /* Default priority and stack size */
{
    /* Create driver-specific parameters */
    createParam("MY_PARAM1", asynParamInt32,   &myParam1_);
    createParam("MY_PARAM2", asynParamFloat64, &myParam2_);

    /* Connect to the underlying communication port (serial, IP, etc.) */
    pasynOctetSyncIO->connect(commPortName, 0, &pasynUserController_, NULL);

    /* Create axis objects */
    for (int axis = 0; axis < numAxes; axis++) {
        new myMotorAxis(this, axis);
    }

    /* Start the poller thread */
    startPoller(movingPollPeriod, idlePollPeriod, 2);
}
```

**Key points about the constructor:**
- `numParams` (3rd argument) is the count of ADDITIONAL parameters beyond the ~60 defined by the base class.
- The 4th and 5th arguments are additional interface/interrupt mask bits to OR into the base class masks.
- `pasynOctetSyncIO->connect()` establishes the connection to the underlying communication port.
- Axis objects are created with `new` and stored in the base class `pAxes_` array.
- `startPoller()` launches the polling thread that calls `poll()` on each axis.

### 4.3 Convenience I/O Methods

The base class provides these methods using `outString_` and `inString_` buffers and `pasynUserController_`:

```cpp
/* Write outString_ to the controller */
asynStatus writeController();
asynStatus writeController(const char *output, double timeout);

/* Read from the controller into inString_ */
asynStatus readController();
asynStatus readController(char *response, size_t maxLen, size_t *responseLen, double timeout);

/* Write outString_ then read response into inString_ */
asynStatus writeReadController();
asynStatus writeReadController(const char *output, char *response,
                                size_t maxLen, size_t *responseLen, double timeout);
```

Typical usage pattern:

```cpp
/* Build command in outString_, send, read response into inString_ */
sprintf(pC_->outString_, "AXIS%d:STATUS?", axisNo_ + 1);
status = pC_->writeReadController();
if (status == asynSuccess) {
    int statusWord = atoi(pC_->inString_);
    /* ... parse status ... */
}
```

The default timeout is `DEFAULT_CONTROLLER_TIMEOUT` (2.0 seconds). The buffer size is `MAX_CONTROLLER_STRING_SIZE` (256 bytes).

### 4.4 getAxis() -- Covariant Return

```cpp
myMotorAxis* myMotorController::getAxis(asynUser *pasynUser)
{
    return static_cast<myMotorAxis*>(asynMotorController::getAxis(pasynUser));
}

myMotorAxis* myMotorController::getAxis(int axisNo)
{
    return static_cast<myMotorAxis*>(asynMotorController::getAxis(axisNo));
}
```

### 4.5 writeInt32() -- Handle Driver-Specific Commands

```cpp
asynStatus myMotorController::writeInt32(asynUser *pasynUser, epicsInt32 value)
{
    int function = pasynUser->reason;
    myMotorAxis *pAxis = getAxis(pasynUser);
    asynStatus status = asynSuccess;

    if (function == myParam1_) {
        /* Handle driver-specific parameter */
        sprintf(outString_, "CONFIG %d", value);
        status = writeController();
    } else {
        /* Call base class for all motor commands (move, home, stop, etc.) */
        status = asynMotorController::writeInt32(pasynUser, value);
    }

    pAxis->callParamCallbacks();
    return status;
}
```

### 4.6 report()

```cpp
void myMotorController::report(FILE *fp, int level)
{
    fprintf(fp, "myMotor controller %s, numAxes=%d, commPort=%s\n",
            portName, numAxes_, commPortName_);
    if (level > 0) {
        /* Print additional details */
    }
    asynMotorController::report(fp, level);
}
```

---

## 5. Motor Status Parameters

The base class pre-defines these parameter indices. Use them in `poll()` and motion commands:

### 5.1 Position and Velocity

| Parameter Index | drvInfo String | Type | Description |
|----------------|----------------|------|-------------|
| `motorPosition_` | `MOTOR_POSITION` | Float64 | Commanded position (steps) |
| `motorEncoderPosition_` | `MOTOR_ENCODER_POSITION` | Float64 | Encoder position (steps) |
| `motorActVelocity_` | `MOTOR_ACT_VELOCITY` | Float64 | Actual velocity |

### 5.2 Status Bits (Integer, 0 or 1)

| Parameter Index | drvInfo String | Description |
|----------------|----------------|-------------|
| `motorStatusDirection_` | `MOTOR_STATUS_DIRECTION` | Last direction: 1=positive, 0=negative |
| `motorStatusDone_` | `MOTOR_STATUS_DONE` | Motion complete: 1=done, 0=moving |
| `motorStatusHighLimit_` | `MOTOR_STATUS_HIGH_LIMIT` | High limit switch active |
| `motorStatusLowLimit_` | `MOTOR_STATUS_LOW_LIMIT` | Low limit switch active |
| `motorStatusHome_` | `MOTOR_STATUS_HOME` | Home switch active |
| `motorStatusHomed_` | `MOTOR_STATUS_HOMED` | Axis has been homed |
| `motorStatusMoving_` | `MOTOR_STATUS_MOVING` | Axis is moving |
| `motorStatusPowerOn_` | `MOTOR_STATUS_POWERED` | Amplifier power is on |
| `motorStatusHasEncoder_` | `MOTOR_STATUS_HAS_ENCODER` | Axis has an encoder |
| `motorStatusGainSupport_` | `MOTOR_STATUS_GAIN_SUPPORT` | Supports closed-loop PID |
| `motorStatusProblem_` | `MOTOR_STATUS_PROBLEM` | General problem flag |
| `motorStatusCommsError_` | `MOTOR_STATUS_COMMS_ERROR` | Communication error |
| `motorStatusFollowingError_` | `MOTOR_STATUS_FOLLOWING_ERROR` | Following error exceeded |
| `motorStatusSlip_` | `MOTOR_STATUS_SLIP` | Encoder slip detected |
| `motorStatusAtHome_` | `MOTOR_STATUS_AT_HOME` | At home position |

### 5.3 Motor Record Feedback Parameters

These are set by the database auxiliary records and can be read by the driver:

| Parameter Index | drvInfo String | Description |
|----------------|----------------|-------------|
| `motorRecResolution_` | `MOTOR_REC_RESOLUTION` | Motor record MRES value |
| `motorRecDirection_` | `MOTOR_REC_DIRECTION` | Motor record DIR value |
| `motorRecOffset_` | `MOTOR_REC_OFFSET` | Motor record OFF value |

### 5.4 Power Management Parameters

| Parameter Index | drvInfo String | Description |
|----------------|----------------|-------------|
| `motorPowerAutoOnOff_` | `MOTOR_POWER_AUTO_ONOFF` | Auto power on/off enable |
| `motorPowerOnDelay_` | `MOTOR_POWER_ON_DELAY` | Delay after power-on (sec) |
| `motorPowerOffDelay_` | `MOTOR_POWER_OFF_DELAY` | Delay before power-off (sec) |
| `motorPowerOffFraction_` | `MOTOR_POWER_OFF_FRACTION` | Holding current fraction |
| `motorPostMoveDelay_` | `MOTOR_POST_MOVE_DELAY` | Delay after move completes (sec) |

---

## 6. The Poller Thread

The base class provides a poller thread that calls `poll()` on each axis. Configure it in the constructor:

```cpp
startPoller(
    0.1,    /* movingPollPeriod: seconds between polls when any axis is moving */
    1.0,    /* idlePollPeriod: seconds between polls when all axes are idle */
    2       /* forcedFastPolls: number of fast polls after a wakeup event */
);
```

The poller automatically switches between fast and slow polling based on axis movement status. Call `wakeupPoller()` to force an immediate poll cycle (e.g., after sending a move command).

---

## 7. IOC Shell Registration

```cpp
/* At the bottom of myMotorDriver.cpp */

extern "C" {

/* The create function -- called from st.cmd */
int myMotorCreateController(const char *portName, const char *commPortName,
                             int numAxes, double movingPollPeriod,
                             double idlePollPeriod)
{
    new myMotorController(portName, commPortName, numAxes,
                           movingPollPeriod, idlePollPeriod);
    return asynSuccess;
}

/* iocsh registration */
static const iocshArg arg0 = {"Port name",          iocshArgString};
static const iocshArg arg1 = {"Comm port name",     iocshArgString};
static const iocshArg arg2 = {"Num axes",           iocshArgInt};
static const iocshArg arg3 = {"Moving poll period", iocshArgDouble};
static const iocshArg arg4 = {"Idle poll period",   iocshArgDouble};
static const iocshArg *args[] = {&arg0, &arg1, &arg2, &arg3, &arg4};
static const iocshFuncDef configDef = {"myMotorCreateController", 5, args};

static void configCallFunc(const iocshArgBuf *args)
{
    myMotorCreateController(args[0].sval, args[1].sval, args[2].ival,
                             args[3].dval, args[4].dval);
}

static void myMotorRegister(void)
{
    iocshRegister(&configDef, configCallFunc);
}

epicsExportRegistrar(myMotorRegister);

} /* extern "C" */
```

---

## 8. Complete Minimal Driver

```cpp
/* myMotorDriver.cpp */
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include <iocsh.h>
#include <epicsThread.h>
#include <asynOctetSyncIO.h>

#include "asynMotorController.h"
#include "asynMotorAxis.h"

#include <epicsExport.h>

static const char *driverName = "myMotor";

/* Forward declaration */
class myMotorController;

/*** Axis class ***/
class myMotorAxis : public asynMotorAxis {
public:
    myMotorAxis(myMotorController *pC, int axisNo);
    asynStatus move(double position, int relative,
                    double minVelocity, double maxVelocity, double acceleration);
    asynStatus moveVelocity(double minVelocity, double maxVelocity,
                            double acceleration);
    asynStatus home(double minVelocity, double maxVelocity,
                    double acceleration, int forwards);
    asynStatus stop(double acceleration);
    asynStatus poll(bool *moving);
    asynStatus setPosition(double position);
    asynStatus setClosedLoop(bool closedLoop);
private:
    myMotorController *pC_;
    friend class myMotorController;
};

/*** Controller class ***/
class myMotorController : public asynMotorController {
public:
    myMotorController(const char *portName, const char *commPort,
                      int numAxes, double movingPoll, double idlePoll);
    myMotorAxis* getAxis(asynUser *pasynUser);
    myMotorAxis* getAxis(int axisNo);
    void report(FILE *fp, int level);
    friend class myMotorAxis;
};

/* Controller constructor */
myMotorController::myMotorController(const char *portName,
    const char *commPort, int numAxes, double movingPoll, double idlePoll)
    : asynMotorController(portName, numAxes, 0, 0, 0,
                           ASYN_CANBLOCK | ASYN_MULTIDEVICE, 1, 0, 0)
{
    pasynOctetSyncIO->connect(commPort, 0, &pasynUserController_, NULL);
    for (int axis = 0; axis < numAxes; axis++) {
        new myMotorAxis(this, axis);
    }
    startPoller(movingPoll, idlePoll, 2);
}

myMotorAxis* myMotorController::getAxis(asynUser *pasynUser) {
    return static_cast<myMotorAxis*>(asynMotorController::getAxis(pasynUser));
}
myMotorAxis* myMotorController::getAxis(int axisNo) {
    return static_cast<myMotorAxis*>(asynMotorController::getAxis(axisNo));
}

void myMotorController::report(FILE *fp, int level) {
    fprintf(fp, "myMotor controller %s, numAxes=%d\n", portName, numAxes_);
    asynMotorController::report(fp, level);
}

/* Axis constructor */
myMotorAxis::myMotorAxis(myMotorController *pC, int axisNo)
    : asynMotorAxis(pC, axisNo), pC_(pC) {}

asynStatus myMotorAxis::move(double position, int relative,
    double minVelocity, double maxVelocity, double acceleration)
{
    sprintf(pC_->outString_, "%d %s %f %f %f", axisNo_ + 1,
            relative ? "MOVEREL" : "MOVEABS", position, maxVelocity, acceleration);
    return pC_->writeController();
}

asynStatus myMotorAxis::moveVelocity(double minVelocity,
    double maxVelocity, double acceleration)
{
    sprintf(pC_->outString_, "%d JOG %f %f", axisNo_ + 1, maxVelocity, acceleration);
    return pC_->writeController();
}

asynStatus myMotorAxis::home(double minVelocity, double maxVelocity,
    double acceleration, int forwards)
{
    sprintf(pC_->outString_, "%d HOME %s %f", axisNo_ + 1,
            forwards ? "+" : "-", maxVelocity);
    return pC_->writeController();
}

asynStatus myMotorAxis::stop(double acceleration)
{
    sprintf(pC_->outString_, "%d STOP", axisNo_ + 1);
    return pC_->writeController();
}

asynStatus myMotorAxis::setPosition(double position)
{
    sprintf(pC_->outString_, "%d SETPOS %f", axisNo_ + 1, position);
    return pC_->writeController();
}

asynStatus myMotorAxis::setClosedLoop(bool closedLoop)
{
    sprintf(pC_->outString_, "%d SERVO %s", axisNo_ + 1, closedLoop ? "ON" : "OFF");
    return pC_->writeController();
}

asynStatus myMotorAxis::poll(bool *moving)
{
    asynStatus status;

    /* Query position */
    sprintf(pC_->outString_, "%d POS?", axisNo_ + 1);
    status = pC_->writeReadController();
    if (status) {
        setIntegerParam(pC_->motorStatusCommsError_, 1);
        callParamCallbacks();
        *moving = false;
        return status;
    }
    double position = atof(pC_->inString_);

    /* Query status */
    sprintf(pC_->outString_, "%d STATUS?", axisNo_ + 1);
    status = pC_->writeReadController();
    int done = 1, highLim = 0, lowLim = 0, homeSw = 0, powered = 0;
    if (status == asynSuccess) {
        sscanf(pC_->inString_, "%d %d %d %d %d",
               &done, &highLim, &lowLim, &homeSw, &powered);
    }

    setDoubleParam(pC_->motorPosition_, position);
    setDoubleParam(pC_->motorEncoderPosition_, position);
    setIntegerParam(pC_->motorStatusDone_, done);
    setIntegerParam(pC_->motorStatusMoving_, !done);
    setIntegerParam(pC_->motorStatusHighLimit_, highLim);
    setIntegerParam(pC_->motorStatusLowLimit_, lowLim);
    setIntegerParam(pC_->motorStatusHome_, homeSw);
    setIntegerParam(pC_->motorStatusPowerOn_, powered);
    setIntegerParam(pC_->motorStatusCommsError_, 0);

    *moving = !done;
    callParamCallbacks();
    return asynSuccess;
}

/* iocsh registration */
extern "C" {
int myMotorCreateController(const char *portName, const char *commPort,
                             int numAxes, double movingPoll, double idlePoll)
{
    new myMotorController(portName, commPort, numAxes, movingPoll, idlePoll);
    return asynSuccess;
}

static const iocshArg a0 = {"Port name", iocshArgString};
static const iocshArg a1 = {"Comm port", iocshArgString};
static const iocshArg a2 = {"Num axes", iocshArgInt};
static const iocshArg a3 = {"Moving poll period", iocshArgDouble};
static const iocshArg a4 = {"Idle poll period", iocshArgDouble};
static const iocshArg *as[] = {&a0, &a1, &a2, &a3, &a4};
static const iocshFuncDef cf = {"myMotorCreateController", 5, as};
static void cc(const iocshArgBuf *a) {
    myMotorCreateController(a[0].sval, a[1].sval, a[2].ival, a[3].dval, a[4].dval);
}
static void myMotorRegister(void) { iocshRegister(&cf, cc); }
epicsExportRegistrar(myMotorRegister);
}
```

---

## 9. Key Rules and Pitfalls

1. **`poll()` must always call `callParamCallbacks()`** at the end, even on communication failure. Without it, the motor record never gets status updates.

2. **Set `*moving` correctly in `poll()`.** The poller thread uses this to decide between fast and slow polling. Getting it wrong causes either excessive CPU usage or sluggish response.

3. **`motorStatusDone_` and `motorStatusMoving_` must be consistent.** Set `Done=1, Moving=0` when idle, `Done=0, Moving=1` when moving. The motor record uses `Done` to know when a move is complete.

4. **On communication error in `poll()`**, set `motorStatusCommsError_` to 1, call `callParamCallbacks()`, set `*moving = false`, and return the error status. Do NOT leave the axis in a "moving" state.

5. **The axis constructor must call `asynMotorAxis(pC, axisNo)`** which stores the axis pointer in `pC->pAxes_[axisNo]`. Do NOT store axes yourself.

6. **`outString_` and `inString_` are shared** across all axes on the controller. The poller thread holds the controller lock during each `poll()` call, so they are safe to use from within `poll()` and motion commands. Do NOT use them from threads without locking.

7. **Axes are created with `new` in the controller constructor** and never explicitly deleted. The base class manages the `pAxes_` array.

8. **The `numParams` argument** (3rd arg) to `asynMotorController` is the count of ADDITIONAL parameters, not the total. The base class automatically registers ~60 motor parameters.

9. **Positions, velocities, and accelerations** passed to `move()`, `home()`, etc. are in motor record steps (raw units after MRES conversion). The motor record handles the user-to-dial-to-step conversion.

10. **Use `asynPrint(pasynUser_, ...)` or `asynPrint(pC_->pasynUserSelf, ...)`** for trace logging. Do NOT use `printf` -- it bypasses the asyn trace system.

11. **Call `wakeupPoller()`** after initiating a move to trigger an immediate status poll (the base class `writeInt32` does this automatically for standard motor commands).

12. **The `pasynOctetSyncIO->connect()` call** in the constructor connects to the underlying communication port. The port name is the asyn port configured with `drvAsynIPPortConfigure` or `drvAsynSerialPortConfigure` in st.cmd.
