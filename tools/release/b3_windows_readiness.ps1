# Read-only B3 device observation kit. Default inspects a local saved transcript.
# -RunReadOnly explicitly requests a fresh authenticated SSH read from Windows.
param([string]$SnapshotPath,
      [switch]$RunReadOnly,
      [string]$HostAlias = 'comma4',
      [string]$IdentityFile)
$ErrorActionPreference = 'Stop'
$Expected = '21f732825d9d61580e44e7c33e67cd9f8f4904884e84e96f284641529f13740d'
if (-not $RunReadOnly) {
  if (-not $SnapshotPath) {
    Write-Output 'READ_ONLY_OFFLINE: supply -SnapshotPath to hash and inspect the saved transcript.'
    Write-Output 'DEVICE_COMPILE_BLOCKED_UNVERIFIED_PARKED_OR_POWER_OR_RESOURCE'
    exit 0
  }
  $got = (Get-FileHash -LiteralPath $SnapshotPath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($got -ne $Expected) { throw 'Passive transcript SHA-256 mismatch' }
  $raw = Get-Content -LiteralPath $SnapshotPath -Raw
  foreach ($key in @('AGNOS_VERSION','ARCH','ACTIVE_COMMIT','ONROAD_FLAG','OFFROAD_FLAG','IGNITION_FLAG')) {
    $values = [regex]::Matches($raw, "(?m)^$key=([^`r`n]*)`r?$")
    if ($values.Count -ne 1) { Write-Output "$key=UNKNOWN_OR_AMBIGUOUS" }
    else { Write-Output ("{0}={1}" -f $key, $values[0].Groups[1].Value) }
  }
  Write-Output 'SNAPSHOT_SHA256_VERIFIED; DEVICE_COMPILE_BLOCKED_UNVERIFIED_PARKED_OR_POWER_OR_RESOURCE'
  exit 0
}
if ($HostAlias -notmatch '^[A-Za-z0-9_.-]{1,64}$' -or $HostAlias.StartsWith('-')) { throw 'Use a configured SSH alias.' }
if (-not $IdentityFile -or -not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) { throw 'Supply an existing SSH identity with -IdentityFile.' }
$Remote = @'
set -u
printf 'AGNOS_VERSION='; cat /VERSION 2>/dev/null || :
printf 'ARCH='; uname -m 2>/dev/null || :
printf 'ACTIVE_COMMIT='; GIT_OPTIONAL_LOCKS=0 git -C /data/openpilot rev-parse HEAD 2>/dev/null || :
printf 'OFFROAD_FLAG=UNKNOWN\nONROAD_FLAG=UNKNOWN\nIGNITION_FLAG=UNKNOWN\n'
printf 'DATA_FREE_BYTES='; df -B1 /data 2>/dev/null | awk 'NR==2 {print $4}'
printf 'MEM_AVAILABLE_KB='; awk '/^MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null
for supply in usb dc pc_port; do
  path="/sys/class/power_supply/$supply/online"
  if [ -r "$path" ]; then printf '%s=' "$path"; cat "$path" 2>/dev/null || :; fi
done
if [ -c /dev/kgsl-3d0 ]; then printf 'KGSL_NODE=present\n'; else printf 'KGSL_NODE=absent\n'; fi
for zone in /sys/class/thermal/thermal_zone*/type; do
  if [ -r "$zone" ]; then type=$(cat "$zone" 2>/dev/null || :); value=$(cat "${zone%/type}/temp" 2>/dev/null || :); printf 'THERMAL_TYPE_VALUE=%s:%s\n' "$type" "$value"; fi
done
'@
# Strict host key checking is mandatory; stdout is the only script output.
$Remote | & ssh -T -i $IdentityFile -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 -o ConnectionAttempts=1 $HostAlias 'sh -s'
if ($LASTEXITCODE -ne 0) { throw "Read-only SSH exited $LASTEXITCODE" }
Write-Output 'READ_ONLY_SNAPSHOT_ONLY; NEVER A DEVICE COMPILE QUALIFICATION'
