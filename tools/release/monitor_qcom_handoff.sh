#!/usr/bin/env sh
# Read-only bounded capacity and thermal sampler for an authorized isolated build.
set -eu
samples=${1:-180}
case "$samples" in ''|*[!0-9]*) echo 'samples must be an integer 1..180' >&2; exit 2;; esac
if [ "$samples" -lt 1 ] || [ "$samples" -gt 180 ]; then echo 'samples must be 1..180' >&2; exit 2; fi
count=0
while [ "$count" -lt "$samples" ]; do
  date -u '+%Y-%m-%dT%H:%M:%SZ'
  uname -m
  df -Pk /data /tmp 2>/dev/null || df -Pk /
  cat /proc/loadavg
  sed -n '1,6p' /proc/meminfo
  for zone in /sys/class/thermal/thermal_zone*/temp; do
    [ -r "$zone" ] && { printf '%s ' "$zone"; cat "$zone"; }
  done
  count=$((count + 1))
  [ "$count" -eq "$samples" ] || sleep 5
done
