#!/usr/bin/env bash
set -euo pipefail

SOURCE_DEFAULT=/mnt/commadrive/MVL_C15_HOST_UI_SOURCE_20261110
PYTHON_DEFAULT=/mnt/commadrive/.venv-native15/bin/python
XVFB_BIN=${C17_XVFB_BIN:-/usr/bin/Xvfb}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
SOURCE_ROOT=${C17_SOURCE_ROOT:-$SOURCE_DEFAULT}
PYTHON_BIN=${C17_PYTHON_BIN:-$PYTHON_DEFAULT}
LAYOUT=
OUTPUT_DIR=
FRAMES=12
PARAMS_MODE=normal
PUBLISHER_MODE=continuous
TIMEOUT_SECONDS=30

usage() {
  echo "usage: $0 --layout large|compact --output DIR [--frames N] [--params-mode normal|empty|malformed] [--publisher continuous|terminate|absent]" >&2
}

while (($#)); do
  case "$1" in
    --layout) LAYOUT=${2-}; shift 2 ;;
    --output) OUTPUT_DIR=${2-}; shift 2 ;;
    --frames) FRAMES=${2-}; shift 2 ;;
    --params-mode) PARAMS_MODE=${2-}; shift 2 ;;
    --publisher) PUBLISHER_MODE=${2-}; shift 2 ;;
    --timeout) TIMEOUT_SECONDS=${2-}; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 64 ;;
  esac
done

