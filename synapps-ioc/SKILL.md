---
name: synapps-ioc
description: Create and configure synApps IOCs using mkioc and the xxx template -- mkioc options, post-creation workflow, xxx template structure, hardware configuration examples, and module customization
---

# synApps IOC Skill

You are an expert at creating and configuring EPICS IOC applications based on the synApps xxx template. You understand the `mkioc` script for IOC creation, the xxx template directory structure, the post-creation build workflow, and how to customize an IOC for specific beamline hardware.

---

## 1. Creating a New IOC with mkioc

### 1.1 Standard Usage

```bash
mkioc -n -f -s 6_3 myioc
```

This is the most common invocation. It:

1. Copies the `xxx-R6-3` template from `/APSshare/epics/synApps_6_3/support/`
2. Runs `changePrefix xxx myioc` to rename all files, directories, PV prefixes, and internal references
3. Sets `SUPPORT=/APSshare/epics/synApps_6_3/support` in `configure/RELEASE`
4. Deletes the old `.git/` directory and creates a fresh git repository with an initial commit
5. Sets world-writable permissions on `autosave/`, `bootParms/`, and `softioc/` directories

### 1.2 Post-Creation Steps

After `mkioc` completes, you must clean build artifacts from the copied template before building:

```bash
cd myioc
make distclean    # Remove build artifacts inherited from the xxx copy
# ... configure the IOC (edit settings, enable hardware) ...
make              # Build the IOC
```

**CRITICAL:** `make distclean` must be run before `make`. The copied xxx directory may contain pre-built objects from the synApps deployment that are incompatible with your configuration changes.

### 1.3 Command-Line Options

```
mkioc [options] ioc_name
```

| Option | Description |
|--------|-------------|
| `-h` | Print help |
| `-v` | Print version |
| `-f` | Create a fresh git repo (delete old `.git/`, `git init` from scratch) |
| `-n` | Do not use GitLab (no prompts, no remote repo creation) |
| `-g` | Use GitLab (create repo on `git.aps.anl.gov` and push) |
| `-s <version>` | Specify synApps version (default: `6-3`) |

### 1.4 The `-s` Version Format

The `-s` option accepts flexible version formats -- all of these are equivalent:

```bash
mkioc -n -f -s 6_3 myioc       # Underscores
mkioc -n -f -s 6-3 myioc       # Dashes
mkioc -n -f -s R6-3 myioc      # With R prefix
mkioc -n -f -s R6_3 myioc      # R prefix + underscores
```

The script normalizes the version and resolves it to the synApps installation at `/APSshare/epics/synApps_<version>/`. For example, `-s 6_3` resolves to `/APSshare/epics/synApps_6_3`.

### 1.5 The Four Code Paths

| Flags | Behavior |
|-------|----------|
| `-n` (no `-f`) | Copy xxx from APSshare, preserve git history, `make distclean`, changePrefix, update RELEASE, commit "setup" |
| `-n -f` | Copy xxx from APSshare, changePrefix, update RELEASE, delete `.git/`, `git init`, commit "Initial commit..." |
| `-g` (no `-f`) | Fetch xxx from `git.aps.anl.gov`, preserve history, changePrefix, update RELEASE, commit "setup", push to GitLab |
| `-g -f` | Clone xxx from `git.aps.anl.gov`, changePrefix, update RELEASE, delete `.git/`, `git init`, commit, push to GitLab |

**Note:** If you use `-n` without `-f` (preserving git history), the script automatically runs `make distclean`. With `-f`, it does not -- you must run `make distclean` yourself.

---

## 2. IOC Directory Structure

After running `mkioc -n -f -s 6_3 myioc`:

