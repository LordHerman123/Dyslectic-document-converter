#!/usr/bin/env bash
# Temporary diagnostic: which step makes macOS ask "Allow 'Python' to find devices on local networks?" in the
# macOS build job? Screenshots after each step (the tests, the app's self-test, a plain start of the app) and what
# macOS logs about local-network access. Results in diag/.
set -u
here="$(pwd)"
mkdir -p diag
app=$(find build/macos -maxdepth 1 -name "*.app" | head -n 1)
exe=$(find "$app/Contents/MacOS" -maxdepth 1 -type f -perm -u+x | head -n 1)
echo "app: $app  exe: $exe  python: $(command -v python) $(python -c 'import sys; print(sys.executable)')"
start=$(date "+%Y-%m-%d %H:%M:%S")
shot() { sleep 3; screencapture -x "diag/$1.png"; echo "$(date +%T) screenshot $1"; }

shot 0-start
echo "=== tests $(date +%T)"
python -m pytest -q -p no:cacheprovider 2>&1 | tail -3
shot 1-after-tests
echo "=== app self-test $(date +%T)"
bash .github/scripts/desktop-selftest.sh "$exe" 2>&1 | tail -4
shot 2-after-selftest
echo "=== plain start $(date +%T)"
bash .github/scripts/desktop-screenshot.sh "$exe" diag/3-app-start.png 2>&1 | tail -2

sudo log show --start "$start" --info --debug --style compact \
  --predicate 'process == "nehelper" OR eventMessage CONTAINS[c] "local network" OR eventMessage CONTAINS[c] "localnetwork" OR (subsystem == "com.apple.network" AND process CONTAINS[c] "python")' \
  > diag/network-log.txt 2>&1
sudo log show --start "$start" --info --style compact --predicate 'process == "UserNotificationCenter" OR process == "nehelper" AND eventMessage CONTAINS[c] "prompt"' \
  > diag/prompt-log.txt 2>&1
wc -l diag/*.txt
