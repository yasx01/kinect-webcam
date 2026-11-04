$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$Native = Join-Path $PSScriptRoot 'native'
if (!(Test-Path "$Native/kinect_upload_fw.exe") -or !(Test-Path "$Native/kinect-driver.exe") -or !(Test-Path "$Native/libwdi.dll")) { throw 'Native build is missing.' }
python -m unittest discover -s tests/windows -v
if ($LASTEXITCODE -ne 0) { throw 'Windows tests failed.' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name KinectWebcam-Windows-x64 --distpath dist --workpath build-tools/pyinstaller --specpath build-tools --paths windows --paths v15 --collect-all pyvirtualcam --collect-all pycaw --add-data "${Native};native" --add-data "${PSScriptRoot}/WINDOWS.md;docs" --add-data "$((Resolve-Path 'v15/kinect-facecam-icon-v15.png').Path);." windows/app.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
$Exe = (Resolve-Path 'dist/KinectWebcam-Windows-x64.exe').Path
$Report = Join-Path (Resolve-Path dist).Path 'windows-selftest.json'
$env:QT_QPA_PLATFORM = 'offscreen'
$Process = Start-Process -FilePath $Exe -ArgumentList @('--self-test', ('"' + $Report + '"')) -PassThru
$null = $Process.Handle
if (!$Process.WaitForExit(60000)) { $Process.Kill(); throw 'Packaged executable self-test timed out.' }
$Process.Refresh()
if ($Process.ExitCode -ne 0) {
    if (Test-Path $Report) { Get-Content $Report -Raw | Write-Host }
    throw "Packaged executable failed: $($Process.ExitCode)"
}
$Result = Get-Content $Report -Raw | ConvertFrom-Json
if (!$Result.ok) { Get-Content $Report -Raw | Write-Host; throw 'Packaged self-test reported failure.' }
Get-FileHash $Exe -Algorithm SHA256 | Format-List | Out-File dist/windows-sha256.txt
Copy-Item windows/WINDOWS.md dist/WINDOWS.md
Copy-Item -Recurse windows/native/licenses dist/licenses
python windows/package-notices.py
if ($LASTEXITCODE -ne 0) { throw 'Dependency notice collection failed.' }
Compress-Archive -Path $Exe,dist/WINDOWS.md,dist/windows-selftest.json,dist/windows-sha256.txt,dist/licenses -DestinationPath dist/KinectWebcam-Windows-x64.zip -Force
