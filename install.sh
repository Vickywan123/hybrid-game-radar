#!/bin/bash
# Install/refresh the hybrid-game-radar skill into ~/.claude/skills
set -e
SRC="$(cd "$(dirname "$0")/skill" && pwd)"
DST="$HOME/.claude/skills/hybrid-game-radar"
mkdir -p "$DST"
rsync -a --delete --exclude venv --exclude cache "$SRC/" "$DST/"
if [ ! -d "$DST/venv" ]; then
  python3 -m venv "$DST/venv"
  "$DST/venv/bin/pip" install --quiet google-play-scraper
fi
echo "installed to $DST"
