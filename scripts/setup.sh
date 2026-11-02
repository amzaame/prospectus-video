#!/usr/bin/env bash
# Create (or refresh) a working copy of the generator where catalogues are extracted and videos rendered.
# The installed plugin folder itself is never written to.
#
#   bash scripts/setup.sh [workspace]      # default: ./prospectus-video
#
# Re-running it updates the code and keeps the user's catalogues, specs, spot configs and renders.
set -euo pipefail

TOOL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="${1:-$PWD/prospectus-video}"

fail() { echo "setup: $*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || fail "macOS only (cut-outs and OCR use Apple Vision)."
command -v python3 >/dev/null || fail "python3 not found."
command -v node >/dev/null || fail "node not found: brew install node"
command -v ffmpeg >/dev/null || fail "ffmpeg not found: brew install ffmpeg"
[ -d "/Applications/Google Chrome.app" ] || echo "setup: Google Chrome not found; Remotion will try to download its own browser."

mkdir -p "$WS"
rsync -a --exclude node_modules --exclude public --exclude 'src/spots/*.json' "$TOOL/video/" "$WS/video/"
rsync -a --exclude __pycache__ --exclude '_price_crop.png' "$TOOL/extractor/" "$WS/extractor/"
mkdir -p "$WS/specs/examples" "$WS/video/src/spots" "$WS/video/public" "$WS/output"
cp "$TOOL"/specs/*.json "$WS/specs/examples/"
cp "$TOOL/requirements.txt" "$WS/"

if [ ! -x "$WS/.venv/bin/python" ]; then
  python3 -m venv "$WS/.venv"
fi
"$WS/.venv/bin/pip" install -q --upgrade pip
"$WS/.venv/bin/pip" install -q -r "$WS/requirements.txt"

(cd "$WS/video" && if [ -d node_modules ]; then npm install --no-audit --no-fund --silent; else npm ci --no-audit --no-fund --silent; fi)

echo "setup: ready in $WS"
