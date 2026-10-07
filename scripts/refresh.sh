#!/bin/zsh
# daily: regenerate the readout and push it if anything changed.
set -e
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
cd "$(dirname "$0")/.."
git pull -q --rebase
GH_TOKEN=$(gh auth token) python3 -I scripts/readout.py
git diff --quiet README.md && exit 0
git commit -q -m "readout: daily refresh" README.md
git push -q
