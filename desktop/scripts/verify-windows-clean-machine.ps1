param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$InstallerPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedSha256,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{40}$')]
    [string]$ExpectedSignerThumbprint,

    [Parameter(Mandatory = $true)]
    [string]$EvidencePath,

    [ValidateRange(30, 180)]
    [int]$StartupTimeoutSeconds = 90
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$expectedHash = $ExpectedSha256.ToLowerInvariant()
$expectedSigner = ($ExpectedSignerThumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
$installDirectory = Join-Path $env:LOCALAPPDATA 'Programs\Aurora Relay'
$applicationPath = Join-Path $installDirectory 'Aurora Relay.exe'
$uninstallerPath = Join-Path $installDirectory 'Uninstall Aurora Relay.exe'
# Electron derives the production userData folder from desktop/electron/package.json name.
$userDataPath = Join-Path $env:APPDATA 'aurora-relay-desktop'
$backendStartupLogPath = Join-Path $userDataPath 'logs\backend-startup.log'
$diagnosticLogPath = Join-Path (Split-Path -Parent $EvidencePath) 'clean-machine-backend.log'
$installer = Get-Item -LiteralPath $InstallerPath
$launchedApplication = $null
$installationStarted = $false
$uninstallCompleted = $false

$evidence = [ordered]@{
    schema = 'aurora-relay-clean-machine-evidence/v1'
    started_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    status = 'running'
    installer = [ordered]@{
        name = $installer.Name
        sha256 = $null
        signature_status = $null
        signer_thumbprint = $null
        timestamp_certificate_present = $false
    }
    install = [ordered]@{
        directory = $installDirectory
        silent_exit_code = $null
        application_present = $false
    }
    runtime = [ordered]@{
        user_data_directory = $userDataPath
        application_process_id = $null
        backend_process_id = $null
        loopback_address = $null
        loopback_port = $null
        health_status_code = $null
        backend_startup_log_captured = $false
    }
    uninstall = [ordered]@{
        exit_code = $null
        application_removed = $false
        retained_user_state = $false
    }
    error = $null
}

function Stop-AuroraRelayProcesses {
    foreach ($processName in @('Aurora Relay', 'aurora-backend')) {
        $processes = @(Get-Process -Name $processName -ErrorAction SilentlyContinue)
        foreach ($process in $processes) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

function Write-Evidence {
    $directory = Split-Path -Parent $EvidencePath
    if (-not [string]::IsNullOrWhiteSpace($directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $evidence['completed_at_utc'] = (Get-Date).ToUniversalTime().ToString('o')
    $evidence | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath $EvidencePath -Encoding utf8
}

function Wait-ForLoopbackHealth {
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $backends = @(Get-Process -Name 'aurora-backend' -ErrorAction SilentlyContinue)
        foreach ($backend in $backends) {
            $listeners = @(Get-NetTCPConnection -OwningProcess $backend.Id -State Listen -ErrorAction SilentlyContinue |
                Where-Object { $_.LocalAddress -in @('127.0.0.1', '::1') })
            foreach ($listener in $listeners) {
                try {
                    $response = Invoke-WebRequest -Uri "http://127.0.0.1:$($listener.LocalPort)/health" -TimeoutSec 5
                    if ($response.StatusCode -eq 200) {
                        return [pscustomobject]@{
                            BackendProcessId = $backend.Id
                            Address = $listener.LocalAddress
                            Port = $listener.LocalPort
                            HealthStatusCode = $response.StatusCode
                        }
                    }
                }
                catch {
                    # The backend can bind before its health route is ready; keep polling within the bounded window.
                }
            }
        }
        Start-Sleep -Seconds 1
    }
    throw "Aurora Relay did not expose a healthy loopback backend within $StartupTimeoutSeconds seconds."
}

try {
    if (Test-Path -LiteralPath $installDirectory) {
        throw "The clean runner already contains an Aurora Relay installation at $installDirectory."
    }

    $actualHash = (Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $evidence.installer.sha256 = $actualHash
    if ($actualHash -ne $expectedHash) {
        throw "Installer SHA-256 mismatch. Expected $expectedHash but found $actualHash."
    }

    $signature = Get-AuthenticodeSignature -FilePath $installer.FullName
    $evidence.installer.signature_status = [string]$signature.Status
    if ($null -eq $signature.SignerCertificate) {
        throw 'The installer does not expose an Authenticode signer certificate.'
    }
    $actualSigner = ($signature.SignerCertificate.Thumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
    $evidence.installer.signer_thumbprint = $actualSigner
    $evidence.installer.timestamp_certificate_present = $null -ne $signature.TimeStamperCertificate
    if ($actualSigner -ne $expectedSigner) {
        throw "Installer signer thumbprint mismatch. Expected $expectedSigner but found $actualSigner."
    }
    if ([string]$signature.Status -notin @('Valid', 'NotTrusted', 'UnknownError')) {
        throw "Installer Authenticode integrity validation failed: $($signature.Status)"
    }

    $certificateChain = [System.Security.Cryptography.X509Certificates.X509Chain]::new()
    try {
        $certificateChain.ChainPolicy.TrustMode = [System.Security.Cryptography.X509Certificates.X509ChainTrustMode]::CustomRootTrust
        $certificateChain.ChainPolicy.CustomTrustStore.Add($signature.SignerCertificate)
        $certificateChain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
        $certificateChain.ChainPolicy.UrlRetrievalTimeout = [TimeSpan]::FromSeconds(2)
        if (-not $certificateChain.Build($signature.SignerCertificate)) {
            $chainStatus = ($certificateChain.ChainStatus | ForEach-Object { $_.Status.ToString() }) -join ', '
            throw "Pinned installer signer chain validation failed: $chainStatus"
        }
    }
    finally {
        $certificateChain.Dispose()
    }

    $installationStarted = $true
    $installerProcess = Start-Process -FilePath $installer.FullName -ArgumentList '/S' -Wait -PassThru
    $evidence.install.silent_exit_code = $installerProcess.ExitCode
    if ($installerProcess.ExitCode -ne 0) {
        throw "Silent installer exited with code $($installerProcess.ExitCode)."
    }
    if (-not (Test-Path -LiteralPath $applicationPath -PathType Leaf)) {
        throw "The installed application was not found at $applicationPath."
    }
    $evidence.install.application_present = $true

    $launchedApplication = Start-Process -FilePath $applicationPath -PassThru
    $evidence.runtime.application_process_id = $launchedApplication.Id
    $runtime = Wait-ForLoopbackHealth
    $evidence.runtime.backend_process_id = $runtime.BackendProcessId
    $evidence.runtime.loopback_address = $runtime.Address
    $evidence.runtime.loopback_port = $runtime.Port
    $evidence.runtime.health_status_code = $runtime.HealthStatusCode

    Stop-AuroraRelayProcesses
    Start-Sleep -Seconds 2
    if (-not (Test-Path -LiteralPath $uninstallerPath -PathType Leaf)) {
        throw "The installed uninstaller was not found at $uninstallerPath."
    }
    $uninstallerProcess = Start-Process -FilePath $uninstallerPath -ArgumentList '/S' -Wait -PassThru
    $evidence.uninstall.exit_code = $uninstallerProcess.ExitCode
    if ($uninstallerProcess.ExitCode -ne 0) {
        throw "Silent uninstaller exited with code $($uninstallerProcess.ExitCode)."
    }
    $uninstallCompleted = $true
    $evidence.uninstall.application_removed = -not (Test-Path -LiteralPath $applicationPath -PathType Leaf)
    if (-not $evidence.uninstall.application_removed) {
        throw 'The application executable remained after silent uninstall.'
    }
    $evidence.uninstall.retained_user_state = Test-Path -LiteralPath $userDataPath -PathType Container
    if (-not $evidence.uninstall.retained_user_state) {
        throw "Expected retained per-user application state at $userDataPath after uninstall."
    }

    $evidence.status = 'passed'
}
catch {
    $evidence.status = 'failed'
    $evidence.error = $_.Exception.Message
    throw
}
finally {
    Stop-AuroraRelayProcesses
    if ($evidence.status -eq 'failed' -and (Test-Path -LiteralPath $backendStartupLogPath -PathType Leaf)) {
        try {
            Copy-Item -LiteralPath $backendStartupLogPath -Destination $diagnosticLogPath -Force
            $evidence.runtime.backend_startup_log_captured = $true
        }
        catch {
            # Preserve the primary verification error even if diagnostic export is unavailable.
        }
    }
    if ($installationStarted -and -not $uninstallCompleted -and (Test-Path -LiteralPath $uninstallerPath -PathType Leaf)) {
        try {
            Start-Process -FilePath $uninstallerPath -ArgumentList '/S' -Wait | Out-Null
        }
        catch {
            # Preserve the original verification error while making a best-effort cleanup attempt.
        }
    }
    Write-Evidence
}
