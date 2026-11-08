#!/usr/bin/env bash
set -euo pipefail
source_root=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/source_4b25263
rootfs=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs
out=/mnt/commadrive/MVL_C6_NATIVE_STAGE_20261108
image=sha256:3cc10a4b24fcb74e0f73a9768897e044d28e4e699794ee41c4ca7dda475bbd95
test "$(docker image inspect --format '{{.Id}}' starpilot-larch64-builder:latest)" = "$image"
test "$(cat "$rootfs/VERSION")" = 19.9
test "$(git -C "$source_root" rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb
mkdir -p "$out"
set +e
timeout 300s docker run --rm --platform linux/arm64 --network none --read-only --memory 1g --cpus 1 --pids-limit 64 --security-opt no-new-privileges --tmpfs /agnos/tmp:rw,size=256m --mount type=bind,src="$rootfs",dst=/agnos,readonly --mount type=bind,src="$source_root",dst=/agnos/src,readonly --mount type=bind,src="$out",dst=/agnos/build_cache "$image" chroot --userspec=1000:1000 /agnos /usr/bin/env PATH=/usr/local/venv/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 /bin/sh -c 'set -eu; cd /src; test "$(cat /VERSION)" = 19.9; uname -m; mkdir -p /build_cache/openpilot/cereal; /usr/local/venv/bin/python3 openpilot/cereal/services.py > /build_cache/openpilot/cereal/services.h; clang++ --version | head -n 1; clang++ -g -fPIC -pipe -O2 -Wunused -Werror -Wshadow -Wno-unknown-warning-option -Wno-inconsistent-missing-override -Wno-c99-designator -Wno-reorder-init-list -Wno-vla-cxx-extension -std=c++1z -D__COMMA_HARDWARE__ -mcpu=cortex-a57 -I/build_cache -I/usr/local/venv/lib/python3.12/site-packages/capnproto/install/include -I/src/openpilot -I/src/msgq_repo -I/src/opendbc_repo -I/src/openpilot/cereal/gen/cpp -I/src -c /src/openpilot/cereal/messaging/socketmaster.cc -o /build_cache/socketmaster.o; llvm-ar rcs /build_cache/libsocketmaster.a /build_cache/socketmaster.o' > "$out/socketmaster_build.log" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$out/socketmaster_exit.txt"
tail -n 15 "$out/socketmaster_build.log"
exit "$result"
