#!/usr/bin/env bash
# Temporary diagnostic: why does macOS ask "Allow 'Python' to find devices on local networks?" when the app starts?
# Starts the built app twice (update check off, then on) and records its processes, their network sockets, a
# screenshot and what macOS logs about local-network access. Results in diag/.
set -u
here="$(pwd)"
mkdir -p diag
python tests/make_samples.py selftest
app=$(find build/macos -maxdepth 1 -name "*.app" | head -n 1)
exe=$(find "$app/Contents/MacOS" -maxdepth 1 -type f -perm -u+x | head -n 1)
echo "app: $app  exe: $exe"
find "$app" -maxdepth 6 \( -iname "python*" -o -name "Info.plist" \) | head -40 > diag/bundle.txt
start=$(date "+%Y-%m-%d %H:%M:%S")

tree() {  # the app's process and everything it started
  local pids="$1" all="$1" next
  while [ -n "$pids" ]; do
    next=""
    for p in $pids; do next="$next $(pgrep -P $p | tr '\n' ' ')"; done
    pids=$(echo $next); all="$all $pids"
  done
  echo $all
}

run() {  # run <name> <check_updates True|False>
  local name=$1 updates=$2
  export DYSLEXIA_CONVERTER_HOME="$here/diag/home-$name"
  rm -rf "$DYSLEXIA_CONVERTER_HOME"
  python -c "from dyslexia_converter.settings import SettingsStore; SettingsStore().save_ui({'hide_start_notice': True, 'check_updates': $updates})"
  echo "=== $name (check_updates=$updates) $(date +%T)" | tee -a diag/sockets.txt diag/processes.txt
  "$exe" "$here/selftest/sample_paper.pdf" > "diag/app-$name.log" 2>&1 &
  local pid=$!
  for i in 1 2 3 4 5 6 7 8; do
    sleep 5
    local all; all=$(tree $pid)
    echo "--- t=$((i * 5))s pids: $all" | tee -a diag/sockets.txt >> diag/processes.txt
    ps -o pid,ppid,comm,args -p $(echo $all | tr ' ' ',') >> diag/processes.txt 2>&1
    sudo lsof -nP -a -p $(echo $all | tr ' ' ',') -i >> diag/sockets.txt 2>&1
    sudo lsof -nP -a -p $(echo $all | tr ' ' ',') -U >> diag/sockets.txt 2>&1
  done
  screencapture -x "diag/screen-$name.png"
  pkill -P $pid 2>/dev/null; kill $pid 2>/dev/null; sleep 3
}

run no-update-check False
run with-update-check True

sudo log show --start "$start" --info --debug --style compact \
  --predicate 'eventMessage CONTAINS[c] "local network" OR eventMessage CONTAINS[c] "localnetwork" OR process == "nehelper" OR (subsystem == "com.apple.network" AND (process CONTAINS[c] "python" OR process CONTAINS[c] "dyslexia"))' \
  > diag/network-log.txt 2>&1
sudo log show --start "$start" --info --style compact --predicate 'process CONTAINS[c] "python" OR process CONTAINS[c] "dyslexia"' \
  > diag/app-log.txt 2>&1
wc -l diag/*.txt
grep -i -m 40 "local network\|localnetwork" diag/network-log.txt || true
