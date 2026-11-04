$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $IsWindows -and $env:OS -ne 'Windows_NT') { throw 'EXE būvēšana jāveic Windows vidē.' }
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Nepieciešams Python 3.12.' }
& .\.venv\Scripts\python.exe -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Atkarību instalēšana neizdevās.' }
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Testi neizdevās.' }
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name IepirkumuAsistents --paths . --add-data 'templates\oficiala_2026.docx;templates' scripts\run_app.py
if ($LASTEXITCODE -ne 0) { throw 'EXE būvēšana neizdevās.' }
# Verify the actual EXE and its bundled template before distributing it.
$report = Join-Path (Get-Location) 'dist\windows-smoke.json'
Remove-Item $report -ErrorAction SilentlyContinue
$process = Start-Process -FilePath '.\dist\IepirkumuAsistents\IepirkumuAsistents.exe' -ArgumentList @('--smoke-test', ('"' + $report + '"')) -PassThru
if (-not $process.WaitForExit(60000)) {
    $process.Kill()
    throw 'EXE palaišanas pārbaude pārsniedza 60 sekundes.'
}
$process.Refresh()
if ($process.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'EXE palaišanas pārbaude neizdevās.' }
$result = Get-Content -Raw $report | ConvertFrom-Json
if ($result.status -ne 'passed' -or -not $result.frozen -or $result.platform -ne 'win32') { throw 'Nederīgs Windows EXE pārbaudes rezultāts.' }
Compress-Archive -Path dist\IepirkumuAsistents -DestinationPath dist\IepirkumuAsistents-Windows.zip -Force
Write-Host 'Gatavs: dist\IepirkumuAsistents-Windows.zip. Izpakojiet visu mapi un atveriet EXE.'
