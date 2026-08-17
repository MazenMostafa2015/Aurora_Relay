[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$InstallerPath,

    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Leaf })]
    [string]$ChecksumFile,

    [string]$ReportPath = (Join-Path ([IO.Path]::GetTempPath()) 'aurora-relay-clean-machine-report.json'),

    [ValidateRange(10, 120)]
    [int]$StartupTimeoutSeconds = 35,

    [switch]$RequireMissingOptionalRuntimes,

    [switch]$PurgeTestState
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$checks = [System.Collections.Generic.List[object]]::new()
$startedAt = (Get-Date).ToUniversalTime().ToString('o')
$appProcess = $null
$backendProcessIds = @()
$installRoot = $null
$statePath = Join-Path $env:APPDATA 'AuroraRelay'

function Add-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][bool]$Passed,
        [Parameter(Mandatory = $true)][string]$Detail
    )

    $checks.Add([pscustomobject]@{
        name = $Name
        passed = $Passed
        detail = $Detail
        recorded_at = (Get-Date).ToUniversalTime().ToString('o')
    })
    if (-not $Passed) { throw "$Name failed: $Detail" }
}

function Write-Report {
    param([string]$Status, [string]$Failure = '')

    $report = [pscustomobject]@{
        product = 'Aurora Relay'
        status = $Status
        started_at = $startedAt
        completed_at = (Get-Date).ToUniversalTime().ToString('o')
        installer = (Resolve-Path $InstallerPath).Path
        checksum_file = (Resolve-Path $ChecksumFile).Path
        retained_state_path = $statePath
        optional_runtime_profile = [pscustomobject]@{
            docker = [bool](Get-Command docker -ErrorAction SilentlyContinue)
            ollama = [bool](Get-Command ollama -ErrorAction SilentlyContinue)
        }
        checks = $checks
        failure = $Failure
    }
    $parent = Split-Path -Parent $ReportPath
    if (-not [string]::IsNullOrWhiteSpace($parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $report | ConvertTo-Json -Depth 6 | Set-Content -Path $ReportPath -Encoding utf8
}

function Get-InstallerChecksum {
    $installerName = [IO.Path]::GetFileName($InstallerPath)
    foreach ($line in Get-Content -Path $ChecksumFile) {
        $parts = $line -split '\s+', 2
        if ($parts.Count -ne 2) { continue }
        $recordedName = $parts[1].Trim().TrimStart('*').Replace('/', '\')
        if ([IO.Path]::GetFileName($recordedName) -eq $installerName) { return $parts[0].ToLowerInvariant() }
    }
    return $null
}

function Get-InstalledApplication {
    $roots = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Aurora Relay'),
        (Join-Path $env:ProgramFiles 'Aurora Relay')
    )
    if (${env:ProgramFiles(x86)}) { $roots += (Join-Path ${env:ProgramFiles(x86)} 'Aurora Relay') }
    foreach ($root in $roots) {
        if (-not (Test-Path $root -PathType Container)) { continue }
        $candidate = Get-ChildItem -Path $root -Filter 'Aurora Relay.exe' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $candidate) { return $candidate }
    }
    return $null
}

function Get-AuroraBackendProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -ieq 'aurora-backend.exe' -or $_.CommandLine -match 'aurora-backend'
    }
}

