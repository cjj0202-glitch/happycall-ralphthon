[CmdletBinding(SupportsShouldProcess)]
param([switch]$InstallTools, [switch]$InstallAgentCli, [switch]$InstallVercel)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
# No login, token copy, background watcher, or deployment in this script.
if ($InstallTools) {
    $packages = @{
        git = 'Git.Git'
        gh = 'GitHub.cli'
        node = 'OpenJS.NodeJS.LTS'
        python = 'Python.Python.3.12'
    }
    foreach ($tool in $packages.Keys) {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
            if ($PSCmdlet.ShouldProcess($packages[$tool], 'Install missing tool with winget')) {
                & winget install --id $packages[$tool] --exact --accept-source-agreements --accept-package-agreements
                if ($LASTEXITCODE -ne 0) { throw "winget failed: $tool" }
            }
        }
    }
    Write-Host 'After new installations, reopen PowerShell to refresh PATH.'
}
if ($InstallAgentCli -and $PSCmdlet.ShouldProcess('@openai/codex', 'Install CLI')) {
    & npm install -g @openai/codex
    if ($LASTEXITCODE -ne 0) { throw 'Codex CLI installation failed' }
}
if ($InstallVercel -and $PSCmdlet.ShouldProcess('vercel', 'Install CLI')) {
    & npm install -g vercel
    if ($LASTEXITCODE -ne 0) { throw 'Vercel CLI installation failed' }
}
if (-not $WhatIfPreference) {
    & python -X utf8 (Join-Path $taskRoot 'scripts/preflight.py')
    exit $LASTEXITCODE
}
