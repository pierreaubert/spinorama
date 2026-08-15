# Spinorama : a library to display speaker frequency response and similar graphs

[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://gitHub.com/pierreaubert/spinorama/graphs/commit-activity)
[![Website www.spinorama.org](https://img.shields.io/website-up-down-green-red/http/shields.io.svg)](https://www.spinorama.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![DeepSource](https://deepsource.io/gh/pierreaubert/spinorama.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/pierreaubert/spinorama/?ref=repository-badge)
[![Spinorama Python](https://github.com/pierreaubert/spinorama/actions/workflows/pythonapp.yml/badge.svg?branch=develop)](https://github.com/pierreaubert/spinorama/actions/workflows/pythonapp.yml)
[![Spinorama Javascript](https://github.com/pierreaubert/spinorama/actions/workflows/webapp.yml/badge.svg?branch=develop)](https://github.com/pierreaubert/spinorama/actions/workflows/webapp.yml)

This library provides an easy way to view, compare or analyse speakers data. This can help you take informed decision when buying a speaker instead of relying on commercial information or internet buzz. There are enough measurements now that you can do statistical analysis if you wanted too.

## Jump to [spinorama.org](https://spinorama.org) of all (1000+) speakers measurements.

## Jump to the [documentation](https://spinorama.org/docs) to learn more about what it can do and how to use it.

## Development setup

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12 | |
| Node.js / npm | LTS | |
| git | any | |
| Rust / cargo | stable | Optional, for the Rust scoring extension |
| maturin | stable | Optional, `pip install maturin` |

### Linux / macOS

```bash
./scripts/setup.sh
```

This installs system packages (via `apt` on Linux or `brew` on macOS), creates a
Python virtual environment, installs all dependencies, downloads third-party
assets, and compiles the Cython and Rust extensions.

### Windows (PowerShell)

Install [Python 3.12](https://www.python.org/downloads/),
[Node.js](https://nodejs.org/) and [git](https://git-scm.com/) manually, then
run:

```powershell
.\scripts\setup.ps1
```

The script automatically sets the `PYTHONUTF8=1` environment variable (both for
the current session and persistently for the user) so that Python reads files as
UTF-8 by default.  This is required on Windows where the system locale is
typically not UTF-8.  See
[Python on Windows UTF-8 mode](https://docs.python.org/3/using/windows.html#win-utf8-mode)
for details.

If you prefer to set it yourself:

```powershell
# Current session only
$env:PYTHONUTF8 = "1"

# Persistent (user-level)
[System.Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
```
