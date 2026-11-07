# Bounded, passive cereal subscription. Default prints the plan; no device files are copied.
param([switch]$RunReadOnly, [string]$HostAlias = 'comma4',
      [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_openpilot_dev")
if ($HostAlias -notmatch '^[A-Za-z0-9_.-]{1,64}$' -or $HostAlias.StartsWith('-')) {
  throw 'Use a configured SSH alias.'
}
$Remote = @'
set -u
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH=/data/openpilot
export PYTHONDONTWRITEBYTECODE PYTHONNOUSERSITE PYTHONPATH
timeout 9s /usr/local/venv/bin/python3 -B - <<'PY'
import json, sys, time
from openpilot.cereal import messaging
names = ('pandaStates', 'carState', 'controlsState')
start = time.monotonic()
counts = {name: 0 for name in names}
alive = {name: False for name in names}
ignition_true = False
motion = False
engaged = False
errors = []
try:
  sm = messaging.SubMaster(list(names))
  while time.monotonic() - start < 5:
    sm.update(250)
    for name in names:
      if sm.updated[name]:
        counts[name] += 1
        alive[name] = bool(sm.alive[name])
    if sm.updated['pandaStates']:
      try:
        ignition_true |= any(p.ignitionCan or p.ignitionLine for p in sm['pandaStates'])
      except Exception as exc:
        errors.append('panda_state_parse:' + type(exc).__name__)
    if sm.updated['carState']:
      try:
        motion |= sm['carState'].vEgo != 0
      except Exception as exc:
        errors.append('car_state_parse:' + type(exc).__name__)
    if sm.updated['controlsState']:
      try:
        engaged |= bool(sm['controlsState'].enabled)
      except Exception as exc:
        errors.append('controls_state_parse:' + type(exc).__name__)
except Exception as exc:
  errors.append('subscription:' + type(exc).__name__ + ':' + str(exc)[:120])
print(json.dumps({'duration_seconds': round(time.monotonic()-start, 3),
  'updates': counts, 'alive_last_seen': alive, 'ignition_any_true': ignition_true,
  'motion_any': motion, 'engaged_any': engaged, 'errors': errors,
  'decision': 'READ_ONLY_SNAPSHOT_NOT_PARKED_PROOF'}))
PY
printf 'probe_complete=1\n'
'@
if (-not $RunReadOnly) {
  Write-Output 'PLAN ONLY: bounded passive cereal subscriber, no device file write.'
  Write-Output $Remote
  exit 0
}
if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) { throw 'Configured SSH identity file not found' }
$Remote | & ssh -T -i $IdentityFile -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 -o ConnectionAttempts=1 $HostAlias 'sh -s'
if ($LASTEXITCODE -ne 0) { throw "Read-only SSH failed with exit code $LASTEXITCODE" }
