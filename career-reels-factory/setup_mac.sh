#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "== Check ffmpeg (needs subtitles + drawtext) =="
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found. Install a build WITH subtitles + drawtext:"
  echo "  brew install homebrew-ffmpeg/ffmpeg/ffmpeg"
  exit 1
fi
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq "subtitles"; then
  echo "WARNING: this ffmpeg has no 'subtitles' filter. Burning captions will fail."
  echo "  Reinstall with: brew install homebrew-ffmpeg/ffmpeg/ffmpeg"
fi
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq "drawtext"; then
  echo "WARNING: this ffmpeg has no 'drawtext' filter. Question card overlay will fail."
fi

echo "== Find Python 3.12 =="
if command -v python3.12 >/dev/null 2>&1; then
  PY=python3.12
elif [ -x "$(brew --prefix python@3.12 2>/dev/null)/bin/python3.12" ]; then
  PY="$(brew --prefix python@3.12)/bin/python3.12"
else
  echo "Python 3.12 not found (3.13/3.14 break faster-whisper deps). Install it:"
  echo "  brew install python@3.12"
  exit 1
fi
echo "Using: $("$PY" --version)"

echo "== Create venv =="
if [ ! -x ".venv/bin/python" ]; then
  "$PY" -m venv .venv
fi

echo "== Install packages =="
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ".env created."
else
  echo ".env already exists. Skipping."
fi

echo ""
echo "Done. Next:"
echo "  1. Edit .env and fill GROQ_API_KEY (free) or ANTHROPIC_API_KEY"
echo "  2. ./run_mac.sh"
