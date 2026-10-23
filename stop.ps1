$ErrorActionPreference = 'Stop'
$serverPath = Join-Path $PSScriptRoot 'server.py'
$ownedProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -and $_.CommandLine.Contains('"' + $serverPath + '"')
}
foreach ($ownedProcess in $ownedProcesses) {
    Stop-Process -Id $ownedProcess.ProcessId -ErrorAction SilentlyContinue
}
Write-Host 'Afterglow stopped for this folder. Your records are preserved.'
