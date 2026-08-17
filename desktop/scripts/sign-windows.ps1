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
$temporaryTrustStores = @()
$temporaryTrustEntries = @()
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
            foreach ($storeName in @('Root', 'TrustedPublisher')) {
                $trustStore = [System.Security.Cryptography.X509Certificates.X509Store]::new($storeName, 'CurrentUser')
                $trustStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
                $temporaryTrustStores += $trustStore
                $existingTrust = @($trustStore.Certificates | Where-Object {
                    (($_.Thumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()) -eq $internalCertificateThumbprint
                })
                if ($existingTrust.Count -eq 0) {
                    $trustStore.Add($signature.SignerCertificate)
                    $temporaryTrustEntries += [pscustomobject]@{
                        Store = $trustStore
                        Thumbprint = $internalCertificateThumbprint
                    }
                }
            }
            $trustedSignature = Get-AuthenticodeSignature -FilePath $installer.FullName
            if ([string]$trustedSignature.Status -ne 'Valid') {
                throw "Internal signature verification failed for $($installer.Name) after temporary trust: $($trustedSignature.Status)"
            }
            Write-Warning "Verified internal self-signed signature for $($installer.Name) against the pinned certificate. Recipient devices still require the documented Root and TrustedPublisher trust installation."
        }
    }
}
finally {
    foreach ($entry in $temporaryTrustEntries) {
        $certificatesToRemove = @($entry.Store.Certificates | Where-Object {
            (($_.Thumbprint -replace '[^0-9A-Fa-f]', '').ToUpperInvariant()) -eq $entry.Thumbprint
        })
        foreach ($certificateToRemove in $certificatesToRemove) {
            $entry.Store.Remove($certificateToRemove)
        }
    }
    foreach ($trustStore in $temporaryTrustStores) {
        $trustStore.Close()
    }
    if (Test-Path $certificatePath) {
        Remove-Item -Force $certificatePath
    }
}