```
myioc/
  configure/
    RELEASE                  # Points SUPPORT to synApps, includes synApps RELEASE
    CONFIG                   # Build configuration
  myiocApp/
    src/
      Makefile               # 630-line conditional build (links all synApps modules)
      myiocMain.c            # IOC main() entry point
    Db/
      Makefile               # Installs .db, .template, .proto, .req files
      *.db                   # Application-specific databases
      *.req                  # Autosave request files
    op/
      adl/                   # MEDM display files
      ui/                    # caQtDM display files
      bob/                   # Phoebus display files
      opi/                   # CSS-BOY display files
      python/                # Python helper scripts
      burt/                  # BURT snapshot files
  iocBoot/
    iocmyioc/
      st.cmd.Linux           # Primary Linux startup script
      st.cmd.vxWorks         # vxWorks startup
      st.cmd.Win32           # Windows startup
      settings.iocsh         # Environment variables (PREFIX, IOC name, etc.)
      common.iocsh           # Shared database loading and configuration
      examples/              # Hardware configuration templates (20+ files)
        motors.iocsh
        optics.iocsh
        serial_devices.iocsh
        serial_soft.iocsh
        gpib.iocsh
        std.iocsh
        detectors/           # 18 area detector configurations
        ...
      substitutions/         # Substitution files
      autosave/              # Autosave .sav files (runtime)
      softioc/               # procServ launch infrastructure
      scripts/               # Lua scripts
  start_caQtDM_myioc        # GUI launcher scripts
  start_MEDM_myioc
  start_phoebus_myioc
  setup_epics_common         # Common environment setup
```

---

## 3. Key Configuration Files

### 3.1 configure/RELEASE

```makefile
SUPPORT=/APSshare/epics/synApps_6_3/support
EPICS_BASE=/APSshare/epics/base-7.0.8

# Pull in all synApps module paths
-include $(SUPPORT)/configure/RELEASE
```

The `-include $(SUPPORT)/configure/RELEASE` line imports all module paths (ASYN, CALC, MOTOR, SSCAN, etc.) from the centrally managed synApps deployment. To override a module path locally, create a `configure/RELEASE.local` file.

### 3.2 settings.iocsh -- IOC Identity

```bash
epicsEnvSet("IOC_NAME", "myioc")
epicsEnvSet("IOC", "ioc$(IOC_NAME)")
epicsEnvSet("IOCSH_PS1", "$(IOC)> ")
epicsEnvSet("PREFIX", "$(IOC_NAME):")
epicsEnvSet("ENGINEER", "engineer")
epicsEnvSet("LOCATION", "$(HOSTNAME=location)")
epicsEnvSet("GROUP", "group")
epicsEnvSet("EPICS_DB_INCLUDE_PATH", ".:$(TOP)/db")
epicsEnvSet("STREAM_PROTOCOL_PATH", ".:$(TOP)/db")
epicsEnvSet("EPICS_CA_MAX_ARRAY_BYTES", 64010)
```

**Edit this file** after IOC creation to set:
- `PREFIX` -- the PV prefix for all records (e.g., `"32ida:"`)
- `ENGINEER` -- responsible person
- `LOCATION` -- physical location
- `GROUP` -- organizational group
- `EPICS_CA_MAX_ARRAY_BYTES` -- increase for large waveforms/images

### 3.3 st.cmd.Linux -- Startup Script

```bash
< envPaths

errlogInit(20000)

dbLoadDatabase("../../dbd/iocmyiocLinux.dbd")
iocmyiocLinux_registerRecordDeviceDriver(pdbbase)

< settings.iocsh
< common.iocsh

# devIocStats
dbLoadRecords("$(DEVIOCSTATS)/db/iocAdminSoft.db","IOC=$(PREFIX)")
dbLoadRecords("$(TOP)/myiocApp/Db/iocAdminSoft_aliases.db","P=$(PREFIX)")

iocInit

dbl > dbl-all.txt
dbcar(0,1)
date
```

The startup script follows this pattern:
1. `< envPaths` -- load environment paths
2. `dbLoadDatabase` + `registerRecordDeviceDriver` -- load DBD and register support
3. `< settings.iocsh` -- load environment variables
4. `< common.iocsh` -- load databases (autosave, user calcs, sscan, etc.)
5. Hardware-specific `< examples/*.iocsh` includes (added by user)
6. `iocInit`

### 3.4 common.iocsh -- Shared Configuration

This file is loaded by all platform-specific st.cmd scripts. It configures:
- **Autosave**: save_restore with positions and settings files
- **sscan**: Step scanning with 1000 max data points
- **User calculations**: 20 userCalcs, userCalcOuts, userStringCalcs, userArrayCalcs, userTransforms, userAve (loaded via Lua)
- **Lua scripts**: 20 user-assignable Lua script records
- **String sequences**: sseq records
- **Interpolation tables**: 2000-point interp tables
- **Busy records**: 2 user busy records
- **caputRecorder**: Command capture/replay
- **Alive heartbeat**: Heartbeat to monitoring server
- **PVAlive**: Environment variable monitoring

---

## 4. Adding Hardware Configuration

Hardware support is added by copying example `.iocsh` files from the `examples/` directory into the IOC boot directory and including them in the startup script.

