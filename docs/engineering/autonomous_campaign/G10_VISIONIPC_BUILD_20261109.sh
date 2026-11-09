#!/usr/bin/env bash
set -euo pipefail
src=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263
rootfs=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs
stage=/mnt/commadrive/MVL_B3_G10_COMBINED_20261109/.g10_stage
image=sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95
test "$(docker image inspect --format '{{.Id}}' starpilot-larch64-builder:latest)" = "$image"
test "$(cat "$rootfs/VERSION")" = 19.9
test "$(git -C "$src" rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb
free=$(df -B1 --output=avail "$(dirname "$stage")" | tail -1)
test "$free" -ge 8589934592
mkdir -p "$stage"
trap 'printf "%s\n" "$?" > "$stage/visionipc_exit.txt"' EXIT
timeout 300s docker run --rm --platform linux/arm64 --network none --read-only --memory 1536m --cpus 1 --pids-limit 64 --security-opt no-new-privileges --tmpfs /agnos/tmp:rw,size=128m --mount type=bind,src="$rootfs",dst=/agnos,readonly --mount type=bind,src="$src",dst=/agnos/src,readonly --mount type=bind,src="$stage",dst=/agnos/build_cache "$image" chroot --userspec=1000:1000 /agnos /usr/bin/env PATH=/usr/local/venv/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 /bin/sh -c '
set -eu
cd /src
test "$(cat /VERSION)" = 19.9
inc=/usr/local/venv/lib/python3.12/site-packages/capnproto/install/include
flags="-g -fPIC -pipe -O2 -std=c++1z -D__COMMA_HARDWARE__ -mcpu=cortex-a57 -Werror -Wno-vla-cxx-extension -Wno-c99-designator -Wno-reorder-init-list -I/src -I/src/msgq_repo -I/src/openpilot -I$inc"
for unit in visionipc visionipc_server visionipc_client visionbuf; do
  clang++ $flags -c "/src/msgq_repo/msgq/visionipc/$unit.cc" -o "/build_cache/$unit.o"
done
llvm-ar rcs /build_cache/libvisionipc.a /build_cache/visionipc.o /build_cache/visionipc_server.o /build_cache/visionipc_client.o /build_cache/visionbuf.o
llvm-readelf -h /build_cache/visionipc_server.o
llvm-ar t /build_cache/libvisionipc.a
sha256sum /build_cache/*.o /build_cache/libvisionipc.a
' > "$stage/visionipc_build.log" 2>&1
cat "$stage/visionipc_build.log"
