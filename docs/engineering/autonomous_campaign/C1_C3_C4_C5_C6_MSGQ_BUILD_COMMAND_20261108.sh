set -o pipefail
stage=/mnt/commadrive/MVL_C5_NATIVE_STAGE_20261108
rootfs=/mnt/commadrive/MVL_AGNOS199_NATIVE_20261106/rootfs
mkdir -p "$stage/cache"
timeout 300s docker run --rm --platform linux/arm64 --network none --read-only --memory 1g --cpus 1 --pids-limit 64 --security-opt no-new-privileges --tmpfs /agnos/tmp:rw,size=256m --mount type=bind,src="$rootfs",dst=/agnos,readonly --mount type=bind,src="$stage/source",dst=/agnos/src --mount type=bind,src="$stage/cache",dst=/agnos/build_cache --mount type=bind,src=/dev,dst=/agnos/dev,readonly --mount type=bind,src=/home/jdkd/.codex/worktrees/mvl-starpilot-manual-campaign/.git,dst=/agnos/home/jdkd/.codex/worktrees/mvl-starpilot-manual-campaign/.git,readonly --mount type=bind,src=/mnt/commadrive/MVL_STARPILOT_UBUNTU_REASSESSMENT_20261103/.git/objects,dst=/agnos/mnt/commadrive/MVL_STARPILOT_UBUNTU_REASSESSMENT_20261103/.git/objects,readonly starpilot-larch64-builder:latest chroot /agnos /usr/bin/env PATH=/usr/local/venv/bin:/usr/bin:/bin HOME=/tmp PYTHONDONTWRITEBYTECODE=1 /bin/sh -c 'git config --global --add safe.directory /src; cd /src; test "$(git rev-parse HEAD)" = 4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb; test "$(cat /VERSION)" = 19.9; uname -m; /usr/local/venv/bin/python3 -m SCons -j1 --minimal cache_dir=/build_cache msgq_repo/libmsgq.a' > "$stage/msgq_build.log" 2>&1
result=$?
printf '%s\n' "$result" > "$stage/msgq_exit.txt"
tail -n 20 "$stage/msgq_build.log"
exit "$result"
