# Phase 5 Sandbox Security Research Notes

The implementation follows Docker and OWASP guidance that favors rootless operation where available, non-root containers, dropped Linux capabilities, no-new-privileges, read-only root filesystems, default seccomp filtering, explicit resource limits, and network isolation by default.

## Sources

1. Docker, **Rootless mode**: https://docs.docker.com/engine/security/rootless/
2. OWASP, **Docker Security Cheat Sheet**: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
3. OWASP, **Docker Top 10**: https://owasp.org/www-project-docker-top-10/
4. Wong et al., **Threat modeling and security analysis of containers: A survey**: https://arxiv.org/abs/2111.11475
5. Checkmarx, **The Glass Sandbox: The Complexity of Python Sandboxing**: https://checkmarx.com/zero-post/glass-sandbox-complexity-of-python-sandboxing/

## Design implications

Python language-level restrictions are not treated as a security boundary. Arbitrary code is isolated by the container boundary, kernel-enforced resource controls, disabled networking, non-root execution in the images, and a read-only root filesystem with a narrow writable workspace and temporary filesystem. Docker socket mounts, privileged mode, host networking, host PID/IPC/UTS namespaces, and additional capabilities are not exposed by the default configuration.
