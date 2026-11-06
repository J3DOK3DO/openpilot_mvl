#!/usr/bin/env bash
set -euo pipefail
mode=${1:?use graph or lib}
case "$mode" in graph|lib) ;; *) echo 'mode must be graph or lib' >&2; exit 2;; esac
base=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106
source_root=$base/source_4b25263
rootfs=$base/rootfs
image=$base/system-19.9.ext4.img
cache=$base/build_cache
expected_source=4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb
expected_image=80d9373348ddff2a5d1f534fab3420383939c96f3eba60baab6b15339fc602c7
expected_builder=sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95
[[ $(cat "$rootfs/VERSION") == 19.9 ]]
[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_source" ]]
[[ $(sha256sum "$image" | cut -d' ' -f1) == "$expected_image" ]]
[[ $(docker image inspect --format '{{.Id}}' starpilot-larch64-builder:latest) == "$expected_builder" ]]
mkdir -p "$cache"
if [[ "$mode" == graph ]]; then
  scons_args='-n --minimal cache_dir=/build_cache'
else
  scons_args='-j1 --minimal cache_dir=/build_cache openpilot/common/libparams_c.so'
fi
timeout 900s docker run --rm --platform linux/arm64 --network none --read-only \
  --tmpfs /agnos/tmp:rw,size=512m \
  --mount type=bind,src="$rootfs",dst=/agnos,readonly \
  --mount type=bind,src="$source_root",dst=/agnos/src \
  --mount type=bind,src="$cache",dst=/agnos/build_cache \
  --mount type=bind,src=/dev,dst=/agnos/dev,readonly \
  --mount type=bind,src=/home/jdkd/.codex/worktrees/mvl-starpilot-manual-campaign/.git,dst=/agnos/home/jdkd/.codex/worktrees/mvl-starpilot-manual-campaign/.git,readonly \
  --mount type=bind,src=/mnt/commadrive/MVL_STARPILOT_UBUNTU_REASSESSMENT_20261103/.git/objects,dst=/agnos/mnt/commadrive/MVL_STARPILOT_UBUNTU_REASSESSMENT_20261103/.git/objects,readonly \
  starpilot-larch64-builder:latest \
  chroot /agnos /usr/bin/env PATH=/usr/local/venv/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 AGNOS199_SCONS_ARGS="$scons_args" \
  /bin/sh -c 'for p in /src /src/msgq_repo /src/opendbc_repo /src/openpilot/sunnypilot/neural_network_data /src/panda /src/rednose_repo /src/teleoprtc_repo /src/tinygrad_repo; do git config --global --add safe.directory "$p"; done; cd /src; test "$(git rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb; uname -m; cat /VERSION; /usr/local/venv/bin/python3 -m SCons $AGNOS199_SCONS_ARGS'
