#!/usr/bin/env bash
# Start a packaged app (Linux or macOS) and let it convert a scanned PDF from inside: its self-test checks that
# Python runs, the conversion and OCR work, and MP3 export and the natural voices load (as the Windows build's
# self-test does). Usage: desktop-selftest.sh <app executable> [wrapper...]  (e.g. "xvfb-run -a" on Linux)
set -u
exe="$1"; shift
here="$(pwd)"
python tests/make_samples.py selftest
rm -f selftest/ready.txt selftest/report.txt
export DYSLEXIA_CONVERTER_READY_FILE="$here/selftest/ready.txt"
export DYSLEXIA_CONVERTER_SELFTEST="$here/selftest/sample_scanned.pdf;$here/selftest/out.pdf;$here/selftest/report.txt"
"$@" "$exe" > selftest/app.log 2>&1 &
pid=$!
reported() { [ -f selftest/ready.txt ] && grep -Eq "ready|error" selftest/ready.txt; }
waited=0
while ! reported && [ $waited -lt 240 ]; do
  if ! kill -0 $pid 2>/dev/null; then
    echo "the app closed by itself"; cat selftest/app.log; break
  fi
  sleep 5; waited=$((waited + 5))
done
# end the app (and, on Linux, the virtual screen started for it): the process and its children only
pkill -P $pid 2>/dev/null; kill $pid 2>/dev/null || true
fail() { echo "SELF-TEST FAILED: $1"; echo "--- app output"; tail -50 selftest/app.log; exit 1; }
[ -f selftest/ready.txt ] || fail "the app did not report that it started (Python did not run?)"
cat selftest/ready.txt; echo
[ -f selftest/report.txt ] && cat selftest/report.txt
grep -q "^error" selftest/ready.txt && fail "the app stopped with an error"
grep -q "selftest exit 0" selftest/ready.txt || fail "the self-test failed"
grep -qi "tesseract" selftest/report.txt || fail "Tesseract was not used"
grep -Eq "MISSING|FAILED" selftest/report.txt && fail "part of the app is missing or does not work (see above)"
echo "Self-test passed"
