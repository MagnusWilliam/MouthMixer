# MouthMixer setup for Windows: makes a Python environment, installs MouthMixer and creates the
# desktop and Start-menu shortcuts. Safe to run again (it updates everything in place).
#   Run:  right-click setup.cmd > Open, or in PowerShell:  .\scripts\windows\setup.ps1 [-StartWithWindows]
param([switch]$StartWithWindows)
$ErrorActionPreference = "Stop"
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Repo

Write-Host "== MouthMixer setup ==" -ForegroundColor Cyan

# 1. Find Python 3.11-3.13 (3.12 recommended).
$Py = $null
foreach ($v in @("3.12", "3.13", "3.11")) {
  try { & py "-$v" -c "import sys" 2>$null; if ($LASTEXITCODE -eq 0) { $Py = @("py", "-$v"); break } } catch {}
}
if (-not $Py) {
  try { & python -c "import sys; assert (3,11) <= sys.version_info[:2] <= (3,13)" 2>$null; if ($LASTEXITCODE -eq 0) { $Py = @("python") } } catch {}
}
if (-not $Py) {
  Write-Host "Python 3.12 isn't installed. Install it with:" -ForegroundColor Yellow
  Write-Host "    winget install Python.Python.3.12"
  Write-Host "then run this setup again."
  exit 1
}
Write-Host "Using Python: $($Py -join ' ')"

# 2. Virtual environment + install. It lives in %LOCALAPPDATA%\MouthMixer\venv, not in the repo folder,
#    so OneDrive (or any synced folder) doesn't try to sync thousands of Python files.
$Venv = Join-Path $env:LOCALAPPDATA "MouthMixer\venv"
if (Test-Path (Join-Path $Repo ".venv\Scripts\python.exe")) {
  Write-Host "Removing the old environment from the repo folder (moved to $Venv)."
  Remove-Item -Recurse -Force (Join-Path $Repo ".venv")
}
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
  & $Py[0] $Py[1..9] -m venv $Venv
}
$VPy = Join-Path $Venv "Scripts\python.exe"
$VPyw = Join-Path $Venv "Scripts\pythonw.exe"
# A MouthMixer that's already running would keep using the old code: ask it to quit first.
if (Test-Path (Join-Path $Venv "Scripts\python.exe")) {
  try { & (Join-Path $Venv "Scripts\python.exe") -m mouthmixer stop 2>$null } catch {}
}
# Older versions don't know "stop": end a MouthMixer that still serves the app's port (from settings.json,
# default 8765). Only MouthMixer itself: another program on that port (a dev server) is left alone.
$Port = 8765
$SettingsFile = Join-Path $env:USERPROFILE "MouthMixer\settings.json"
if (Test-Path $SettingsFile) {
  try { $s = Get-Content $SettingsFile -Raw | ConvertFrom-Json; if ($s.port) { $Port = [int]$s.port } } catch {}
}
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" -ErrorAction SilentlyContinue
  if ($proc -and $proc.CommandLine -match "mouthmixer") { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
& $VPy -m pip install --upgrade pip --quiet
& $VPy -m pip install -e ".[windows,dev]" --quiet
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# 3. Icon + shortcuts.
$Ico = Join-Path $Repo "scripts\windows\mouthmixer.ico"
& $VPy -m mouthmixer.icon $Ico
$Shell = New-Object -ComObject WScript.Shell
function New-Shortcut([string]$Path, [string]$Arguments) {
  $s = $Shell.CreateShortcut($Path)
  $s.TargetPath = $VPyw
  $s.Arguments = $Arguments
  $s.WorkingDirectory = "$Repo"
  $s.IconLocation = $Ico
  $s.Description = "MouthMixer: hums and beatbox into music"
  $s.Save()
}
$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "MouthMixer.lnk"
New-Shortcut (Join-Path $Desktop "MouthMixer.lnk") "-m mouthmixer launch"
New-Shortcut $StartMenu "-m mouthmixer launch"
Write-Host "Shortcuts created on the desktop and in the Start menu."

$Startup = Join-Path ([Environment]::GetFolderPath("Startup")) "MouthMixer listener.lnk"
if ($StartWithWindows) {
  New-Shortcut $Startup "-m mouthmixer listen"
  Write-Host "The listener will start with Windows (tray icon only; open the app from the shortcut)."
} elseif (Test-Path $Startup) {
  Remove-Item $Startup
}

# 4. Quick self-check (no mic needed).
& $VPy -m pytest -q --no-header -p no:cacheprovider tests
if ($LASTEXITCODE -ne 0) { Write-Host "Some self-checks failed; MouthMixer may still run. Send Claude the output above." -ForegroundColor Yellow }

Write-Host ""
Write-Host "Done. Double-click 'MouthMixer' on your desktop." -ForegroundColor Green
Write-Host "Your clips live in $env:USERPROFILE\MouthMixer (never uploaded anywhere)."
Write-Host "Command line, if you ever need it: $VPy -m mouthmixer --help"
