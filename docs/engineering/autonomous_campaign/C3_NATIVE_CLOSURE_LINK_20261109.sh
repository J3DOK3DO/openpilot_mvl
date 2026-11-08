#!/usr/bin/env bash
set -euo pipefail
src=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263
rootfs=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs
stage=/mnt/commadrive/MVL_C3_NATIVE_CLOSURE_20261109/.c3_stage
repo=/mnt/commadrive/MVL_C3_NATIVE_CLOSURE_20261109
old_msgq=/mnt/commadrive/MVL_C5_NATIVE_STAGE_20261108/source/msgq_repo/libmsgq.a
old_socket=/mnt/commadrive/MVL_C6_NATIVE_STAGE_20261108/libsocketmaster.a
image=sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95
test "$(docker image inspect --format '{{.Id}}' starpilot-larch64-builder:latest)" = "$image"
test "$(cat "$rootfs/VERSION")" = 19.9
test "$(git -C "$src" rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb
test "$(sha256sum "$old_msgq" | cut -d' ' -f1)" = 0b6ad7dad40090a86aacc93b971a74ed12403810be1a51f51ad1e4965c00d1a7
test "$(sha256sum "$old_socket" | cut -d' ' -f1)" = 05c251e4214dfd2600f489dfdd7f21f2058e8aee794c0607844caeb7f8655d6a
mkdir -p "$stage"
if ! cmp -s "$repo/docs/engineering/autonomous_campaign/C3_NATIVE_CLOSURE_SMOKE_20261109.cc" "$stage/closure_smoke.cc"; then
  cp "$repo/docs/engineering/autonomous_campaign/C3_NATIVE_CLOSURE_SMOKE_20261109.cc" "$stage/closure_smoke.cc"
  rm -f "$stage/closure_smoke.o"
fi
cp "$old_msgq" "$stage/libmsgq.a"
cp "$old_socket" "$stage/libsocketmaster.a"
set +e
timeout 300s docker run --rm --platform linux/arm64 --network none --read-only --memory 1536m --cpus 1 --pids-limit 64 --security-opt no-new-privileges --tmpfs /agnos/tmp:rw,size=128m --mount type=bind,src="$rootfs",dst=/agnos,readonly --mount type=bind,src="$src",dst=/agnos/src,readonly --mount type=bind,src="$stage",dst=/agnos/build_cache "$image" chroot --userspec=1000:1000 /agnos /usr/bin/env PATH=/usr/local/venv/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 /bin/sh -c '
set -eu
cd /src
test "$(cat /VERSION)" = 19.9
clang++ --version | head -n 1
ld --version | head -n 1
llvm-nm --version | head -n 1
llvm-readelf -h /build_cache/libsocketmaster.a | grep -m1 AArch64
llvm-readelf -h /build_cache/libmsgq.a | grep -m1 AArch64
inc=/usr/local/venv/lib/python3.12/site-packages/capnproto/install/include
libs=/usr/local/venv/lib/python3.12/site-packages/capnproto/install/lib
flags="-g -fPIC -pipe -O2 -std=c++1z -D__COMMA_HARDWARE__ -mcpu=cortex-a57 -I/build_cache -I$inc -I/src/openpilot -I/src/msgq_repo -I/src/openpilot/cereal/gen/cpp -I/src"
for name in log deprecated custom car; do
  test -f /build_cache/$name.capnp.o || clang++ $flags -c /src/openpilot/cereal/gen/cpp/$name.capnp.c++ -o /build_cache/$name.capnp.o
done
test -f /build_cache/closure_smoke.o || clang++ $flags -c /build_cache/closure_smoke.cc -o /build_cache/closure_smoke.o
clang++ -Wl,--no-undefined -Wl,-Map,/build_cache/closure_smoke.map -o /build_cache/closure_smoke.elf /build_cache/closure_smoke.o -Wl,--whole-archive /build_cache/libsocketmaster.a /build_cache/libmsgq.a -Wl,--no-whole-archive /build_cache/log.capnp.o /build_cache/deprecated.capnp.o /build_cache/custom.capnp.o /build_cache/car.capnp.o $libs/libcapnp.a $libs/libkj.a -lzmq -pthread
sha256sum /build_cache/closure_smoke.elf > /build_cache/first_link.sha256
clang++ -Wl,--no-undefined -Wl,-Map,/build_cache/closure_smoke.map -o /build_cache/closure_smoke.elf /build_cache/closure_smoke.o -Wl,--whole-archive /build_cache/libsocketmaster.a /build_cache/libmsgq.a -Wl,--no-whole-archive /build_cache/log.capnp.o /build_cache/deprecated.capnp.o /build_cache/custom.capnp.o /build_cache/car.capnp.o $libs/libcapnp.a $libs/libkj.a -lzmq -pthread
sha256sum /build_cache/closure_smoke.elf > /build_cache/second_link.sha256
llvm-readelf -h /build_cache/closure_smoke.elf
llvm-readelf -d /build_cache/closure_smoke.elf
' > "$stage/closure_link.log" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$stage/closure_link_exit.txt"
tail -n 35 "$stage/closure_link.log"
exit "$result"
