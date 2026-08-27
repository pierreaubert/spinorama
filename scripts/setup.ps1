# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

## package check
## ----------------------------------------------------------------------

$ErrorActionPreference = "Stop"

$PYVERSION = "3.12"

# ------------ UTF-8
# Windows does not default to UTF-8 for Python; enable it via PYTHONUTF8.
# See https://docs.python.org/3/using/windows.html#win-utf8-mode
#     https://docs.python.org/3/using/cmdline.html#envvar-PYTHONUTF8
$env:PYTHONUTF8 = "1"
[System.Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
Write-Host "Set PYTHONUTF8=1 (session + user environment)"

# ------------ CHECK PREREQUISITES
$missing = @()
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) { $missing += "python $PYVERSION (https://www.python.org/downloads/)" }
if (-not (Get-Command "npm"    -ErrorAction SilentlyContinue)) { $missing += "Node.js / npm (https://nodejs.org/)" }
if (-not (Get-Command "git"    -ErrorAction SilentlyContinue)) { $missing += "git (https://git-scm.com/)" }

if ($missing.Count -gt 0) {
    Write-Host "`nThe following tools are required but not found in PATH:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host "`nInstall them and re-run this script.`n" -ForegroundColor Red
    exit 1
}

# Verify Python version
$pyVer = python --version 2>&1
Write-Host "Detected: $pyVer"

# ------------ PYTHONPATH
$env:PYTHONPATH = ".\src;.\src\website"

# ------------ PYTHON VENV
Write-Host "`n--- Creating Python virtual environment ---"
python -m venv .venv
& .\.venv\Scripts\Activate.ps1

# ------------ PIP PACKAGES
Write-Host "`n--- Installing Python dependencies ---"
pip install -U pip
$reqFiles = @(
    "requirements.txt",
    "requirements-test.txt",
    "requirements-dev.txt",
    "requirements-api.txt",
    "requirements-meta.txt",
    "requirements-scrape.txt"
)
foreach ($req in $reqFiles) {
    if (Test-Path $req) {
        Write-Host "Installing $req ..."
        pip install -U -r $req
    } else {
        Write-Host "Skipping $req (not found)" -ForegroundColor Yellow
    }
}

# ------------ NODE PACKAGES
Write-Host "`n--- Installing Node dependencies ---"
npm install .

# ------------ LINT
Write-Host "`n--- Running flake8 lint check ---"
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude .venv

# ------------ 3RD PARTIES
Write-Host "`n--- Installing 3rd-party assets ---"

# Versions must match scripts/update_3rdparties.sh
$PLOTLY      = "3.4.0"
$HANDLEBARS  = "4.7.8"
$BULMA       = "1.0.4"
$FUSE        = "7.0.0"

$ASSETS      = ".\dist"
$ASSETS_JS   = "$ASSETS\js3rd"
$ASSETS_CSS  = "$ASSETS\css"
$ASSETS_JSON = "$ASSETS\json"

New-Item -ItemType Directory -Force -Path $ASSETS, $ASSETS_JS, $ASSETS_CSS, $ASSETS_JSON | Out-Null

# Handlebars
$hbsFile = "$ASSETS_JS\handlebars-$HANDLEBARS.min.js"
if (-not (Test-Path $hbsFile)) {
    Write-Host "Downloading Handlebars $HANDLEBARS ..."
    Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/handlebars@$HANDLEBARS/dist/handlebars.min.js" -OutFile $hbsFile
}

# Bulma (compile from SCSS)
npm install bulma
npx sass --load-path=node_modules src/website/bulma4spin.scss "dist\css\bulma-$BULMA.min.css" --style=compressed --no-source-map

# Fuse.js
npm install fuse.js
Copy-Item "node_modules\fuse.js\dist\fuse.min.mjs" "$ASSETS_JS\fuse-$FUSE.min.mjs" -Force

# Plotly
npm install plotly.js-dist-min
Copy-Item "node_modules\plotly.js-dist-min\plotly.min.js" "$ASSETS_JS\plotly-$PLOTLY.min.mjs" -Force

# ------------ CREATE DIRECTORIES
Write-Host "`n--- Creating build directories ---"
New-Item -ItemType Directory -Force -Path "build", "dist" | Out-Null

# ------------ COMPILE CYTHON
Write-Host "`n--- Building Cython extension ---"
Push-Location src\spinorama\compute_scores_cython
try {
    $env:PYTHONPATH = "..\..\.."
    python setup.py build_ext --inplace
    # On Windows the extension is a .pyd, not .so
    $pydFile = Get-ChildItem -Filter "compute_scores_cython.*.pyd" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pydFile) {
        Write-Host "Cython extension built: $($pydFile.Name)"
    } else {
        Write-Host "Warning: Cython .pyd not found after build" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
    $env:PYTHONPATH = ".\src;.\src\website"
}

# ------------ COMPILE AND INSTALL RUST
Write-Host "`n--- Building and installing Rust extensions ---"
if (-not (Get-Command "maturin" -ErrorAction SilentlyContinue)) {
    throw "maturin not found after dependency installation"
}

maturin develop --release --manifest-path "src\spinorama\compute_scores_rust\Cargo.toml"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install compute_scores_rust"
}

maturin develop --release --manifest-path "src\spinorama\annotations_rust\Cargo.toml"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install annotations_rust"
}

# Do not silently fall back to the Python implementations after setup.
python -c "import annotations_rust, compute_scores_rust; from spinorama.plot import annotations; assert annotations._c_place_annotations is not None; print('Rust extensions installed successfully')"
if ($LASTEXITCODE -ne 0) {
    throw "Rust extension import verification failed"
}

Write-Host "`n--- Setup complete ---" -ForegroundColor Green