### 4.1 Available Example Configurations

| File | Hardware |
|------|----------|
| `motors.iocsh` | Motor controllers (OMS MAXv, with substitution patterns) |
| `optics.iocsh` | Slits, optical tables, monochromators, filters, mirrors |
| `serial_devices.iocsh` | 15+ serial instruments (Eurotherm, Keithley, Lakeshore, MKS, etc.) |
| `serial_soft.iocsh` | Local serial ports and MOXA NPort TCP/IP terminal servers |
| `gpib.iocsh` | GPIB bus instruments |
| `industryPack.iocsh` | Industry Pack carrier modules (Acromag, SBS) |
| `std.iocsh` | Standard utility records (ramp/tweak, 4-step, pvHistory, timers) |
| `vme.iocsh` | VME bus devices |
| `softGlue.iocsh` | FPGA-based custom logic |
| `quadEM.cmd` | Electrometers |
| `canberra_*.cmd` | Nuclear spectroscopy |
| `detectors/*.iocsh` | 18 area detector configurations (SimDetector, Pilatus, Eiger, Prosilica, etc.) |

### 4.2 Enabling Hardware

1. Copy the relevant example to the boot directory:
   ```bash
   cp iocBoot/iocmyioc/examples/motors.iocsh iocBoot/iocmyioc/
   ```

2. Edit the copied file to match your hardware (IP addresses, port names, motor assignments, etc.)

3. Add a line to `st.cmd.Linux` (before `iocInit`):
   ```bash
   < motors.iocsh
   ```

4. Rebuild if you added new substitution files:
   ```bash
   make
   ```

### 4.3 Example: Adding Motors

Copy `examples/motors.iocsh` and `examples/substitutions/motor.substitutions`, then edit:

```bash
# In motors.iocsh -- configure the motor controller
drvAsynIPPortConfigure("MC1", "192.168.1.100:2000", 0, 0, 0)
myMotorCreateController("MC1Port", "MC1", 4, 0.1, 1.0)

# Load motor records from substitutions
dbLoadTemplate("substitutions/motor.substitutions")
```

### 4.4 Example: Adding Serial Instruments

Copy `examples/serial_soft.iocsh` and `examples/serial_devices.iocsh`:

```bash
# In serial_soft.iocsh -- configure serial port (MOXA NPort)
drvAsynIPPortConfigure("serial1", "192.168.1.200:4001", 0, 0, 0)
asynOctetSetInputEos("serial1", 0, "\r\n")
asynOctetSetOutputEos("serial1", 0, "\r\n")

# In serial_devices.iocsh -- load instrument databases
dbLoadRecords("$(IP)/db/Keithley2kDMM_mf.db", "P=$(PREFIX),Ession=B0,PORT=serial1,A=-1")
```

---

## 5. Customizing the Build (src/Makefile)

### 5.1 How Conditional Module Linking Works

The xxx `src/Makefile` uses `ifdef` guards so modules are only linked if their path is defined in `configure/RELEASE`:

```makefile
ifdef ASYN
  myioc_DBD += asyn.dbd
  myioc_DBD += drvAsynSerialPort.dbd
  myioc_DBD += drvAsynIPPort.dbd
  myioc_LIBS += asyn
endif

ifdef MOTOR
  myioc_DBD += motorSupport.dbd
  myioc_DBD += devSoftMotor.dbd
  myioc_DBD += motorSimSupport.dbd
  myioc_LIBS += motor softMotor motorSimSupport
endif
```

To remove a module from the IOC build, comment out its line in the synApps `configure/RELEASE` or override it to empty in your IOC's `configure/RELEASE.local`:

```makefile
# configure/RELEASE.local -- disable modules not needed
GALIL=
DXP=
XSPRESS3=
YOKOGAWA_DAS=
```

### 5.2 Platform-Specific Modules

Some modules are only built for specific platforms:

```makefile
# Linux-only
ifdef GALIL
  myioc_DBD_Linux += GalilSupport.dbd
  myioc_LIBS_Linux += GalilSupport
endif

# vxWorks-only
ifdef ALLEN_BRADLEY
  myioc_DBD_vxWorks += allenBradley.dbd
  myioc_LIBS_vxWorks += allenBradley
endif
```

### 5.3 Adding a New Module

To add a module not already in the xxx Makefile:

