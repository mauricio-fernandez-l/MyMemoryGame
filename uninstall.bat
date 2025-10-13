@echo off
echo cd into script directory ...
cd /d %~dp0
setlocal
echo Resolve shortcut name from config.yaml ...
for /f "usebackq tokens=* delims=" %%I in (`powershell -NoProfile -Command ^
    "$text='Memory';" ^
    "if (Test-Path 'config.yaml') {" ^
    "  $lines = Get-Content 'config.yaml';" ^
    "  $inTitle = $false;" ^
    "  foreach ($line in $lines) {" ^
    "    if ($inTitle -and $line -match '^\s*text\s*:\s*(.+)$') {" ^
    "      $val = $matches[1];" ^
    "      $val = $val.Trim();" ^
    "      $val = $val.Trim([char]34);" ^
    "      $val = $val.Trim([char]39);" ^
    "      if (-not [string]::IsNullOrWhiteSpace($val)) { $text = $val }" ^
    "      break" ^
    "    }" ^
    "    if ($line -match '^\s*title\s*:\s*$') { $inTitle = $true; continue }" ^
    "    if ($inTitle -and $line -match '^\S') { break }" ^
    "  }" ^
    "}" ^
    "$invalid = [IO.Path]::GetInvalidFileNameChars();" ^
    "$clean = -join ($text.ToCharArray() | ForEach-Object { if ($invalid -contains $_) { '_' } else { $_ } });" ^
    "if ([string]::IsNullOrWhiteSpace($clean)) { $clean = 'Memory' }" ^
    "Write-Output $clean"`) do set "SHORTCUT_NAME=%%I"

if "%SHORTCUT_NAME%"=="" set "SHORTCUT_NAME=Memory"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\%SHORTCUT_NAME%.lnk"
echo Remove desktop shortcut ...
if exist "%SHORTCUT_PATH%" (
    echo Removing %SHORTCUT_PATH%
    del "%SHORTCUT_PATH%"
) else (
    echo Shortcut not found: %SHORTCUT_PATH%
)
echo Remove .venv ...
if exist .venv (
    rmdir /s /q .venv
)
endlocal
echo Done.
pause