try {
    $signature = Get-AuthenticodeSignature -FilePath $InstallerPath
    Add-Check -Name 'installer_authenticode' -Passed ($signature.Status -eq 'Valid') -Detail "Authenticode status: $($signature.Status) $($signature.StatusMessage)"
    Add-Check -Name 'installer_timestamp' -Passed ($null -ne $signature.TimeStamperCertificate) -Detail 'Installer contains a trusted timestamp certificate.'

    $expectedChecksum = Get-InstallerChecksum
    $actualChecksum = (Get-FileHash -Path $InstallerPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Add-Check -Name 'installer_checksum' -Passed ($null -ne $expectedChecksum -and $expectedChecksum -eq $actualChecksum) -Detail "Expected SHA-256: $expectedChecksum; actual SHA-256: $actualChecksum"

    $runtimeDetail = "Docker present: $([bool](Get-Command docker -ErrorAction SilentlyContinue)); Ollama present: $([bool](Get-Command ollama -ErrorAction SilentlyContinue))"
    $runtimesAbsent = -not (Get-Command docker -ErrorAction SilentlyContinue) -and -not (Get-Command ollama -ErrorAction SilentlyContinue)
    if ($RequireMissingOptionalRuntimes) {
        Add-Check -Name 'optional_runtime_profile' -Passed $runtimesAbsent -Detail $runtimeDetail
    } else {
        $checks.Add([pscustomobject]@{ name = 'optional_runtime_profile'; passed = $true; detail = $runtimeDetail; recorded_at = (Get-Date).ToUniversalTime().ToString('o') })
    }

    $install = Start-Process -FilePath $InstallerPath -ArgumentList '/S' -Wait -PassThru
    Add-Check -Name 'silent_install' -Passed ($install.ExitCode -eq 0) -Detail "Installer exit code: $($install.ExitCode)"

    $application = Get-InstalledApplication
    Add-Check -Name 'application_installed' -Passed ($null -ne $application) -Detail 'Aurora Relay executable was discovered in a supported per-user or machine install location.'
    $installRoot = Split-Path -Parent $application.FullName

    $appProcess = Start-Process -FilePath $application.FullName -PassThru
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $listeningConnections = @()
    while ((Get-Date) -lt $deadline) {
        $backendProcesses = @(Get-AuroraBackendProcesses)
        $backendProcessIds = @($backendProcesses | ForEach-Object { $_.ProcessId })
        if ($backendProcessIds.Count -gt 0) {
            $listeningConnections = @(Get-NetTCPConnection -OwningProcess $backendProcessIds -State Listen -ErrorAction SilentlyContinue)
            if ($listeningConnections.Count -gt 0) { break }
        }
        Start-Sleep -Seconds 1
    }

    Add-Check -Name 'backend_started' -Passed ($backendProcessIds.Count -gt 0) -Detail "Detected Aurora backend process IDs: $($backendProcessIds -join ', ')"
    $listenerDetail = ($listeningConnections | ForEach-Object { '{0}:{1}' -f $_.LocalAddress, $_.LocalPort }) -join ', '
    Add-Check -Name 'loopback_listener' -Passed ($listeningConnections.Count -gt 0 -and @($listeningConnections | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') }).Count -eq 0) -Detail "Listening addresses: $listenerDetail"
    Add-Check -Name 'retained_state_created' -Passed (Test-Path $statePath -PathType Container) -Detail "Expected per-user state location: $statePath"

    if ($null -ne $appProcess -and -not $appProcess.HasExited) { Stop-Process -Id $appProcess.Id -Force }
    foreach ($backendProcessId in $backendProcessIds) {
        $process = Get-Process -Id $backendProcessId -ErrorAction SilentlyContinue
        if ($null -ne $process) { Stop-Process -Id $backendProcessId -Force }
    }
    Start-Sleep -Seconds 2
    $remainingBackends = @(Get-AuroraBackendProcesses)
    Add-Check -Name 'backend_shutdown' -Passed ($remainingBackends.Count -eq 0) -Detail 'Aurora backend process exited after application shutdown.'

    $uninstaller = Get-ChildItem -Path $installRoot -Filter 'Uninstall*.exe' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    Add-Check -Name 'uninstaller_present' -Passed ($null -ne $uninstaller) -Detail 'NSIS uninstaller executable was found in the installed application directory.'
    $uninstall = Start-Process -FilePath $uninstaller.FullName -ArgumentList '/S' -Wait -PassThru
    Add-Check -Name 'silent_uninstall' -Passed ($uninstall.ExitCode -eq 0) -Detail "Uninstaller exit code: $($uninstall.ExitCode)"
    Add-Check -Name 'application_removed' -Passed (-not (Test-Path $installRoot)) -Detail "Installation directory removed: $installRoot"
    Add-Check -Name 'retained_state_preserved' -Passed (Test-Path $statePath -PathType Container) -Detail "Per-user state persists after uninstall: $statePath"

    Write-Report -Status 'passed'
    Write-Host "Clean-machine verification passed. Report: $ReportPath"
}
catch {
    Write-Report -Status 'failed' -Failure $_.Exception.Message
    throw
}
finally {
    if ($PurgeTestState -and (Test-Path $statePath -PathType Container)) {
        Remove-Item -Path $statePath -Recurse -Force
    }
}
