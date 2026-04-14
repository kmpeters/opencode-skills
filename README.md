# OpenCode Skills for EPICS

A collection of [OpenCode](https://opencode.ai) skills for EPICS (Experimental Physics and Industrial Control System) development. These skills provide the AI assistant with detailed, accurate reference material for writing EPICS code.

## Available Skills

| Skill | Description |
|-------|-------------|
| `streamdevice` | Write StreamDevice protocol files (`.proto`) and database records for byte-stream device communication (serial, TCP/IP, GPIB) |
| `epics-database` | Write EPICS database files (`.db`), templates (`.template`), and substitution files (`.substitutions`) for all 34 standard record types |
| `epics-module` | Create and configure EPICS IOC applications and support modules -- directory structure, Makefiles, configure files, DBD files, and st.cmd startup scripts |
| `epics-device-support` | Write custom EPICS device support in C/C++ -- dset structures, init/read/write routines, async processing, I/O Intr scanning, iocsh commands, and sub/aSub functions |
| `epics-ca-client` | Write Channel Access client programs in C -- context management, get/put/monitor, DBR types, callbacks, and error handling |
| `epics-pva-client` | Write PV Access client and server programs in C++ -- pvac API, pvData structures, normative types, SharedPV servers, and QSRV group configuration |
| `epics-libcom` | Use libCom OS-independent APIs -- threading, mutexes, events, message queues, ring buffers, timers, time stamps, error logging, linked lists, and iocsh registration |
| `asyn-port-driver` | Write asynPortDriver subclasses in C++ -- parameter library, virtual read/write methods, interface/interrupt masks, background threads, and callbacks |
| `asyn-database` | Write database records for asyn drivers -- DTYP choices, INP/OUT link format, setpoint/readback patterns, I/O Intr scanning, and array records |
| `asyn-port-config` | Configure asyn ports in st.cmd -- IP, serial, and server ports, serial options, EOS settings, trace control, and diagnostic commands |
| `asyn-gpib` | Write GPIB/SCPI device support using the devGpib framework -- gpibCmd command tables, DSET macros, EFAST tables, and custom conversions |

## Installation

Clone this repository into your OpenCode skills directory:

```bash
git clone git@git.aps.anl.gov:kpetersn/opencode-skills.git ~/.config/opencode/skills
```

If the `~/.config/opencode/skills` directory already exists, clone to a temporary location and copy:

```bash
git clone git@git.aps.anl.gov:kpetersn/opencode-skills.git /tmp/opencode-skills
cp -r /tmp/opencode-skills/*/ ~/.config/opencode/skills/
rm -rf /tmp/opencode-skills
```

Or, if you want to manage the skills directory as the git repo itself:

```bash
rm -rf ~/.config/opencode/skills   # Remove existing (back up first if needed)
git clone git@git.aps.anl.gov:kpetersn/opencode-skills.git ~/.config/opencode/skills
```

## Verification

After installation, restart OpenCode. The skills should appear in the available skills list. You can verify by checking for the skill directories:

```bash
ls ~/.config/opencode/skills/*/SKILL.md
```

Each skill is activated automatically when OpenCode detects a task matching the skill's description.

## Project-Local Installation

Skills can also be installed into a specific project's `.opencode/skills/` directory to make them available only within that project:

```bash
cd /path/to/my/project
mkdir -p .opencode/skills
git clone git@git.aps.anl.gov:kpetersn/opencode-skills.git /tmp/opencode-skills
cp -r /tmp/opencode-skills/*/ .opencode/skills/
rm -rf /tmp/opencode-skills
```

## Sources

These skills were derived from analysis of the [EPICS base 7.0](https://github.com/epics-base/epics-base) and [asyn 4.45](https://github.com/epics-modules/asyn) source code, including record type definitions, build system templates, device support headers, CA/PVA client APIs, libCom headers, asynPortDriver class, asyn device support, devGpib framework, and example programs.
