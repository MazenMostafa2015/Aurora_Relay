[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$AppInstaller,

    [switch]$InstallOllama,
    [switch]$InstallDocker,
    [switch]$SkipPrerequisites
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host "[Aurora Relay] $Message" -ForegroundColor Cyan
}

function Test-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-WingetPackage([string]$Id, [string]$DisplayName) {
    if (-not (Test-Command 'winget')) {
        throw "Microsoft App Installer (winget) is required to install $DisplayName automatically. Install it from Microsoft Store or choose SkipPrerequisites and install $DisplayName manually."
    }

    Write-Step "Installing or verifying $DisplayName ($Id) with winget."
    if ($PSCmdlet.ShouldProcess($DisplayName, "Install or upgrade $Id")) {
        & winget install --id $Id --exact --source winget --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "winget failed for $DisplayName with exit code $LASTEXITCODE."
        }
    }
}

try {
    if (-not (Test-Path $AppInstaller -PathType Leaf)) {
        throw "Aurora Relay installer was not found: $AppInstaller"
    }

    if (-not $SkipPrerequisites) {
        if ($InstallOllama) {
            Install-WingetPackage -Id 'Ollama.Ollama' -DisplayName 'Ollama'
        }
        if ($InstallDocker) {
            Install-WingetPackage -Id 'Docker.DockerDesktop' -DisplayName 'Docker Desktop'
        }
    }

    Write-Step 'Launching the Aurora Relay installer.'
    if ($PSCmdlet.ShouldProcess('Aurora Relay', 'Run the application installer')) {
        $process = Start-Process -FilePath $AppInstaller -Wait -PassThru
        exit $process.ExitCode
    }
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
