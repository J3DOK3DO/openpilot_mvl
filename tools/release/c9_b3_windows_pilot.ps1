param(
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9._@-]+$')][string]$SshTarget,
  [Parameter(Mandatory=$true)][ValidatePattern('^/data/mvl-builds/[0-9a-f]{40}/[A-Za-z0-9_./-]+$')][string]$Source,
  [Parameter(Mandatory=$true)][ValidatePattern('^/data/mvl-builds/[0-9a-f]{40}/[A-Za-z0-9_./-]+$')][string]$Scratch,
  [Parameter(Mandatory=$true)][ValidatePattern('^/data/mvl-builds/[0-9a-f]{40}/[A-Za-z0-9_./-]+$')][string]$Kit,
  [switch]$Execute,
  [string]$Gate,
  [string]$Monitor,
  [string]$Log
)
$ErrorActionPreference = 'Stop'
$sourceCommit = '4b25263e8c1ccc7a72dc5fa5c08b7eacc70257fb'
if (-not $Source.StartsWith("/data/mvl-builds/$sourceCommit/") -or -not $Scratch.StartsWith("/data/mvl-builds/$sourceCommit/") -or -not $Kit.StartsWith("/data/mvl-builds/$sourceCommit/")) { throw 'Wrong isolated source root' }
foreach ($value in @($Source, $Scratch, $Kit)) {
  if ($value -match '(^|/)\.\.(/|$)') { throw 'Path traversal is forbidden' }
}
$argv = @('env', "PYTHONPATH=$Kit", 'python3', '-m', 'tools.release.c9_b3_pilot', '--source', $Source, '--scratch', $Scratch)
if ($Execute) {
  foreach ($value in @($Gate, $Monitor, $Log)) {
    if ($value -notmatch '^/data/mvl-builds/[0-9a-f]{40}/[A-Za-z0-9_./-]+$' -or -not $value.StartsWith("/data/mvl-builds/$sourceCommit/")) { throw 'Execution paths must be isolated' }
    if ($value -match '(^|/)\.\.(/|$)') { throw 'Path traversal is forbidden' }
  }
  $argv += @('--execute', '--gate', $Gate, '--monitor', $Monitor, '--log', $Log)
}
& ssh -o BatchMode=yes -o ConnectTimeout=10 -- $SshTarget ($argv -join ' ')
exit $LASTEXITCODE
