#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PACKAGE_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)
LAYOUT=auto
MAX_FRAMES=0
MAX_SECONDS=120
STATUS=
AUTHORIZATION=

usage() { echo "usage: $0 --status ABS_PATH [--layout auto|large|compact] [--max-frames N] [--max-seconds 1..3600] --authorization FILE" >&2; }
while (($#)); do
  case "$1" in
    --layout) LAYOUT=${2-}; shift 2 ;;
    --max-frames) MAX_FRAMES=${2-}; shift 2 ;;
    --max-seconds) MAX_SECONDS=${2-}; shift 2 ;;
    --status) STATUS=${2-}; shift 2 ;;
    --authorization) AUTHORIZATION=${2-}; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 64 ;;
  esac
done
[[ $LAYOUT == auto || $LAYOUT == large || $LAYOUT == compact ]] || { usage; exit 64; }
[[ $MAX_FRAMES =~ ^[0-9]+$ && $MAX_FRAMES -le 36000 ]] || { usage; exit 64; }
[[ $MAX_SECONDS =~ ^[0-9]+$ && $MAX_SECONDS -ge 1 && $MAX_SECONDS -le 3600 ]] || { usage; exit 64; }
[[ $STATUS == /* && ! -e $STATUS && ! -L $STATUS ]] || { echo "new absolute status path required" >&2; exit 65; }
[[ $(uname -m) == aarch64 && -f /AGNOS && $(cat /VERSION) == 19.9 ]] || { echo "requires physical AGNOS 19.9 AArch64" >&2; exit 69; }
source "$PACKAGE_ROOT/app/c18_supervise.sh"
[[ -r $AUTHORIZATION && ! -L $AUTHORIZATION ]] || { echo "exact-candidate device authorization required" >&2; exit 77; }
[[ $(stat -c '%u:%a' "$AUTHORIZATION") == 0:400 ]] || { echo "authorization must be root-owned mode 0400" >&2; exit 77; }

PYTHON=/usr/local/venv/bin/python
"$PYTHON" "$PACKAGE_ROOT/app/c18_preflight.py" --package "$PACKAGE_ROOT" --rootfs /
"$PYTHON" - "$AUTHORIZATION" "$PACKAGE_ROOT/MANIFEST.json" <<'PY'
import hashlib,json,sys
auth=json.load(open(sys.argv[1],encoding="utf-8"))
manifest=hashlib.sha256(open(sys.argv[2],"rb").read()).hexdigest()
if auth.get("schema") != "c18-device-authorization-v1":
  raise SystemExit("authorization schema mismatch")
required=("physical_isolation_verified","device_identity_verified","power_thermal_verified",
          "backup_verified","recovery_demonstrated","independent_test_approval","installation_authorized")
if any(auth.get(k) is not True for k in required) or auth.get("manifest_sha256") != manifest:
  raise SystemExit("authorization does not match all P1-P7 gates and exact manifest")
PY

if ps -eo comm= | grep -Eq '^(manager|controlsd|pandad|boardd|modeld|plannerd|radard)$'; then
  echo "control-related process detected; aborting" >&2
  exit 78
fi
[[ -e /dev/dri/card0 ]] || { echo "Comma DRM device unavailable" >&2; exit 69; }

RUNTIME_DIR=$(mktemp -d /tmp/c18-display.XXXXXXXX)
mkdir -m 700 "$RUNTIME_DIR/params"
export C18_DISPLAY_ONLY=1 NOBOARD=1 RECORD=0 RAYLIB_BACKEND=comma PYTHONDONTWRITEBYTECODE=1
export C18_SUPERVISOR_TIMEOUT_SECONDS="$MAX_SECONDS"
export C18_SUPERVISOR_KILL_GRACE_SECONDS=5
export PARAMS_ROOT="$RUNTIME_DIR/params"
export OPENPILOT_PREFIX="c18_display_$$_${RANDOM}"
export PYTHONPATH="$PACKAGE_ROOT/runtime:$PACKAGE_ROOT/runtime/msgq_repo:$PACKAGE_ROOT/runtime/opendbc_repo"
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy LD_PRELOAD
c18_supervise "$RUNTIME_DIR" "$PYTHON" -P "$PACKAGE_ROOT/app/c18_native_ui.py" \
  --layout "$LAYOUT" --max-frames "$MAX_FRAMES" --status "$STATUS"
