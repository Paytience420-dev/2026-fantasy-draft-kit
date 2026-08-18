#!/usr/bin/env bash
set -euo pipefail
REPO="https://github.com/Paytience420-dev/2026-fantasy-draft-kit.git"
WORK="${TMPDIR:-/tmp}/2026-fantasy-draft-kit-publish"
rm -rf "$WORK"
git clone "$REPO" "$WORK"
rsync -av --delete --exclude .git ./ "$WORK"/
cd "$WORK"
git add -A
if git diff --cached --quiet; then echo "No changes"; exit 0; fi
git commit -m "update 2026 fantasy draft kit"
git push origin main
echo "Published: https://paytience420-dev.github.io/2026-fantasy-draft-kit/"
