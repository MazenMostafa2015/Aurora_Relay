
## Official CI/CD security findings

GitHub artifact attestations create cryptographically signed provenance claims linking a release artifact to its workflow, repository, environment, commit SHA, and triggering event. GitHub documents that attestations can include an SBOM and that consumers can verify them with the GitHub CLI. The documentation states that attestations alone do not provide security benefit unless consumers verify them, and recommends signing released binaries and packages rather than frequent test builds or source files.

Source: https://docs.github.com/en/actions/concepts/security/artifact-attestations
