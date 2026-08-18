# Connector implementation source notes

## GitHub REST connector

The GitHub REST adapter uses `Authorization: Bearer <token>` with `Accept: application/vnd.github+json` and `X-GitHub-Api-Version` headers. GitHub documents that personal access tokens and app-issued tokens require endpoint-specific scopes or permissions; insufficient authorization can surface as `401`, `403`, or `404`. The connector therefore stores credentials only in the local vault, never returns them in its API schema, and maps authorization failures to actionable test feedback.

The implemented route family follows the official paths: repository access uses `/user/repos` and `/repos/{owner}/{repo}`; releases use `POST /repos/{owner}/{repo}/releases`; workflow dispatch uses `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` with a required `ref` and optional `inputs`. Any live GitHub call remains dependent on a user-supplied credential reference and is covered by mocked HTTP tests in this repository.

## GitHub Actions allowance for repository-backed agent loops

GitHub’s official billing documentation states that private repositories consume the repository owner’s included minutes and storage, while standard runners are free for public repositories. The current GitHub Free entitlement is 2,000 GitHub-hosted-runner minutes and 500 MB shared artifact/package storage per month; use beyond included amounts is billed to the repository owner. The proposed schedule has 35 iterations, so it remains within the minute allowance only when the account’s existing monthly usage plus the actual aggregate runtime remains below 2,000 minutes and retained artifact/package storage stays within the shared 500 MB allowance. The scheduler should therefore use Ubuntu runners, avoid retained artifacts by default, and expose estimated or observed minute consumption rather than claim a guaranteed zero-cost run.

## References

1. [GitHub REST authentication](https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api)
2. [GitHub REST repositories](https://docs.github.com/en/rest/repos/repos)
3. [GitHub REST releases](https://docs.github.com/en/rest/releases/releases)
4. [GitHub REST workflows](https://docs.github.com/rest/actions/workflows)
5. [GitHub Actions billing](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions)
6. [GitHub pricing](https://github.com/pricing)
