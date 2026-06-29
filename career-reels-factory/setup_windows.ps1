$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "== Check Python 3.12 =="
try {
    & py -3.12 --version
} catch {
    Write-Host "Python 3.12 was not found. Installing with winget..."
    & winget install --id Python.Python.3.12 -e
    Write-Host "Python was installed. Close and reopen PowerShell, then run this script again."
    exit 0
}

Write-Host "== Check FFmpeg =="
try {
    & ffmpeg -version | Select-Object -First 1
} catch {
    Write-Host "FFmpeg was not found. Installing with winget..."
    & winget install --id Gyan.FFmpeg -e
    Write-Host "FFmpeg was installed. Close and reopen PowerShell, then run this script again."
    exit 0
}

$filters = & ffmpeg -hide_banner -filters 2>$null
if (($filters -notmatch "subtitles") -or ($filters -notmatch "drawtext")) {
    Write-Warning "FFmpeg may be missing the subtitles or drawtext filter. Install a full FFmpeg build if video composition fails."
}

Write-Host "== Create Python venv =="
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & py -3.12 -m venv .venv
}

Write-Host "== Install Python packages =="
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env was created. Run: notepad .env"
} else {
    Write-Host ".env already exists. Skipping."
}

Write-Host ""
Write-Host "Done. Next:"
Write-Host "1. notepad .env"
Write-Host "2. Fill GROQ_API_KEY"
Write-Host "3. .\run_windows.ps1"
