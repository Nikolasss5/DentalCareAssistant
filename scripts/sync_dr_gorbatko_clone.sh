#!/usr/bin/env bash
set -euo pipefail

SOURCE_REPO="https://github.com/Nikolasss5/DrGorbatkoAssistant.git"
TARGET_BRANCH="sync/dr-gorbatko-test-clone"

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ROOT_DIR" ]]; then
  echo "ERROR: Run this command inside the DentalCareAssistant repository."
  exit 1
fi

cd "$ROOT_DIR"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: DentalCareAssistant has uncommitted changes. Commit or stash them first."
  exit 1
fi

git fetch origin "$TARGET_BRANCH"
git checkout "$TARGET_BRANCH"
git pull --ff-only origin "$TARGET_BRANCH"

TEMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

echo "Cloning DrGorbatkoAssistant..."
git clone --depth 1 "$SOURCE_REPO" "$TEMP_DIR/source"

# Export only Git-tracked source files. Local .env files and untracked credentials
# are never included in git archive.
git -C "$TEMP_DIR/source" archive HEAD | tar -x -C "$ROOT_DIR"

# Defense in depth: remove secret-bearing files even if they were accidentally
# present in the source repository.
rm -f \
  "$ROOT_DIR/.env" \
  "$ROOT_DIR/google_credentials.json" \
  "$ROOT_DIR/src/google_credentials.json" \
  "$ROOT_DIR/service-account.json" \
  "$ROOT_DIR/src/service-account.json"

# Preserve this reusable sync helper in the test branch.
mkdir -p "$ROOT_DIR/scripts"
cp "$0" "$ROOT_DIR/scripts/sync_dr_gorbatko_clone.sh"
chmod +x "$ROOT_DIR/scripts/sync_dr_gorbatko_clone.sh"

echo "Checking for forbidden secret files..."
if git ls-files | grep -E '(^|/)(\.env|google_credentials\.json|service-account\.json)$' >/dev/null; then
  echo "ERROR: A forbidden secret file is tracked. Nothing will be committed."
  exit 1
fi

git add -A

if git diff --cached --quiet; then
  echo "Dental test clone is already synchronized."
  exit 0
fi

git commit -m "Sync current Dr.Gorbatko Assistant into Dental test clone"
git push origin "$TARGET_BRANCH"

echo "DONE: DentalCareAssistant test branch synchronized safely."
