# Connector implementation source notes

## GitHub REST connector

The GitHub REST adapter uses `Authorization: Bearer <token>` with `Accept: application/vnd.github+json` and `X-GitHub-Api-Version` headers. GitHub documents that personal access tokens and app-issued tokens require endpoint-specific scopes or permissions; insufficient authorization can surface as `401`, `403`, or `404`. The connector therefore stores credentials only in the local vault, never returns them in its API schema, and maps authorization failures to actionable test feedback.

The implemented route family follows the official paths: repository access uses `/user/repos` and `/repos/{owner}/{repo}`; releases use `POST /repos/{owner}/{repo}/releases`; workflow dispatch uses `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` with a required `ref` and optional `inputs`. Any live GitHub call remains dependent on a user-supplied credential reference and is covered by mocked HTTP tests in this repository.

## References

1. [GitHub REST authentication](https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api)
2. [GitHub REST repositories](https://docs.github.com/en/rest/repos/repos)
3. [GitHub REST releases](https://docs.github.com/en/rest/releases/releases)
4. [GitHub REST workflows](https://docs.github.com/rest/actions/workflows)
