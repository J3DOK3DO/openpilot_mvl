# Campaign 2 read-only Comma 4 filesystem and guardian capability probe.
# Default prints the remote script. -RunReadOnly requires the configured SSH identity.
param([switch]$RunReadOnly, [string]$HostAlias = 'comma4',
      [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_openpilot_dev")
if ($HostAlias -notmatch '^[A-Za-z0-9_.-]{1,64}$' -or $HostAlias.StartsWith('-')) {
  throw 'Use a configured SSH alias.'
}
$Remote = @'
set -u
GIT_OPTIONAL_LOCKS=0; PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS PYTHONDONTWRITEBYTECODE
printf 'model='; tr -d '\000\n' </proc/device-tree/model 2>/dev/null || :; printf '\n'
printf 'arch='; uname -m 2>/dev/null || :
printf 'agnos='; cat /VERSION 2>/dev/null || :
printf 'data_fs='; stat -f -c %T /data 2>/dev/null || :
printf 'data_mount='; awk '$5=="/data" {print $0}' /proc/self/mountinfo 2>/dev/null || :
printf 'data_ext4_features='; tune2fs -l /dev/sda12 2>/dev/null | awk '/^Filesystem features:/ {sub(/^Filesystem features:[[:space:]]*/, ""); print; exit}' || :
printf 'data_default_mount_options='; tune2fs -l /dev/sda12 2>/dev/null | awk '/^Default mount options:/ {sub(/^Default mount options:[[:space:]]*/, ""); print; exit}' || :
printf 'data_free_kib='; df -Pk /data 2>/dev/null | awk 'NR==2 {print $4}'
printf 'mem_available_kib='; awk '/^MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null
printf 'cgroup_controllers='; cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null || :
printf 'cgroup_subtree_control='; cat /sys/fs/cgroup/cgroup.subtree_control 2>/dev/null || :
printf 'cgroup_type='; stat -f -c %T /sys/fs/cgroup 2>/dev/null || :
printf 'self_cgroup='; cat /proc/self/cgroup 2>/dev/null || :
printf 'cgroup_memory_events='; cat /sys/fs/cgroup/memory.events 2>/dev/null | tr '\n' ',' || :; printf '\n'
printf 'kgsl_gpu_node='; if [ -c /dev/kgsl-3d0 ]; then printf 'yes\n'; else printf 'no\n'; fi
printf 'cereal_messaging='; if [ -d /data/openpilot/openpilot/cereal/messaging ]; then printf 'nested\n'; elif [ -d /data/openpilot/cereal/messaging ]; then printf 'top_level\n'; else printf 'missing\n'; fi
printf 'installed_branch='; git -C /data/openpilot branch --show-current 2>/dev/null || :
printf 'installed_sha='; git -C /data/openpilot rev-parse HEAD 2>/dev/null || :
for path in /sys/class/thermal/thermal_zone*/type; do
  if [ -r "$path" ]; then
    type=$(cat "$path" 2>/dev/null || :)
    case "$type" in *cpu*|*CPU*|*gpu*|*GPU*|*lmh*|*limit*|*virtual*)
      value=$(cat "${path%/type}/temp" 2>/dev/null || :)
      printf 'thermal=%s|%s|%s\n' "$type" "$value" "${path%/type}/temp";; esac
  fi
done
printf 'running_relevant='; ps -eo comm 2>/dev/null | grep -E '^(manager|controlsd|pandad|modeld|ui|card)(\.py)?$' | sort -u | tr '\n' ',' || :; printf '\n'
'@
if (-not $RunReadOnly) {
  Write-Output 'PLAN ONLY: strict-host-key SSH read-only inspection; no device files changed.'
  Write-Output $Remote
  exit 0
}
if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) { throw 'Configured SSH identity file not found' }
$Remote | & ssh -T -i $IdentityFile -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 -o ConnectionAttempts=1 $HostAlias 'sh -s'
if ($LASTEXITCODE -ne 0) { throw "Read-only SSH failed with exit code $LASTEXITCODE" }
