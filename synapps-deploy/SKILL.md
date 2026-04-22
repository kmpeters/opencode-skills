---
name: synapps-deploy
description: Deploy and configure EPICS synApps -- assemble_synApps script usage, module customization, building, creating IOCs from the xxx template, and managing module versions
---

# synApps Deployment Skill

You are an expert at deploying and configuring EPICS synApps. synApps is a curated collection of ~40 EPICS support modules that have been tested and confirmed to work together. You understand the `assemble_synApps` script, the support build infrastructure, and how to create IOC applications from the `xxx` template.

---

## 1. What is synApps?

synApps is a distribution of EPICS support modules maintained by the APS BCDA group. It includes:

- **Core infrastructure**: asyn, autosave, busy, calc, sscan, std, devIocStats
- **Communication**: StreamDevice, modbus, EtherIP
- **Motor control**: motor (with all driver submodules), Galil
- **Detectors**: areaDetector (with ADCore, ADSupport, ADSimDetector)
- **Data acquisition**: mca, dxp, quadEM, measComp, LabJack
- **Sequencer**: SNCSEQ (State Notation Language)
- **Hardware I/O**: ipac, ip, ip330, ipUnidig, vme, camac, dac128V, softGlue
- **Optics**: optics, delaygen
- **Utilities**: alive, caputRecorder, love, vac, lua, scaler, Yokogawa_DAS
- **Template IOC**: xxx (starting point for new IOC applications)

The `assemble_synApps` script clones all modules from GitHub at tested version tags and configures them to build together with a single `make` command.

---

## 2. Prerequisites

Before deploying synApps you need:

1. **EPICS base** installed and built (7.0.x recommended)
2. **Git** installed
3. **Perl** (v5.12+) for the assemble script
4. **Standard build tools**: make, C/C++ compiler (gcc/g++)
5. **re2c** (required by the sequencer module)
6. Optional: **libusb**, **libtirpc-devel** (RHEL 8+), **libnet-dev**

---

## 3. Deploying synApps

### 3.1 Quick Start (Default Configuration)

```bash
# Download the assemble script
git clone https://github.com/EPICS-synApps/assemble_synApps.git
cd assemble_synApps

# Deploy synApps with your EPICS base location
./assemble_synApps --base=/path/to/epics/base

# Build (this takes a while -- 40+ modules)
cd git/support
make -j4        # Use parallel jobs to speed up the build
```

This creates a `git/support/` directory containing all modules at default versions.

### 3.2 Custom Directory Name

```bash
./assemble_synApps --base=/path/to/base --dir=synApps_R6-3
# Creates synApps_R6-3/support/
```

### 3.3 Dry Run (Check Configuration)

```bash
./assemble_synApps --base=/path/to/base --check
```

Prints the module list and versions without downloading anything.

---

## 4. Command-Line Options

```
./assemble_synApps [options]
```

| Option | Description |
|--------|-------------|
| `--base=/path/to/base` | Set the EPICS base installation path (required) |
| `--dir=name` | Set the output directory name (default: `git`) |
| `--config=file` | Use an external config file instead of default module list |
| `--set MODULE=TAG` | Override a single module version (repeatable) |
| `--check` | Display module list without downloading |
| `--help` | Print usage information |

---

## 5. Customizing the Module Set

### 5.1 Override Individual Module Versions

```bash
./assemble_synApps --base=/path/to/base \
    --set ASYN=R4-45 \
    --set MOTOR=R7-3-1 \
    --set CALC=R3-7-5
```

### 5.2 Remove a Module

```bash
# Set module to empty string to exclude it
./assemble_synApps --base=/path/to/base --set GALIL= --set DXP= --set XSPRESS3=
```

### 5.3 Add Extra areaDetector Submodules

```bash
# AREA_DETECTOR_SUBMODULES is a space-separated list
./assemble_synApps --base=/path/to/base \
    --set "AREA_DETECTOR_SUBMODULES=ADProsilica ADPointGrey ADPilatus"
```

### 5.4 Use a Config File

Create a text file with one `MODULE=TAG` per line:

```
# myconfig.txt -- minimal synApps
ASYN=R4-44-2
AUTOSAVE=R5-11
BUSY=R1-7-4
CALC=R3-7-5
SSCAN=R2-11-6
DEVIOCSTATS=3.1.16
SNCSEQ=R2-2-9
STD=R3-6-4
STREAM=2.8.24
XXX=R6-3
```

```bash
./assemble_synApps --base=/path/to/base --config=myconfig.txt
```

