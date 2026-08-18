#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND="${FRONTEND_DIR:-$ROOT/frontend}"
TARGET="${1:-dir}"
PYTHON="${PYTHON:-python3}"

if [[ "$TARGET" == "win" ]] && [[ "$(uname -s)" != MINGW* && "$(uname -s)" != MSYS* && "$(uname -s)" != CYGWIN* ]]; then
  cat >&2 <<'EOF'
[desktop] Refusing an unsupported Linux-to-Windows release build.
[desktop] PyInstaller freezes the backend for the host operating system, so a Linux build would embed an ELF backend that cannot run inside the Windows installer.
[desktop] Run this command on a native Windows runner (for example, the release-windows GitHub Actions workflow) to produce a functional Windows NSIS setup executable.
EOF
  exit 2
fi

log() { printf '[desktop] %s\n' "$*"; }
fail() { printf '[desktop] ERROR: %s\n' "$*" >&2; exit 1; }

command -v "$PYTHON" >/dev/null || fail "Python 3 is required"
command -v node >/dev/null || fail "Node.js is required"
command -v pnpm >/dev/null || fail "pnpm is required"
[ -d "$FRONTEND" ] || fail "Frontend directory not found: $FRONTEND"

cd "$ROOT"
rm -rf desktop/frontend-dist desktop/backend-dist desktop/release

log "Building frontend from $FRONTEND"
(cd "$FRONTEND" && pnpm build)
cp -R "$FRONTEND/dist/public" desktop/frontend-dist
rm -rf desktop/frontend-dist/__manus__
if find desktop/frontend-dist -type f \( -iname '*debug-collector*' -o -path '*/__manus__/*' \) -print -quit | grep -q .; then
  fail "Development diagnostics remain in the desktop frontend bundle"
fi
if grep -R --binary-files=without-match -E 'VITE_ANALYTICS_ENDPOINT|VITE_ANALYTICS_WEBSITE_ID|/umami' desktop/frontend-dist >/dev/null; then
  fail "Analytics placeholders or Umami script references remain in the desktop frontend bundle"
fi

log "Preparing backend runtime environment"
if ! "$PYTHON" -c 'import PyInstaller' >/dev/null 2>&1; then
  fail "PyInstaller is not installed; install it in the build environment with: python -m pip install pyinstaller"
fi
PYTHONPATH="$ROOT" pyinstaller desktop/pyinstaller/backend.spec --clean --noconfirm --distpath "$ROOT/desktop/backend-dist" --workpath "$ROOT/desktop/.pyinstaller"

log "Installing desktop dependencies"
(cd desktop/electron && pnpm install --frozen-lockfile=false)

case "$TARGET" in
  dir) (cd desktop/electron && pnpm pack) ;;
  win) (cd desktop/electron && pnpm build:win) ;;
  mac) (cd desktop/electron && pnpm build:mac) ;;
  linux) (cd desktop/electron && pnpm build:linux) ;;
  all) (cd desktop/electron && pnpm build) ;;
  *) fail "Usage: $0 [dir|win|mac|linux|all]" ;;
esac

if [ -d desktop/release ]; then
  (cd desktop/release && sha256sum * > SHA256SUMS 2>/dev/null || true)
fi
log "Desktop build completed for target: $TARGET"
