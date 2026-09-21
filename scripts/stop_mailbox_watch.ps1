[CmdletBinding()]
param([string]$PythonPath = 'python')
# Optional wrapper; the Python launcher verifies PID/command/creation time.
$ErrorActionPreference = 'Stop'
& $PythonPath (Join-Path $PSScriptRoot 'mailbox_watch.py') stop
exit $LASTEXITCODE
