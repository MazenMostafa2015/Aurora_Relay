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

$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if ($null -eq $signtool) {
    throw 'signtool.exe was not found. Use a Windows runner with the Windows SDK installed.'
}
if ([string]::IsNullOrWhiteSpace($TimestampUrl)) {
    throw 'A trusted timestamp URL is required.'
}

$certificatePath = Join-Path $env:RUNNER_TEMP 'aurora-relay-signing.pfx'
try {
    [IO.File]::WriteAllBytes($certificatePath, [Convert]::FromBase64String($PfxBase64))
    $installers = Get-ChildItem -Path $ReleaseDirectory -Filter '*.exe' -File
    if ($installers.Count -eq 0) {
        throw "No Windows installer executables found in $ReleaseDirectory"
    }

    foreach ($installer in $installers) {
        Write-Host "Signing $($installer.Name)"
        & $signtool.Source sign /fd SHA256 /f $certificatePath /p $PfxPassword /tr $TimestampUrl /td SHA256 $installer.FullName
        if ($LASTEXITCODE -ne 0) {
            throw "signtool failed for $($installer.Name) with exit code $LASTEXITCODE"
        }

        & $signtool.Source verify /pa /all $installer.FullName
        if ($LASTEXITCODE -ne 0) {
            throw "Signature verification failed for $($installer.Name)"
        }
    }
}
finally {
    if (Test-Path $certificatePath) {
        Remove-Item -Force $certificatePath
    }
}
