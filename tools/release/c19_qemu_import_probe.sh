#!/usr/bin/env bash
# Offline ARM64 import closure probe. Requires a disposable AGNOS rootfs copy.
set -euo pipefail

OVERLAY=${1-}
[[ -n $OVERLAY && $OVERLAY == /* && -d $OVERLAY && ! -L $OVERLAY ]] || {
  echo "usage: $0 ABS_DISPOSABLE_AGNOS_ROOTFS_COPY" >&2
  exit 64
}
[[ -x $OVERLAY/usr/bin/python3.12 ]] || { echo "AGNOS Python missing" >&2; exit 69; }
if [[ -d $OVERLAY/opt/c19/C19_NATIVE_UI_OFFLINE_CANDIDATE/runtime ]]; then
  PACKAGE_NAME=C19_NATIVE_UI_OFFLINE_CANDIDATE
elif [[ -d $OVERLAY/opt/c19/C18_NATIVE_UI_OFFLINE_CANDIDATE/runtime ]]; then
  PACKAGE_NAME=C18_NATIVE_UI_OFFLINE_CANDIDATE
else
  echo "a C18 or C19 native candidate must be staged at /opt/c19 in the disposable copy" >&2
  exit 69
fi
[[ ! -e $OVERLAY/AGNOS ]] || {
  echo "disable only the disposable /AGNOS marker to avoid emulating device identity" >&2
  exit 69
}

PREFIX=c19_qemu_probe_$$
PARAMS=$(mktemp -d /tmp/c19-native-params.XXXXXXXX)
HOST_MSGQ=/dev/shm/msgq_$PREFIX
OVERLAY_MSGQ=$OVERLAY/dev/shm/msgq_$PREFIX
PUBLISHER=
cleanup() {
  trap - EXIT INT TERM HUP
  if [[ -n $PUBLISHER ]] && kill -0 "$PUBLISHER" 2>/dev/null; then
    kill -TERM "$PUBLISHER" 2>/dev/null || true
    wait "$PUBLISHER" 2>/dev/null || true
  fi
  rm -rf -- "$PARAMS" "$HOST_MSGQ" "$OVERLAY_MSGQ"
}
trap cleanup EXIT INT TERM HUP
mkdir -m 700 "$HOST_MSGQ" "$OVERLAY_MSGQ"

GUEST_RUNTIME=/opt/c19/$PACKAGE_NAME/runtime
PYTHONPATH_GUEST=$GUEST_RUNTIME:$GUEST_RUNTIME/msgq_repo:$GUEST_RUNTIME/opendbc_repo:/usr/local/venv/lib/python3.12/site-packages
ENV=(PYTHONHOME=/usr PYTHONPATH=$PYTHONPATH_GUEST QEMU_LD_PREFIX=$OVERLAY
     RAYLIB_BACKEND=comma NOBOARD=1 RECORD=0 PARAMS_ROOT=$PARAMS
     OPENPILOT_PREFIX=$PREFIX PYTHONDONTWRITEBYTECODE=1)
PYTHON=(/usr/bin/qemu-aarch64-static "$OVERLAY/usr/bin/python3.12" -u)
SERVICES='["modelV2","controlsState","onroadEvents","extrinsicsCalibration","radarState","deviceState","pandaStates","carParams","driverMonitoringState","carState","driverStateV2","narrowRoadCameraState","wideRoadCameraState","managerState","selfdriveState","longitudinalPlan","gpsLocationExternal","gpsLocation","navInstruction","carOutput","carControl","vehicleParameters","testJoystick","rawAudioData","modelManagerSP","selfdriveStateSP","longitudinalPlanSP","backupManagerSP","lateralTorqueParameters","carStateSP","liveMapDataSP","carParamsSP","lateralDelay"]'

cd /
env "${ENV[@]}" "${PYTHON[@]}" -c \
  "import time; from openpilot.cereal import messaging; pm=messaging.PubMaster($SERVICES); print('PRIVATE_FIXTURE_READY',flush=True); time.sleep(90)" &
PUBLISHER=$!
for _ in $(seq 1 150); do
  [[ -e $HOST_MSGQ/deviceState || -e $OVERLAY_MSGQ/deviceState ]] && break
  kill -0 "$PUBLISHER" 2>/dev/null || { echo "private fixture exited" >&2; exit 70; }
  sleep 0.1
done
[[ -e $HOST_MSGQ/deviceState || -e $OVERLAY_MSGQ/deviceState ]] || {
  echo "private fixture did not become ready" >&2
  exit 70
}

env "${ENV[@]}" timeout 75 "${PYTHON[@]}" -c \
  'import openpilot.cereal; print("CEREAL_PASS"); import openpilot.common.params; print("PARAMS_PASS"); import openpilot.system.ui.lib.application; print("GUI_APP_IMPORT_PASS"); import openpilot.selfdrive.ui.ui_state; print("UI_STATE_IMPORT_PASS"); import openpilot.selfdrive.ui.layouts.main; print("LARGE_LAYOUT_MODULE_IMPORT_PASS"); import openpilot.selfdrive.ui.mici.layouts.main; print("COMPACT_LAYOUT_MODULE_IMPORT_PASS")'
echo "PACKAGE_NAME=$PACKAGE_NAME"
echo "C19_QEMU_IMPORT_CLOSURE_PASS"
