# Optional Windows authenticated, read-only SSH diagnostic. Default: print plan only.
param([switch]$RunReadOnly, [string]$HostAlias = 'comma')
if ($HostAlias -notmatch '^[A-Za-z0-9_.-]{1,64}$' -or $HostAlias.StartsWith('-')) {
  throw 'Use a configured SSH alias.'
}
$Remote = @'
set -u
GIT_OPTIONAL_LOCKS=0; export GIT_OPTIONAL_LOCKS
printf 'model='; tr -d '\000\n' </proc/device-tree/model 2>/dev/null || :; printf '\n'
printf 'arch='; uname -m 2>/dev/null || :
printf 'agnos='; cat /VERSION 2>/dev/null || :
printf 'gpu_node='; if [ -c /dev/kgsl-3d0 ]; then printf 'yes\n'; else printf 'no\n'; fi
for path in /sys/class/kgsl/kgsl-3d0/gpu_model /sys/class/kgsl/kgsl-3d0/gpu_id /sys/class/kgsl/kgsl-3d0/device/uevent /proc/driver/kgsl-3d0/gpuclk; do
  if [ -r "$path" ]; then printf 'identity_path=%s\n' "$path"; head -n 12 "$path" 2>/dev/null || :; fi
done
for path in /usr/lib/aarch64-linux-gnu/libOpenCL.so* /usr/lib/aarch64-linux-gnu/libEGL.so* /usr/lib/aarch64-linux-gnu/libGLESv2.so*; do
  if [ -e "$path" ]; then printf 'userspace_path=%s\n' "$path"; readlink -f "$path" 2>/dev/null || :; fi
done
for path in /sys/class/thermal/thermal_zone*/temp; do
  if [ -r "$path" ]; then
    type=$(cat "${path%/temp}/type" 2>/dev/null || :)
    value=$(cat "$path" 2>/dev/null || :)
    case "$type" in *cpu*|*CPU*|*gpu*|*GPU*|*lmh*|*limit*|*virtual*)
      printf 'thermal=%s|%s|%s\n' "$type" "$value" "$path";; esac
  fi
done
printf 'data_available_kib='; df -Pk /data 2>/dev/null | awk 'NR==2 {print $4}'
printf 'tmp_available_kib='; df -Pk /tmp 2>/dev/null | awk 'NR==2 {print $4}'
printf 'mem_available_kib='; awk '/^MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null
for path in /usr/local/venv/bin/python3 /usr/local/venv/bin/scons /usr/bin/clang /usr/bin/clang++ /usr/bin/capnpc /usr/bin/taskset /usr/bin/timeout; do
  if [ -x "$path" ]; then printf 'tool=%s\n' "$path"; fi
done
printf 'installed_branch='; git -C /data/openpilot branch --show-current 2>/dev/null || :
printf 'installed_sha='; git -C /data/openpilot rev-parse HEAD 2>/dev/null || :
'@
if (-not $RunReadOnly) {
  Write-Output 'PLAN ONLY: authenticated SSH read-only observations; no device files changed.'
  Write-Output $Remote
  exit 0
}
$Remote | & ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 -o ConnectionAttempts=1 $HostAlias 'sh -s'
if ($LASTEXITCODE -ne 0) { throw "Read-only SSH failed with exit code $LASTEXITCODE" }
