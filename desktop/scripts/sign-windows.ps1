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
            if ($null -eq $signature.SignerCertificate) {
                throw "Internal signature verification did not return a signer certificate for $($installer.Name)"
            }
            $actualThumbprint = ($signature.SignerCertificate.Thumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()
            if ($actualThumbprint -ne $internalCertificateThumbprint) {
                throw "Internal signing certificate mismatch for $($installer.Name). Expected $internalCertificateThumbprint but the signing PFX produced $actualThumbprint. Update the protected environment pin only after confirming this is the intended internal certificate."
            }
            if ([string]$signature.Status -notin @('Valid', 'NotTrusted', 'UnknownError')) {
                throw "Internal signature integrity validation failed for $($installer.Name): $($signature.Status)"
            }
            $certificateChain = [System.Security.Cryptography.X509Certificates.X509Chain]::new()
            try {
                $certificateChain.ChainPolicy.TrustMode = [System.Security.Cryptography.X509Certificates.X509ChainTrustMode]::CustomRootTrust
                $certificateChain.ChainPolicy.CustomTrustStore.Add($signature.SignerCertificate)
                $certificateChain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
                $certificateChain.ChainPolicy.UrlRetrievalTimeout = [TimeSpan]::FromSeconds(2)
                if (-not $certificateChain.Build($signature.SignerCertificate)) {
                    $chainStatus = ($certificateChain.ChainStatus | ForEach-Object { $_.Status.ToString() }) -join ', '
                    throw "Pinned internal signing certificate chain validation failed for $($installer.Name): $chainStatus"
                }
            }
            finally {
                $certificateChain.Dispose()
            }
            Write-Warning "Verified the pinned internal self-signed signing certificate for $($installer.Name) with bounded in-memory trust. Recipient devices still require the documented Root and TrustedPublisher trust installation."
        }
    }
}
finally {
    if (Test-Path $certificatePath) {
        Remove-Item -Force $certificatePath
    }
}
