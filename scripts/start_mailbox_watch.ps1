[CmdletBinding()]
param(
    [ValidateSet('Background', 'Foreground', 'Once', 'Check')]
    [string]$Mode = 'Background',
    [ValidateRange(1, 86400)][int]$IntervalSeconds = 30,
    [string]$PythonPath = 'python'
)
# Optional wrapper; the Python launcher is the primary path.
$ErrorActionPreference = 'Stop'
$action = @{ Background = 'start'; Foreground = 'foreground'; Once = 'once'; Check = 'check' }[$Mode]
& $PythonPath (Join-Path $PSScriptRoot 'mailbox_watch.py') $action --interval $IntervalSeconds
exit $LASTEXITCODE
