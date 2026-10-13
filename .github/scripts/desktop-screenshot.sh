#!/usr/bin/env bash
# Start a packaged app (Linux or macOS) with a sample paper, as "Open with" does, and save a screenshot of it, to
# see each build as its users will. Usage: desktop-screenshot.sh <app executable> <out.png>
# (on Linux inside a virtual screen: xvfb-run -a -s "-screen 0 1280x720x24" desktop-screenshot.sh ...)
set -u
exe="$1"; out="$2"
here="$(pwd)"
python tests/make_samples.py selftest
# a fresh settings folder in which the "Good to know" notice of the first start is already ticked off
export DYSLEXIA_CONVERTER_HOME="$here/selftest/screenshot-home"
rm -rf "$DYSLEXIA_CONVERTER_HOME" selftest/opened.txt selftest/ready.txt
python -c "from dyslexia_converter.settings import SettingsStore; SettingsStore().save_ui({'hide_start_notice': True})"
export DYSLEXIA_CONVERTER_READY_FILE="$here/selftest/ready.txt"
"$exe" "$here/selftest/sample_paper.pdf" > selftest/app-screenshot.log 2>&1 &
pid=$!
waited=0
while [ ! -f selftest/opened.txt ] && [ $waited -lt 180 ]; do
  kill -0 $pid 2>/dev/null || break
  sleep 5; waited=$((waited + 5))
done
sleep 15  # let the pages of the document appear
if command -v screencapture > /dev/null; then
  screencapture -x "$out"
else
  python -c "import os, sys; from PIL import ImageGrab; ImageGrab.grab(xdisplay=os.environ['DISPLAY']).save(sys.argv[1])" "$out"
fi
pkill -P $pid 2>/dev/null; kill $pid 2>/dev/null || true
cat selftest/opened.txt 2>/dev/null; echo
ls -la "$out"
