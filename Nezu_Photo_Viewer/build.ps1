param([string]$ImagesFolder)

$ErrorActionPreference = 'Stop'
$KitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path $KitRoot 'tools'
$Generated = Join-Path $KitRoot 'generated'
$PyDeps = Join-Path $Tools 'pydeps'
$NwlinkRoot = Join-Path $Tools 'nwlink'
$null = New-Item -ItemType Directory -Force -Path $Tools, $PyDeps, $Generated

function Find-Python {
  $found = Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python*\python.exe') -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
  if ($found) { return $found }
  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { return $cmd.Source }
  throw 'Python 3 is required. Install it from python.org, then run this file again.'
}

function Invoke-Python([string[]]$Arguments) {
  & $script:Python @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Python exited with code $LASTEXITCODE." }
}

function Invoke-Node([string[]]$Arguments) {
  & $script:Node '--no-experimental-global-navigator' @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Node.js exited with code $LASTEXITCODE." }
}

try {
  $Python = Find-Python
  Write-Host "Python: $Python"

  $DevRoot = Split-Path -Parent (Split-Path -Parent $KitRoot)
  $DevDeps = Join-Path $DevRoot 'work\pydeps'
  $DevNode = Join-Path $DevDeps 'nodejs_wheel\node.exe'
  $DevGcc = Join-Path $DevRoot 'work\gcc\xpack-arm-none-eabi-gcc-15.2.1-1.1\bin\arm-none-eabi-gcc.exe'
  $DevNwlink = Join-Path $DevRoot 'work\nwlink\node_modules\nwlink'

  $env:PYTHONPATH = $PyDeps
  $HasPillow = $false
  try { Invoke-Python @('-c', "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('PIL') else 1)"); $HasPillow = $true } catch { $HasPillow = $false }
  if (-not $HasPillow -and (Test-Path (Join-Path $DevDeps 'PIL'))) { $env:PYTHONPATH = "$DevDeps;$PyDeps"; $HasPillow = $true }
  if (-not $HasPillow) {
    Write-Host 'Installing Pillow (one time)...'
    Invoke-Python @('-m', 'pip', 'install', '--disable-pip-version-check', '--quiet', '--target', $PyDeps, 'Pillow==13.0.0')
  }

  $Node = Join-Path $PyDeps 'nodejs_wheel\node.exe'
  $Npm = Join-Path $PyDeps 'nodejs_wheel\lib\node_modules\npm\bin\npm-cli.js'
  if (-not (Test-Path $Node)) { $Node = Join-Path $Tools 'node\node.exe'; $Npm = Join-Path $Tools 'node\node_modules\npm\bin\npm-cli.js' }
  if ((-not (Test-Path $Node) -or -not (Test-Path $Npm)) -and (Test-Path $DevNode)) { $Node = $DevNode; $Npm = Join-Path $DevDeps 'nodejs_wheel\lib\node_modules\npm\bin\npm-cli.js' }
  if (-not (Test-Path $Node) -or -not (Test-Path $Npm)) {
    Write-Host 'Installing Node.js (one time)...'
    Invoke-Python @('-m', 'pip', 'install', '--disable-pip-version-check', '--quiet', '--target', $PyDeps, 'nodejs-wheel-binaries==22.20.0')
    $Node = Join-Path $PyDeps 'nodejs_wheel\node.exe'
    $Npm = Join-Path $PyDeps 'nodejs_wheel\lib\node_modules\npm\bin\npm-cli.js'
  }
  if (-not (Test-Path $Node) -or -not (Test-Path $Npm)) { throw 'Node.js or npm could not be found after installation.' }

  $Gcc = Join-Path $Tools 'gcc\xpack-arm-none-eabi-gcc-15.2.1-1.1\bin\arm-none-eabi-gcc.exe'
  if (-not (Test-Path $Gcc) -and (Test-Path $DevGcc)) { $Gcc = $DevGcc }
  if (-not (Test-Path $Gcc)) {
    Write-Host 'Downloading the NumWorks ARM compiler (about 300 MB, one time)...'
    $Archive = Join-Path $Tools 'arm-gcc.zip'
    $Url = 'https://github.com/xpack-dev-tools/arm-none-eabi-gcc-xpack/releases/download/v15.2.1-1.1/xpack-arm-none-eabi-gcc-15.2.1-1.1-win32-x64.zip'
    & curl.exe -L --fail --retry 4 --retry-delay 2 -o $Archive $Url
    if ($LASTEXITCODE -ne 0) { throw 'The ARM compiler download failed.' }
    Expand-Archive -LiteralPath $Archive -DestinationPath (Join-Path $Tools 'gcc') -Force
    Remove-Item -LiteralPath $Archive -Force
    if (-not (Test-Path $Gcc)) { throw 'The ARM compiler could not be found after extraction.' }
  }

  $Nwlink = Join-Path $NwlinkRoot 'node_modules\nwlink'
  if (-not (Test-Path (Join-Path $Nwlink 'dist\eadk\eadk.h')) -and (Test-Path (Join-Path $DevNwlink 'dist\eadk\eadk.h'))) { $Nwlink = $DevNwlink }
  if (-not (Test-Path (Join-Path $Nwlink 'dist\eadk\eadk.h'))) {
    Write-Host 'Installing the NumWorks tools (one time)...'
    $null = New-Item -ItemType Directory -Force -Path $NwlinkRoot
    $env:Path = "$(Split-Path -Parent $Node);$env:Path"
    Invoke-Node @($Npm, 'install', '--prefix', $NwlinkRoot, '--ignore-scripts', '--no-audit', '--no-fund', 'nwlink@0.0.16')
    $Nwlink = Join-Path $NwlinkRoot 'node_modules\nwlink'
  }

  if (-not $ImagesFolder) {
    Add-Type -AssemblyName System.Windows.Forms
    $Picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $Picker.Description = 'Choose the folder containing the images for the app.'
    $Picker.ShowNewFolderButton = $false
    if ($Picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { Write-Host 'No folder selected.'; exit 0 }
    $ImagesFolder = $Picker.SelectedPath
  }
  if (-not (Test-Path -LiteralPath $ImagesFolder -PathType Container)) { throw "Image folder not found: $ImagesFolder" }

  Write-Host "Preparing images from: $ImagesFolder"
  Invoke-Python @((Join-Path $KitRoot 'prepare_images.py'), '--images', $ImagesFolder, '--output', $Generated, '--icon', (Join-Path $KitRoot 'assets\icon.png'))

  $NwlinkCli = Join-Path $Nwlink 'bin\nwlink'
  Invoke-Node @($NwlinkCli, 'png-icon-o', (Join-Path $Generated 'icon.png'), (Join-Path $Generated 'icon.o'))

  $Header = Join-Path $Nwlink 'dist\eadk'
  $Shim = Join-Path $KitRoot 'include'
  Push-Location $Generated
  try {
    & $Gcc -std=c99 -Os -Wall -mthumb -mfloat-abi=hard -mcpu=cortex-m7 -mfpu=fpv5-sp-d16 "-I$Shim" "-I$Header" -ffunction-sections -fdata-sections -c main.c -o main.o
    if ($LASTEXITCODE -ne 0) { throw 'App compilation failed.' }
    & $Gcc -mthumb -mfloat-abi=hard -mcpu=cortex-m7 -mfpu=fpv5-sp-d16 -c image_data.S -o image_data.o
    if ($LASTEXITCODE -ne 0) { throw 'Image data compilation failed.' }
    & $Gcc -mthumb -mfloat-abi=hard -mcpu=cortex-m7 -mfpu=fpv5-sp-d16 '-Wl,--relocatable' -nostdlib '-Wl,-e,main' '-Wl,-u,eadk_app_name' '-Wl,-u,eadk_app_icon' '-Wl,-u,eadk_api_level' '-Wl,--gc-sections' main.o image_data.o icon.o -o Gallery.nwa
    if ($LASTEXITCODE -ne 0) { throw 'NWA file creation failed.' }
  } finally { Pop-Location }

  Invoke-Node @($NwlinkCli, 'nwa-name', (Join-Path $Generated 'Gallery.nwa'))
  Write-Host ''
  Write-Host "Nezu Photo Viewer is ready: $(Join-Path $Generated 'Gallery.nwa')" -ForegroundColor Green
  Write-Host 'Gallery opens in the photo grid. Use arrows to navigate, OK to open, and EXE or Back to return.'
  Start-Process explorer.exe -ArgumentList ('/select,"' + (Join-Path $Generated 'Gallery.nwa') + '"')
} catch {
  Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
}
