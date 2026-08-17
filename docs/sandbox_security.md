# Sandboxed Code Execution Security

## Scope and security boundary

Phase 5 executes agent-generated Python, JavaScript, and shell code inside short-lived Docker containers. The container boundary, not a Python language-level restriction, is the primary security boundary. This distinction matters because Python is introspectable and language-level “sandboxes” are not reliable against hostile code [5]. The system is therefore designed for untrusted code, while recognizing that container isolation ultimately depends on the host kernel, Docker daemon, runtime, and image supply chain.

> **Security principle:** Do not expose the Docker socket, host namespaces, privileged mode, or unrestricted mounts to agent-created containers.

## Threat model

The threat model includes malicious or accidentally destructive generated code, fork bombs and process exhaustion, memory and CPU exhaustion, output amplification, filesystem traversal, data exfiltration, package supply-chain attacks, container metadata probing, privilege escalation, and attempts to reach the Docker daemon or host kernel. A compromised sandbox is assumed possible; the goal is to limit its blast radius and make every execution auditable.

| Threat | Primary control | Residual risk |
| --- | --- | --- |
| Host filesystem access | Narrow staged workspace mount; path validation; no arbitrary mounts | Host compromise through runtime/kernel vulnerabilities remains out of scope |
| Privilege escalation | Non-root images, `cap_drop=ALL`, `no-new-privileges`, `privileged=false` | Runtime and kernel vulnerabilities require host patching |
| Network exfiltration | `network_mode=none` by default | An operator may intentionally enable network access; that must be reviewed |
| Resource exhaustion | Memory, CPU, PID, timeout, disk/tmpfs, and output limits | Kernel-level accounting and Docker availability are prerequisites |
| Container escape | Read-only root filesystem, default seccomp, dropped capabilities, no host namespaces | No container is an absolute security boundary |
| Supply-chain abuse | Pinned/approved images and no package installation by default | Images and dependencies still require scanning and provenance |
| Audit evasion | Execution IDs, timestamps, exit status, stderr/stdout, suspicious-command audit records | Logs must be shipped to protected storage in production |

## Implemented controls

The default `SandboxConfig` disables networking, enables a read-only root filesystem, drops all Linux capabilities, enables `no-new-privileges`, limits memory to 512 MiB, limits CPU to one core, caps processes at 128, uses a 100 MiB temporary filesystem, clamps execution time to 120 seconds, and truncates captured output at one MiB. Each run receives a staged workspace under the configured project workspace and is removed during cleanup.

Docker recommends rootless operation to reduce daemon and runtime exposure [1]. The supplied images run as a non-root user, and the deployment should use rootless Docker or an equivalent least-privilege runtime when available. OWASP similarly recommends avoiding privileged containers, reducing capabilities, using read-only filesystems, and protecting the Docker socket [2] [3]. Docker’s default seccomp profile remains enabled because the manager does not request `seccomp=unconfined`.

The default network policy is `none`. `localhost` and internet access are represented in configuration for future controlled deployment, but enabling them requires an explicit security review. The manager never mounts `/var/run/docker.sock`, never requests host networking, never uses host PID/IPC/UTS namespaces, and rejects paths that escape the staged workspace.

## Monitoring and audit

Every execution receives an execution ID and records language, container ID, start and end times, duration, exit code, success, timeout status, output truncation, and monitor metrics. Suspicious command fragments such as Docker socket references, namespace entry, mount, unshare, setns, and ptrace are recorded as security events. Production deployments should forward these records to append-only centralized logging and alert on repeated failures, unexpected image changes, escape indicators, and resource-limit violations.

## Incident response

If an escape indicator or unexpected host behavior is observed, immediately disable the code-executor MCP server, stop and remove all active sandbox containers, preserve the audit records, rotate any credentials that may have been reachable, and isolate the Docker host from sensitive networks. Review the container image digest, runtime version, Docker daemon logs, and host audit logs. Rebuild from approved images, patch the host and runtime, and re-enable the server only after a security review and malicious-code regression suite pass.

## Operational limitations

This system is not a replacement for a dedicated microVM or multi-tenant code-execution service when the threat model includes sophisticated kernel exploitation or mutually distrustful tenants. Internet-enabled execution, arbitrary package installation, host-mounted secrets, and long-lived containers should remain disabled in production unless separately designed and reviewed. Docker must be installed, running, and protected; on hosts without Docker, the manager fails closed with a clear availability error.

## References

[1]: https://docs.docker.com/engine/security/rootless/ "Docker: Rootless mode"

[2]: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html "OWASP Docker Security Cheat Sheet"

[3]: https://owasp.org/www-project-docker-top-10/ "OWASP Docker Top 10"

[4]: https://arxiv.org/abs/2111.11475 "Threat modeling and security analysis of containers: A survey"

[5]: https://checkmarx.com/zero-post/glass-sandbox-complexity-of-python-sandboxing/ "The Glass Sandbox: The Complexity of Python Sandboxing"
