# `.SP1` packaging findings

## Verified findings

Microsoft Windows Installer documentation describes standard installation packages and patches, including MSI-based packages and Windows Installer patches. It does not identify `.SP1` as a standard application-installer extension. The `.SP1` extension is historically associated with Windows service-pack or vendor-specific files, so it should not be used as the native Aurora Relay installer format without a specific third-party deployment system that defines it.

Microsoft’s bootstrapper documentation describes the supported pattern for combining prerequisite installation with application deployment: detect prerequisites, present license agreements, install missing prerequisites after consent, and then start the application installer. The bootstrapper uses product and package manifests for redistributable components.

Aurora Relay already uses Electron Builder’s Windows NSIS target. The supported single-file Windows artifact should therefore be a signed NSIS setup executable or a dedicated signed bootstrapper executable that bundles or downloads approved prerequisites, not a renamed `.SP1` file.

## Official references

1. Microsoft Windows Installer portal: https://learn.microsoft.com/en-us/windows/win32/msi/windows-installer-portal
2. Microsoft Create bootstrapper packages: https://learn.microsoft.com/en-us/visualstudio/deployment/creating-bootstrapper-packages?view=visualstudio
3. Electron Builder documentation: https://www.electron.build/docs/configuration
4. Electron Builder repository: https://github.com/electron-userland/electron-builder

## Safety boundary

The deployment package may install the Aurora Relay application and documented prerequisites only after user or administrator consent. Ollama and Docker Desktop should be treated as separately licensed third-party software with official installers, explicit user consent, and clear restart/privilege behavior. Docker must be healthy before code execution is enabled; the application must never fall back to a host shell when Docker is unavailable.