[[ $LAYOUT == large || $LAYOUT == compact ]] || { usage; exit 64; }
[[ $PARAMS_MODE == normal || $PARAMS_MODE == empty || $PARAMS_MODE == malformed ]] || { usage; exit 64; }
[[ $PUBLISHER_MODE == continuous || $PUBLISHER_MODE == terminate || $PUBLISHER_MODE == absent ]] || { usage; exit 64; }
[[ $FRAMES =~ ^[0-9]+$ && $FRAMES -ge 1 && $FRAMES -le 600 ]] || { usage; exit 64; }
[[ $TIMEOUT_SECONDS =~ ^[0-9]+$ && $TIMEOUT_SECONDS -ge 5 && $TIMEOUT_SECONDS -le 120 ]] || { usage; exit 64; }
[[ -n $OUTPUT_DIR && $OUTPUT_DIR == /* && -d $OUTPUT_DIR && ! -L $OUTPUT_DIR ]] || { echo "output must be an existing absolute non-symlink directory" >&2; exit 65; }
for output_name in result.json frame.png xvfb.log publisher.log ui.log; do
  [[ ! -e $OUTPUT_DIR/$output_name && ! -L $OUTPUT_DIR/$output_name ]] || { echo "refusing to overwrite output" >&2; exit 73; }
done
[[ -x $PYTHON_BIN && -e $SOURCE_ROOT/.git ]] || { echo "pinned host runtime unavailable" >&2; exit 69; }
[[ -x $XVFB_BIN ]] || { echo "Xvfb unavailable" >&2; exit 69; }
[[ $(git -C "$SOURCE_ROOT" rev-parse HEAD) == 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb ]] || { echo "source identity mismatch" >&2; exit 66; }
set +e
PYTHON_ABI=$($PYTHON_BIN -c 'import platform,capnp,pyray; print(platform.machine())' 2>/dev/null)
PYTHON_ABI_STATUS=$?
set -e
[[ $PYTHON_ABI_STATUS -eq 0 && $PYTHON_ABI == *x86_64 ]] || { echo "wrong ABI or missing Python dependency" >&2; exit 69; }

RUNTIME_DIR=$(mktemp -d /tmp/c17-ui.XXXXXXXX)
XVFB_PID=
PUB_PID=
UI_PID=
cleanup() {
  trap - EXIT INT TERM HUP
  for child in "$UI_PID" "$PUB_PID" "$XVFB_PID"; do
    if [[ -n $child ]] && kill -0 "$child" 2>/dev/null; then
      kill -TERM "$child" 2>/dev/null || true
    fi
  done
  for child in "$UI_PID" "$PUB_PID" "$XVFB_PID"; do
    if [[ -n $child ]]; then wait "$child" 2>/dev/null || true; fi
  done
  rm -rf -- "$RUNTIME_DIR"
}
forward_signal() {
  local sig=$1
  if [[ -n $UI_PID ]] && kill -0 "$UI_PID" 2>/dev/null; then kill -s "$sig" "$UI_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'forward_signal TERM' TERM
trap 'forward_signal INT' INT
trap 'forward_signal HUP' HUP

DISPLAY_NUM=$((200 + ($$ % 400)))
export DISPLAY=:$DISPLAY_NUM
export HOME=$RUNTIME_DIR/home
export XDG_CACHE_HOME=$RUNTIME_DIR/xdg-cache
export XDG_CONFIG_HOME=$RUNTIME_DIR/xdg-config
export XDG_DATA_HOME=$RUNTIME_DIR/xdg-data
export PARAMS_ROOT=$RUNTIME_DIR/params
export OPENPILOT_PREFIX=c17_$$_${RANDOM}
export C17_BENCH_TOKEN=display-only
export NOBOARD=1 SIMULATION=1 RECORD=0 RAYLIB_BACKEND=desktop
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$SOURCE_ROOT:$SOURCE_ROOT/msgq_repo:$SOURCE_ROOT/opendbc_repo:$SOURCE_ROOT/rednose_repo:$SOURCE_ROOT/tinygrad_repo
export NO_PROXY='*' no_proxy='*'
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export C17_MSGQ_ROOT=$RUNTIME_DIR/msgq
mkdir -m 700 "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$PARAMS_ROOT" "$C17_MSGQ_ROOT"
mkdir -m 700 "$C17_MSGQ_ROOT/msgq_$OPENPILOT_PREFIX"
mkdir -m 700 "$C17_MSGQ_ROOT/event"
cc -shared -fPIC -O2 -Wall -Wextra -Werror "$SCRIPT_DIR/c17_ipc_redirect.c" -ldl -o "$RUNTIME_DIR/c17_ipc_redirect.so"
export LD_PRELOAD=$RUNTIME_DIR/c17_ipc_redirect.so

if [[ $LAYOUT == large ]]; then
  export BIG=1 SCALE=0.65
  SCREEN=1500x800x24
else
  export BIG=0 SCALE=1.0
  SCREEN=600x300x24
fi

"$XVFB_BIN" "$DISPLAY" -screen 0 "$SCREEN" -nolisten tcp -noreset >"$OUTPUT_DIR/xvfb.log" 2>&1 &
XVFB_PID=$!
for _ in {1..50}; do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then break; fi
  kill -0 "$XVFB_PID" 2>/dev/null || { echo "Xvfb exited before ready" >&2; exit 70; }
  sleep 0.05
done
xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 || { echo "Xvfb unavailable" >&2; exit 70; }

PUBLISH_REQUIREMENT=required
if [[ $PUBLISHER_MODE != absent ]]; then
  PUB_ARGS=(--messages 0)
  [[ $PUBLISHER_MODE == terminate ]] && PUB_ARGS=(--messages 8)
  (cd "$SOURCE_ROOT" && exec "$PYTHON_BIN" "$SCRIPT_DIR/c17_device_state_publisher.py" "${PUB_ARGS[@]}") >"$OUTPUT_DIR/publisher.log" 2>&1 &
  PUB_PID=$!
else
  PUBLISH_REQUIREMENT=optional
fi

(cd "$SOURCE_ROOT" && exec "$PYTHON_BIN" "$SCRIPT_DIR/c17_standalone_ui.py" \
  --layout "$LAYOUT" --frames "$FRAMES" --output-dir "$OUTPUT_DIR" \
  --params-mode "$PARAMS_MODE" --publisher "$PUBLISH_REQUIREMENT" \
  --publisher-mode "$PUBLISHER_MODE") >"$OUTPUT_DIR/ui.log" 2>&1 &
UI_PID=$!

DEADLINE=$((SECONDS + TIMEOUT_SECONDS))
while kill -0 "$UI_PID" 2>/dev/null; do
  if ((SECONDS >= DEADLINE)); then
    kill -TERM "$UI_PID" 2>/dev/null || true
    sleep 1
    kill -KILL "$UI_PID" 2>/dev/null || true
    echo "UI exceeded timeout" >&2
    wait "$UI_PID" 2>/dev/null || true
    exit 124
  fi
  sleep 0.05
done
set +e
wait "$UI_PID"
UI_STATUS=$?
set -e
UI_PID=
echo "C17_LAUNCHER_EXIT ui_status=$UI_STATUS layout=$LAYOUT publisher=$PUBLISHER_MODE"
if [[ $UI_STATUS -eq 0 && ! -s $OUTPUT_DIR/result.json ]]; then
  echo "UI exited zero without result evidence" >&2
  exit 74
fi
exit "$UI_STATUS"
