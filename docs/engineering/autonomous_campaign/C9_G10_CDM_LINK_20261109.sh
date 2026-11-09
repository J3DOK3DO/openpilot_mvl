#!/usr/bin/env bash
set -euo pipefail
src=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263
rootfs=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs
stage=/mnt/commadrive/MVL_C9_B3_G10_R0_ARTIFACTS_20261109/g10_cdm
image=sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95
test "$(docker image inspect --format '{{.Id}}' starpilot-larch64-builder:latest)" = "$image"
test "$(git -C "$src" rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb
test "$(cat "$rootfs/VERSION")" = 19.9
free=$(df -B1 --output=avail "$(dirname "$stage")" | tail -1)
test "$free" -ge 8589934592
mkdir -p "$stage"
trap 'printf "%s\n" "$?" > "$stage/build_exit.txt"' EXIT
timeout 300s docker run --rm --platform linux/arm64 --network none --read-only \
  --memory 1536m --cpus 1 --pids-limit 64 --security-opt no-new-privileges \
  --tmpfs /agnos/tmp:rw,size=128m \
  --mount type=bind,src="$rootfs",dst=/agnos,readonly \
  --mount type=bind,src="$src",dst=/agnos/src,readonly \
  --mount type=bind,src="$stage",dst=/agnos/build_cache \
  "$image" chroot --userspec=1000:1000 /agnos /bin/sh -c '
set -eu
cd /src
clang++ -fPIC -O2 -std=c++1z -D__COMMA_HARDWARE__ -mcpu=cortex-a57 \
  -I/src/openpilot -c /src/openpilot/system/camerad/cameras/cdm.cc -o /build_cache/cdm.o
clang++ -shared -Wl,--no-undefined -Wl,-soname,libmvl_cdm_proof.so \
  /build_cache/cdm.o -o /build_cache/libmvl_cdm_proof.so
llvm-readelf -h /build_cache/cdm.o
llvm-readelf -h -d /build_cache/libmvl_cdm_proof.so
llvm-nm -D --defined-only /build_cache/libmvl_cdm_proof.so
sha256sum /build_cache/cdm.o /build_cache/libmvl_cdm_proof.so
' > "$stage/build.log" 2>&1
