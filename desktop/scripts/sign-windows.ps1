[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path $_ -PathType Container })]
    [string]$ReleaseDirectory,

    [Parameter(Mandatory = $true)]
    [string]$PfxBase64,

    [Parameter(Mandatory = $true)]
    [string]$PfxPassword,

    [Parameter(Mandatory = $true)]
    [string]$TimestampUrl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$signtoolPath = if (-not [string]::IsNullOrWhiteSpace($env:AURORA_SIGNTOOL_PATH) -and (Test-Path $env:AURORA_SIGNTOOL_PATH -PathType Leaf)) {
    (Get-Item $env:AURORA_SIGNTOOL_PATH).FullName
}
else {
    (Get-Command signtool.exe -ErrorAction SilentlyContinue).Source
}
if ([string]::IsNullOrWhiteSpace($signtoolPath)) {
    throw 'signtool.exe was not found. Use a Windows runner with the Windows SDK installed.'
}
if ([string]::IsNullOrWhiteSpace($TimestampUrl)) {
    throw 'A trusted timestamp URL is required.'
}
$internalCertificateThumbprint = ($env:AURORA_INTERNAL_SIGNING_CERT_SHA1 -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
if (-not [string]::IsNullOrWhiteSpace($env:AURORA_INTERNAL_SIGNING_CERT_SHA1) -and $internalCertificateThumbprint.Length -ne 40) {
    throw 'AURORA_INTERNAL_SIGNING_CERT_SHA1 must contain a 40-character SHA-1 certificate thumbprint.'
}

$certificatePath = Join-Path $env:RUNNER_TEMP 'aurora-relay-signing.pfx'
try {
    [IO.File]::WriteAllBytes($certificatePath, [Convert]::FromBase64String($PfxBase64))
    $installers = @(Get-ChildItem -Path $ReleaseDirectory -Filter '*.exe' -File)
    if ($installers.Count -eq 0) {
        throw "No Windows installer executables found in $ReleaseDirectory"
    }

    foreach ($installer in $installers) {
        Write-Host "Signing $($installer.Name)"
        & $signtoolPath sign /fd SHA256 /f $certificatePath /p $PfxPassword /tr $TimestampUrl /td SHA256 $installer.FullName
        if ($LASTEXITCODE -ne 0) {
            throw "signtool failed for $($installer.Name) with exit code $LASTEXITCODE"
        }

        if ([string]::IsNullOrWhiteSpace($internalCertificateThumbprint)) {
            & $signtoolPath verify /pa /all $installer.FullName
            if ($LASTEXITCODE -ne 0) {
                throw "Signature verification failed for $($installer.Name)"
            }
        }
        else {
            $signature = Get-AuthenticodeSignature -FilePath $installer.FullName
            $actualThumbprint = ($signature.SignerCertificate.Thumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
            if ($actualThumbprint -ne $internalCertificateThumbprint) {
                throw "Internal signing certificate mismatch for $($installer.Name)"
            }
            if ([string]$signature.Status -notin @('Valid', 'NotTrusted')) {
                throw "Internal signature verification failed for $($installer.Name): $($signature.Status)"
            }
            Write-Warning "Verified internal self-signed signature for $($installer.Name). TrustedPublisher and Root installation is required on recipient devices."
        }
    }
}
finally {
    if (Test-Path $certificatePath) {
        Remove-Item -Force $certificatePath
    }
}
