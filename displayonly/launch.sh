#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
PYTHON=/usr/local/venv/bin/python
STARTUP_TIMEOUT=${C19_STARTUP_TIMEOUT_SECONDS:-120}
KILL_GRACE=${C19_KILL_GRACE_SECONDS:-5}
LAYOUT=${C19_LAYOUT:-auto}

[[ $STARTUP_TIMEOUT =~ ^[0-9]+$ && $STARTUP_TIMEOUT -ge 1 && $STARTUP_TIMEOUT -le 300 ]] || exit 64
[[ $KILL_GRACE =~ ^[0-9]+$ && $KILL_GRACE -ge 1 && $KILL_GRACE -le 30 ]] || exit 64
[[ $LAYOUT == auto || $LAYOUT == large || $LAYOUT == compact ]] || exit 64
[[ -x $PYTHON && -f /AGNOS && -r /VERSION && $(cat /VERSION) == 19.9 ]] || {
  echo "C19 display requires AGNOS 19.9 Python 3.12" >&2
  exit 69
}
[[ -S /tmp/drmfd.sock && -e /dev/dri/card0 ]] || {
  echo "C19 display cannot acquire the authentic Comma display path" >&2
  exit 69
}
if ps -eo comm= | grep -Eq '^(manager|controlsd|selfdrived|pandad|boardd|modeld|plannerd|radard|can)$'; then
  echo "vehicle or manager process detected; refusing display startup" >&2
  exit 78
fi

RUNTIME_DIR=$(mktemp -d /tmp/c19-display.XXXXXXXX)
chmod 700 "$RUNTIME_DIR"
READY=$RUNTIME_DIR/ready.json
STATUS=$RUNTIME_DIR/status.json
CHILD=

stop_child() {
  local sig=${1:-TERM}
  local remaining=$KILL_GRACE
  if [[ -n $CHILD ]] && kill -0 "$CHILD" 2>/dev/null; then
    kill -s "$sig" -- "-$CHILD" 2>/dev/null || kill -s "$sig" "$CHILD" 2>/dev/null || true
    while ((remaining > 0)) && kill -0 "$CHILD" 2>/dev/null; do
      sleep 1
      remaining=$((remaining - 1))
    done
    if kill -0 "$CHILD" 2>/dev/null; then
      kill -KILL -- "-$CHILD" 2>/dev/null || kill -KILL "$CHILD" 2>/dev/null || true
    fi
  fi
  [[ -z $CHILD ]] || wait "$CHILD" 2>/dev/null || true
}

cleanup() {
  trap - EXIT INT TERM HUP
  stop_child TERM
  rm -rf -- "$RUNTIME_DIR"
}
trap cleanup EXIT
trap 'stop_child TERM; exit 143' TERM
trap 'stop_child INT; exit 130' INT
trap 'stop_child HUP; exit 129' HUP

export C19_RUNTIME_DIR=$RUNTIME_DIR
export RAYLIB_BACKEND=comma
export PYTHONDONTWRITEBYTECODE=1
export NOBOARD=1
export RECORD=0
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy LD_PRELOAD PYTHONPATH PARAMS_ROOT OPENPILOT_PREFIX C19_OFFLINE_QUALIFICATION

setsid "$PYTHON" -P "$ROOT/displayonly/c19_display.py" --layout "$LAYOUT" \
  --ready "$READY" --status "$STATUS" &
CHILD=$!

deadline=$((SECONDS + STARTUP_TIMEOUT))
while [[ ! -f $READY ]]; do
  if ! kill -0 "$CHILD" 2>/dev/null; then
    wait "$CHILD"
    exit $?
  fi
  if ((SECONDS >= deadline)); then
    echo "C19 display startup watchdog expired" >&2
    stop_child TERM
    exit 124
  fi
  sleep 0.1
done

set +e
wait "$CHILD"
code=$?
set -e
CHILD=
exit "$code"
