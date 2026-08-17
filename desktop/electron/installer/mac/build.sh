#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
[ "$(uname -s)" = "Darwin" ] || { echo "macOS DMG builds must run on macOS for signing and notarization." >&2; exit 2; }
cd "$ROOT/desktop/electron"
pnpm build:mac