**Note:** A config file completely replaces the default module list. Only modules listed in the file will be downloaded.

---

## 6. Default Module Versions (synApps R6-3)

| Module | Tag | GitHub Source |
|--------|-----|--------------|
| ALIVE | R1-4-1 | epics-modules/alive |
| ALLENBRADLEY | 2.3 | (tarball from epics.anl.gov) |
| AREA_DETECTOR | R3-12-1 | areaDetector/areaDetector |
| ASYN | R4-44-2 | epics-modules/asyn |
| AUTOSAVE | R5-11 | epics-modules/autosave |
| BUSY | R1-7-4 | epics-modules/busy |
| CALC | R3-7-5 | epics-modules/calc |
| CAMAC | R2-7-5 | epics-modules/camac |
| CAPUTRECORDER | R1-7-6 | epics-modules/caputRecorder |
| DAC128V | R2-10-1 | epics-modules/dac128V |
| DELAYGEN | R1-2-4 | epics-modules/delaygen |
| DEVIOCSTATS | 3.1.16 | epics-modules/iocStats |
| DXP | R6-1 | epics-modules/dxp |
| DXPSITORO | R1-3 | epics-modules/dxpSITORO |
| ETHERIP | ether_ip-3-3 | epics-modules/ether_ip |
| GALIL | V3-5 | motorapp/Galil-3-0 |
| IP | R2-22 | epics-modules/ip |
| IP330 | R2-10 | epics-modules/ip330 |
| IPAC | 2.16 | epics-modules/ipac |
| IPUNIDIG | R2-12 | epics-modules/ipUnidig |
| LABJACK | R3-0 | epics-modules/LabJack |
| LOVE | R3-2-9 | epics-modules/love |
| LUA | R3-1 | epics-modules/lua |
| MCA | R7-10 | epics-modules/mca |
| MEASCOMP | R4-2 | epics-modules/measComp |
| MODBUS | R3-3 | epics-modules/modbus |
| MOTOR | R7-3-1 | epics-modules/motor |
| OPTICS | R2-14 | epics-modules/optics |
| QUADEM | R9-5 | epics-modules/quadEM |
| SCALER | 4.1 | epics-modules/scaler |
| SNCSEQ | R2-2-9 | mdavidsaver/sequencer-mirror |
| SOFTGLUE | R2-8-4 | epics-modules/softGlue |
| SOFTGLUEZYNQ | R2-0-5 | epics-modules/softGlueZynq |
| SSCAN | R2-11-6 | epics-modules/sscan |
| STD | R3-6-4 | epics-modules/std |
| STREAM | 2.8.24 | paulscherrerinstitute/StreamDevice |
| VAC | R1-9-2 | epics-modules/vac |
| VME | R2-9-5 | epics-modules/vme |
| XSPRESS3 | 3.2.8 | epics-modules/xspress3 |
| XXX | R6-3 | epics-modules/xxx |
| YOKOGAWA_DAS | R2-0-2 | epics-modules/Yokogawa_DAS |

---

## 7. Directory Structure After Assembly

```
synApps/
  support/
    configure/
      RELEASE              # Master file: all module paths
      CONFIG_SITE           # Site-specific build flags
      makeReleaseConsistent.pl
    Makefile               # Top-level: dependency resolution, build ordering
    utils/
      changePrefix         # IOC prefix renaming tool
      depends.pl           # Module dependency computation
      copyScreens.pl       # Aggregate display files
    alive-R1-4-1/
    asyn-R4-44-2/
    autosave-R5-11/
    busy-R1-7-4/
    calc-R3-7-5/
    ...                    # All other modules
    areaDetector-R3-12-1/
      ADCore/
      ADSupport/
      ADSimDetector/
    motor-R7-3-1/
      modules/             # Motor driver submodules
    xxx-R6-3/              # Template IOC application
```

---

## 8. Building synApps

### 8.1 First Build

```bash
cd synApps/support

# Propagate all paths (done automatically by assemble, but needed after manual changes)
make release

# Build all modules in dependency order
make -j4
```

### 8.2 Rebuild After RELEASE Changes

```bash
make release    # Re-propagate paths
make rebuild    # Clean and rebuild everything
```

### 8.3 Remove a Module After Assembly

1. Comment out or delete the module's line in `configure/RELEASE`
2. Run `make release`
3. Run `make rebuild`

### 8.4 Update a Module Version

