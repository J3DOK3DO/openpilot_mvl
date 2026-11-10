#!/usr/bin/env bash
set -euo pipefail

OUTPUT_ROOT=${1-}
[[ -n $OUTPUT_ROOT && $OUTPUT_ROOT == /* && -d $OUTPUT_ROOT && ! -L $OUTPUT_ROOT ]] || { echo "usage: $0 ABSOLUTE_EMPTY_OUTPUT_DIR" >&2; exit 64; }
LAUNCHER=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)/c17_standalone_ui.sh
XCLOSE_SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)/tests/c17_x11_close.c
XCLOSE=$OUTPUT_ROOT/c17_x11_close
cc -Wall -Wextra -Werror "$XCLOSE_SRC" -lX11 -o "$XCLOSE"

PASS_COUNT=0
FAIL_COUNT=0
run_success() {
  local name=$1
  shift
  local out=$OUTPUT_ROOT/$name
  mkdir -m 700 "$out"
  echo "C17_CASE_BEGIN $name"
  set +e
  "$LAUNCHER" --output "$out" "$@"
  local status=$?
  set -e
  echo "$status" >"$out/exit.status"
  if [[ $status -eq 0 && -s $out/result.json ]]; then
    echo "C17_CASE_PASS $name exit=$status"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "C17_CASE_FAIL $name exit=$status"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

run_expected_failure() {
  local name=$1 expected=$2
  shift 2
  local out=$OUTPUT_ROOT/$name
  mkdir -m 700 "$out"
  echo "C17_CASE_BEGIN $name expected_failure=$expected"
  set +e
  "$@" --output "$out" --layout compact
  local status=$?
  set -e
  echo "$status" >"$out/exit.status"
  if [[ $status -eq $expected ]]; then
    echo "C17_CASE_PASS $name expected_exit=$status"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "C17_CASE_FAIL $name exit=$status expected=$expected"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

run_success bounded_compact --layout compact --frames 12
run_success bounded_large --layout large --frames 12
run_success empty_params --layout compact --frames 3 --params-mode empty
run_success malformed_params --layout compact --frames 3 --params-mode malformed
run_success publisher_terminated --layout compact --frames 80 --publisher terminate
run_success publisher_absent --layout compact --frames 3 --publisher absent

if grep -q 'DEGRADED_PUBLISHER_TERMINATED_STALE' "$OUTPUT_ROOT/publisher_terminated/result.json" &&
   grep -q '"ipc_fresh_at_exit": false' "$OUTPUT_ROOT/publisher_terminated/result.json"; then
  echo "C17_IPC_CLASSIFICATION_PASS publisher_terminated=DEGRADED_STALE"
else
  echo "C17_IPC_CLASSIFICATION_FAIL publisher_terminated"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
if grep -q 'DEGRADED_NO_PUBLISHER' "$OUTPUT_ROOT/publisher_absent/result.json" &&
   grep -q '"device_state_seen_by_real_ui_submaster": false' "$OUTPUT_ROOT/publisher_absent/result.json"; then
  echo "C17_IPC_CLASSIFICATION_PASS publisher_absent=DEGRADED_NO_PUBLISHER"
else
  echo "C17_IPC_CLASSIFICATION_FAIL publisher_absent"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

SIG_OUT=$OUTPUT_ROOT/sigterm
mkdir -m 700 "$SIG_OUT"
echo "C17_CASE_BEGIN sigterm"
"$LAUNCHER" --output "$SIG_OUT" --layout large --frames 600 --timeout 60 &
LAUNCH_PID=$!
sleep 2
kill -TERM "$LAUNCH_PID"
set +e
wait "$LAUNCH_PID"
SIG_STATUS=$?
set -e
echo "$SIG_STATUS" >"$SIG_OUT/exit.status"
if [[ $SIG_STATUS -eq 0 && -s $SIG_OUT/result.json ]] && grep -q 'signal:SIGTERM' "$SIG_OUT/result.json"; then
  echo "C17_CASE_PASS sigterm exit=$SIG_STATUS"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "C17_CASE_FAIL sigterm exit=$SIG_STATUS"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

WM_OUT=$OUTPUT_ROOT/window_close
mkdir -m 700 "$WM_OUT"
echo "C17_CASE_BEGIN window_close"
"$LAUNCHER" --output "$WM_OUT" --layout compact --frames 600 --timeout 60 &
LAUNCH_PID=$!
DISPLAY_VALUE=
for _ in {1..100}; do
  XVFB_CHILD=$(pgrep -P "$LAUNCH_PID" -f '/Xvfb' | head -1 || true)
  if [[ -n $XVFB_CHILD ]]; then
    DISPLAY_VALUE=$(tr '\0' '\n' <"/proc/$XVFB_CHILD/cmdline" | grep -E '^:[0-9]+$' | head -1 || true)
  fi
  [[ -n $DISPLAY_VALUE ]] && break
  sleep 0.05
done
XCLOSE_STATUS=1
if [[ -n $DISPLAY_VALUE ]]; then
  for _ in {1..100}; do
    set +e
    DISPLAY=$DISPLAY_VALUE "$XCLOSE" "C17 MVL DISPLAY-ONLY COMPACT HOST BENCH"
    XCLOSE_STATUS=$?
    set -e
    [[ $XCLOSE_STATUS -eq 0 ]] && break
    sleep 0.05
  done
fi
set +e
wait "$LAUNCH_PID"
WM_STATUS=$?
set -e
echo "$WM_STATUS" >"$WM_OUT/exit.status"
echo "$XCLOSE_STATUS" >"$WM_OUT/x11_close.status"
if [[ $WM_STATUS -eq 0 && $XCLOSE_STATUS -eq 0 && -s $WM_OUT/result.json ]] && grep -q 'window_manager_close' "$WM_OUT/result.json"; then
  echo "C17_CASE_PASS window_close exit=$WM_STATUS"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "C17_CASE_FAIL window_close exit=$WM_STATUS xclose=$XCLOSE_STATUS"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

run_expected_failure missing_xvfb 70 env C17_XVFB_BIN=/bin/false "$LAUNCHER"
run_expected_failure missing_dependency 69 env C17_PYTHON_BIN=/bin/false "$LAUNCHER"
run_expected_failure wrong_abi 69 env C17_PYTHON_BIN=/mnt/commadrive/MVL_C14A_NATIVE_IPC_WORK_20261110/openpilot/common/libparams_c.so "$LAUNCHER"

RO_OUT=$OUTPUT_ROOT/read_only_output
mkdir -m 500 "$RO_OUT"
echo "C17_CASE_BEGIN read_only_output expected_failure"
set +e
"$LAUNCHER" --output "$RO_OUT" --layout compact
RO_STATUS=$?
set -e
chmod 700 "$RO_OUT"
echo "$RO_STATUS" >"$RO_OUT/exit.status"
if [[ $RO_STATUS -ne 0 ]]; then
  echo "C17_CASE_PASS read_only_output expected_nonzero=$RO_STATUS"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  echo "C17_CASE_FAIL read_only_output unexpectedly_zero"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo "C17_LIFECYCLE_SUMMARY pass=$PASS_COUNT fail=$FAIL_COUNT total=$((PASS_COUNT + FAIL_COUNT))"
[[ $FAIL_COUNT -eq 0 ]]