1. Add the module path to `configure/RELEASE` (or ensure it's in the synApps RELEASE):
   ```makefile
   MYMODULE = /path/to/myModule
   ```

2. Add the DBD and library to `src/Makefile`:
   ```makefile
   ifdef MYMODULE
     myioc_DBD += myModuleSupport.dbd
     myioc_LIBS += myModule
   endif
   ```

3. Rebuild:
   ```bash
   make
   ```

### 5.4 The DBD Naming Convention

The composite DBD file is named based on the OS:

| Platform | DBD Name |
|----------|----------|
| Linux | `iocmyiocLinux.dbd` |
| vxWorks | `iocmyiocVX.dbd` |
| Darwin | `iocmyiocDarwin.dbd` |
| Windows 32 | `iocmyiocWin32.dbd` |
| Windows 64 | `iocmyiocWin64.dbd` |
| Cygwin | `iocmyiocCygwin.dbd` |

The st.cmd must reference the correct one for the platform.

---

## 6. Modules Available in the xxx Template

The xxx template can link against all synApps modules. Here are the major categories:

### Core Infrastructure
asyn, autosave, busy, calc, sscan, std, devIocStats, alive, caputRecorder, lua, SNCSEQ

### Motion Control
motor (with 20+ driver submodules: OMS, Newport, Aerotech, IMS, Parker, PI, Kohzu, Mclennan, Micos, MicroMo, NewFocus, Oriel, SmartMotor, ThorLabs, Attocube, Faulhaber, ACS, Galil, DeltaTau, softMotor, motorSim)

### Detectors (via areaDetector)
ADCore + plugins, SimDetector, Andor, Aravis, Vimba, Spinnaker, PointGrey, Prosilica, Pixirad, Mar345, Pilatus, Eiger, URL, PVA driver

### Communication
StreamDevice, modbus, EtherIP, OPCUA

### Optics
optics (slits, tables, monochromators, filters, mirrors, orientation matrix)

### Data Acquisition
mca, dxp, dxpSITORO, Dante, quadEM, measComp, LabJack, scaler

### Hardware I/O
ipac, ip, ip330, ipUnidig, vme, camac, dac128V, softGlue, softGlueZynq

### Other
delaygen, vac, love, Yokogawa_DAS, xspress3, allenBradley

---

## 7. The softioc Launcher

The `iocBoot/iocmyioc/softioc/` directory contains infrastructure for running the IOC under `procServ` (a process supervisor that provides a detached console):

```
softioc/
  run                    # Main launch script
  in-screen.sh           # Alternative: run in GNU screen
  myioc.pl               # Perl launch wrapper
  logs/
    iocConsole            # Console log directory
    remote                # Remote access log directory
```

---

## 8. Key Rules and Pitfalls

1. **Always run `make distclean` before `make`** after creating an IOC with mkioc. The copied xxx directory contains build artifacts from the synApps deployment that must be cleaned.

2. **Edit `settings.iocsh` first** to set the correct `PREFIX`, `ENGINEER`, and `LOCATION`. The PREFIX determines all PV names in the IOC.

3. **Do not edit `common.iocsh` directly** unless you understand the consequences. It provides standard subsystems (autosave, sscan, user calcs) that most IOCs need. Instead, add hardware by including example `.iocsh` files in `st.cmd.Linux`.

4. **Hardware configuration goes in `st.cmd.Linux`** (or the platform-specific st.cmd), NOT in `common.iocsh`. Add `< myHardware.iocsh` lines before `iocInit`.

5. **The xxx Makefile links everything by default.** If you only need a few modules, disable unused ones via `configure/RELEASE.local` to reduce build time and IOC binary size.

6. **The `examples/` directory is a reference, not a live configuration.** Files in `examples/` are NOT loaded by the IOC. You must copy them to the `iocBoot/iocmyioc/` directory and include them in `st.cmd.Linux`.

7. **If you copied xxx manually** without using mkioc, you need to run `changePrefix xxx myioc` from the IOC top directory. The `xxxApp/` directory and `iocBoot/` directory must exist in the current working directory.

8. **The `-s` version must correspond to an installed synApps** at `/APSshare/epics/synApps_<version>/`. If the directory doesn't exist, mkioc will exit with an error.

9. **QSRV (PV Access server) is always linked** in the xxx template (not conditional). All PVs are automatically available via both Channel Access and PV Access.

10. **The `autosave/` directory must be writable** by the IOC process at runtime. mkioc sets `chmod a+w` on this directory automatically.
