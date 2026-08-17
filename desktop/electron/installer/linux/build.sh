#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
case "$(uname -s)" in Linux) ;; *) echo "Linux packages must be built on Linux or a compatible CI runner." >&2; exit 2 ;; esac
cd "$ROOT/desktop/electron"
pnpm build:linux