1. Delete the old module directory
2. Clone the new version: `git clone https://github.com/epics-modules/<repo>.git <name>-<tag> && cd <name>-<tag> && git checkout <tag>`
3. Update the path in `configure/RELEASE`
4. Run `make release`
5. Run `make rebuild`

---

## 9. Creating a New IOC from the xxx Template

The `xxx` module is a template IOC application that imports support from all synApps modules. To create a new IOC:

### 9.1 Copy and Rename

```bash
cd synApps/support

# Copy the xxx template
cp -r xxx-R6-3 /path/to/my/iocTop

# Rename from xxx to your IOC name
cd /path/to/my/iocTop
../../support/utils/changePrefix xxx myioc
```

### 9.2 changePrefix Usage

```
changePrefix old new
```

- `old` is the current prefix (typically `xxx`)
- `new` is your IOC name (e.g., `1bma`, `myDetector`, `beamline`)

The script renames:
- `xxxApp/` directory to `myiocApp/`
- Source files: `xxxMain.cpp` to `myiocMain.cpp`
- IOC boot directory: `iocBoot/iocxxx/` to `iocBoot/iocmyioc/`
- All PV prefixes in `.cmd`, `.iocsh`, `.substitutions`, `.template`, `.req` files
- GUI launcher scripts and display files (`.adl`, `.ui`, `.opi`)
- All internal references in Makefiles and DBD files

### 9.3 Configure the IOC

After renaming:

1. Edit `configure/RELEASE` to point to the synApps support directory:
   ```makefile
   SUPPORT = /path/to/synApps/support
   -include $(SUPPORT)/configure/RELEASE
   ```

2. Edit `iocBoot/iocmyioc/st.cmd` to configure your specific hardware (asyn ports, motor controllers, detector drivers, database loads, etc.)

3. Edit `.substitutions` files to define your PV instances

4. Build:
   ```bash
   make
   ```

---

## 10. Key Files in the Support Infrastructure

| File | Purpose |
|------|---------|
| `configure/RELEASE` | Master module path definitions. Single source of truth. |
| `configure/CONFIG_SITE` | Site-specific build flags (LINUX_USB_INSTALLED, etc.) |
| `configure/makeReleaseConsistent.pl` | Propagates paths from master RELEASE to all module RELEASE files |
| `Makefile` | Computes inter-module dependencies, builds in correct order |
| `utils/depends.pl` | Parses a module's RELEASE to determine its dependencies |
| `utils/changePrefix` | Renames an IOC application (prefix, files, directories) |
| `utils/copyScreens.pl` | Collects display files from all modules into one directory |

---

## 11. Key Rules and Pitfalls

1. **Always run `make release` after editing `configure/RELEASE`.** This propagates the path changes to all module RELEASE files via `makeReleaseConsistent.pl`. Without it, modules will have stale paths and the build will fail.

2. **EPICS base must be built before synApps.** The `--base` path must point to a fully built EPICS base installation.

3. **The `--config` option completely replaces the default module list.** If you use a config file but omit a module that other modules depend on (e.g., asyn), the build will fail.

4. **Module directory names follow the pattern `<repo>-<tag>`** with dots replaced by dashes. For example, ASYN tag `R4-44-2` clones into `asyn-R4-44-2/`. This naming convention is used by the master RELEASE file.

5. **Read and write modbus/motor/areaDetector ports share the same underlying TCP connection.** When configuring these in your IOC, ensure write-only ports use the same `drvAsynIPPortConfigure` port name as at least one read port to avoid TCP timeouts.

6. **RHEL 8+ requires TIRPC.** The assemble script auto-detects this and sets `TIRPC=YES` in asyn's CONFIG_SITE. If building manually, ensure `/usr/include/tirpc/rpc/rpc.h` exists and `TIRPC=YES` is set.

7. **areaDetector submodules must be explicitly initialized.** The assemble script does this automatically. If adding areaDetector to a manual synApps build, run `git submodule init` and `git submodule update` for ADCore, ADSupport, and any detector submodules.

8. **`make -jN` for parallel builds** works at the top level because the Makefile resolves inter-module dependencies. However, the first build may be slow as the dependency graph is computed. Subsequent rebuilds are faster.

9. **To build a subset of modules**, temporarily comment out unwanted modules in `configure/RELEASE`, run `make release`, and then `make`. Modules that depend on commented-out modules will also fail to build -- check `utils/depends.pl` output for the dependency chain.

10. **The `xxx` IOC includes support for ALL synApps modules.** After copying and renaming, remove database loads and st.cmd sections for modules you don't need. This reduces startup time and avoids loading unnecessary device support.
