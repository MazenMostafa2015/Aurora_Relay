# Aurora Relay internal code-signing trust guide

## Scope

This document applies only to the internally issued, self-signed Aurora Relay code-signing certificate. It permits controlled internal testing after a device administrator has reviewed the certificate fingerprint. It does **not** make Aurora Relay suitable for public download or remove Windows reputation warnings. For public distribution, replace this identity with a certificate from a trusted code-signing authority or an approved managed signing service. [1]

## Public certificate verification

Use only `docs/certificates/AuroraRelay-Internal-CodeSigning.cer` from the reviewed release source. Its SHA-256 file hash is:

```text
380A07432E7647050F606D5FF33A09A05E03EEA221BCC9C80FDA5A0A5F149577
```

The certificate SHA-256 fingerprint is:

```text
38:0A:07:43:2E:76:47:05:0F:60:6D:5F:F3:3A:09:A0:5E:03:EE:A2:21:BC:C9:C8:0F:DA:5A:0A:5F:14:95:77
```

Verify the downloaded public certificate before trusting it:

```powershell
Get-FileHash .\AuroraRelay-Internal-CodeSigning.cer -Algorithm SHA256
```

## Current-user trust installation

Run PowerShell as the intended Aurora Relay user. This deliberately limits trust to that user profile.

```powershell
$certificate = Resolve-Path .\AuroraRelay-Internal-CodeSigning.cer
Import-Certificate -FilePath $certificate -CertStoreLocation Cert:\CurrentUser\Root
Import-Certificate -FilePath $certificate -CertStoreLocation Cert:\CurrentUser\TrustedPublisher
```

The first import establishes the self-signed certificate as a trusted root for that user. The second identifies it as an explicitly trusted publisher. Both are required for predictable internal Authenticode behavior. `Import-Certificate` supports adding certificates to certificate stores from a public certificate file. [2]

## Managed-device installation and removal

For enterprise devices, deploy the certificate only through an approved endpoint-management policy to `LocalMachine\Root` and `LocalMachine\TrustedPublisher`; this requires administrator authorization. Do not distribute the PFX, private key, or signing password to endpoints.

To remove current-user trust when internal testing is complete, identify the certificate by its SHA-1 thumbprint in the appropriate certificate stores and remove only that reviewed certificate:

```powershell
$thumbprint = '34E83CA90590FE37D4F323534BFC64F50066DED1'
Remove-Item "Cert:\CurrentUser\Root\$thumbprint" -ErrorAction SilentlyContinue
Remove-Item "Cert:\CurrentUser\TrustedPublisher\$thumbprint" -ErrorAction SilentlyContinue
```

## Release verification

Before internal deployment, verify both the installer hash from `SHA256SUMS` and the Authenticode signature. For a self-signed identity, review the signer certificate thumbprint against the value above after trust has been installed.

```powershell
Get-FileHash .\Aurora-Relay-<version>-win-x64.exe -Algorithm SHA256
Get-AuthenticodeSignature .\Aurora-Relay-<version>-win-x64.exe | Format-List Status,StatusMessage,SignerCertificate
```

## References

[1]: https://learn.microsoft.com/en-us/windows/security/application-security/application-control/windows-defender-application-control/design/trusted-signing "Microsoft trusted signing documentation"
[2]: https://learn.microsoft.com/en-us/powershell/module/pki/import-certificate?view=windowsserver2025-ps "Microsoft Import-Certificate documentation"
