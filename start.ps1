param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$portablePython = Join-Path $PSScriptRoot 'runtime\python.exe'
if (Test-Path -LiteralPath $portablePython) {
    $runtime = $portablePython
} elseif (Test-Path -LiteralPath $bundledPython) {
    $runtime = $bundledPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $runtime = 'py'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $runtime = 'python'
} else {
    Write-Host 'Please install Python 3.10+ from python.org, then try again.'
    Read-Host 'Press Enter to exit'
    exit 1
}
Write-Host 'Afterglow - Personal media library'
$appPort = if ($env:PORT) { [int]$env:PORT } else { 8765 }
if ($appPort -lt 1 -or $appPort -gt 65535) { throw 'Invalid port.' }
Write-Host "Open http://127.0.0.1:$appPort in your browser."
Write-Host 'On your phone, use the LAN address shown in the app.'
$appUrl = "http://127.0.0.1:$appPort"
function Test-AppReady {
    try {
        $response = Invoke-RestMethod -Uri "$appUrl/api/export" -TimeoutSec 2
        return ($response.app -eq 'afterglow')
    } catch { return $false }
}
if (-not (Test-AppReady)) {
    $serverPath = Join-Path $PSScriptRoot 'server.py'
    $serverProcess = Start-Process -FilePath $runtime -ArgumentList '-X', 'utf8', ('"' + $serverPath + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'server-error.log') -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (Test-AppReady) { $ready = $true; break }
        if ($serverProcess.HasExited) { break }
        Start-Sleep -Milliseconds 300
    }
    if (-not $ready) {
        Write-Host 'Startup failed. Details:' -ForegroundColor Red
        Get-Content -LiteralPath (Join-Path $PSScriptRoot 'server-error.log') -Tail 15
        Read-Host 'Press Enter to exit'
        exit 1
    }
}
Write-Host "Ready: $appUrl (running in background)"
if (-not $NoBrowser) { Start-Process $appUrl }
