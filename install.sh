#!/bin/bash
# Install/refresh the game-recon skill into ~/.claude/skills
set -e
SRC="$(cd "$(dirname "$0")/skill" && pwd)"
DST="$HOME/.claude/skills/game-recon"
mkdir -p "$DST"
rsync -a --delete --exclude venv "$SRC/" "$DST/"
if [ ! -d "$DST/venv" ]; then
  python3 -m venv "$DST/venv"
  "$DST/venv/bin/pip" install --quiet google-play-scraper
fi
echo "installed to $DST"
