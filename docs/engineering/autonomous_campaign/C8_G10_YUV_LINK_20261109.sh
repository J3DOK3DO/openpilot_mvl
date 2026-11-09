#!/usr/bin/env bash
# Offline model-independent native link proof. No output is executed.
set -euo pipefail
source_root=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263
rootfs=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs
stage=/mnt/commadrive/MVL_B3_G10_R0_RELEASE_ARTIFACTS_20261109/g10_yuv
image=sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95
test "$(docker image inspect --format '{{.Id}}' "$image")" = "$image"
test "$(cat "$rootfs/VERSION")" = 19.9
test "$(git -C "$source_root" rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb
test "$(df -B1 --output=avail "$(dirname "$stage")" | tail -1)" -ge 8589934592
mkdir -p "$stage"
trap 'printf "%s\n" "$?" > "$stage/build_exit.txt"' EXIT
timeout 300s docker run --rm --platform linux/arm64 --network none --read-only \
  --memory 1536m --cpus 1 --pids-limit 64 --security-opt no-new-privileges \
  --tmpfs /agnos/tmp:rw,size=128m \
  --mount type=bind,src="$rootfs",dst=/agnos,readonly \
  --mount type=bind,src="$source_root",dst=/agnos/src,readonly \
  --mount type=bind,src="$stage",dst=/agnos/build_cache \
  "$image" chroot --userspec=1000:1000 /agnos /bin/sh -c '
set -eu
test "$(cat /VERSION)" = 19.9
cd /src
clang++ -g -fPIC -pipe -O2 -std=c++1z -D__COMMA_HARDWARE__ -mcpu=cortex-a57 \
  -Werror -Wno-vla-cxx-extension -I/src/openpilot -I/src \
  -c /src/openpilot/common/yuv.cc -o /build_cache/yuv.o
clang++ -shared -Wl,--no-undefined -Wl,--as-needed \
  /build_cache/yuv.o -o /build_cache/libmvl_yuv_proof.so
llvm-readelf -h /build_cache/yuv.o /build_cache/libmvl_yuv_proof.so
llvm-readelf -d /build_cache/libmvl_yuv_proof.so
sha256sum /build_cache/yuv.o /build_cache/libmvl_yuv_proof.so
' > "$stage/build.log" 2>&1
