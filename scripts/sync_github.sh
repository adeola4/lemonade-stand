#!/bin/bash
# Auto-sync Lemonade Stand skill dir -> GitHub (adeola4/lemonade-stand)
# Commits any changes with an auto message and pushes. Safe to run repeatedly.

set -e
DIR="/home/ubuntu/.hermes/skills/tan-executive-agent"
cd "$DIR"

# Skip if git not initialized or no remote
if [ ! -d .git ] || ! git remote get-url origin >/dev/null 2>&1; then
  echo "SKIP: no git repo/remote in $DIR"
  exit 0
fi

# Nothing to do if clean AND up to date
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  # still push in case local is ahead
  git push origin master >/dev/null 2>&1 || true
  echo "CLEAN: nothing to sync"
  exit 0
fi

# Auto-commit
STAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
FILES=$(git status --short | wc -l | tr -d ' ')
git add -A
git commit -q -m "auto-sync: $FILES file(s) changed — $STAMP" || true

# Push
if git push origin master 2>&1; then
  echo "SYNCED: $FILES file(s) pushed to github.com/adeola4/lemonade-stand @ $STAMP"
else
  echo "PUSH FAILED — check network/auth"
  exit 1
fi
