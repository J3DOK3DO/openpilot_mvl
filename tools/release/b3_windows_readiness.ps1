# Read-only B3 device observation kit. Offline mode inspects one pinned local buffer.
# -RunReadOnly explicitly requests a fresh authenticated SSH read from Windows.
param([string]$SnapshotPath,
      [switch]$RunReadOnly,
      [string]$HostAlias = 'comma4',
      [string]$IdentityFile)
$ErrorActionPreference = 'Stop'
$Expected = '21f732825d9d61580e44e7c33e67cd9f8f4904884e84e96f284641529f13740d'
$Blocked = 'DEVICE_COMPILE_BLOCKED_UNVERIFIED_PARKED_OR_POWER_OR_RESOURCE'

try {
  if (-not $RunReadOnly) {
    if (-not $SnapshotPath) {
      Write-Output 'READ_ONLY_OFFLINE: supply -SnapshotPath to inspect the pinned transcript.'
      Write-Output $Blocked
      exit 2
    }
    # Open the leaf without following reparse points. Inspect the opened handle,
    # including its final path, then hash and parse only bytes from that handle.
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class B3PinnedRead {
  [StructLayout(LayoutKind.Sequential)]
  public struct FileInfo {
    public uint Attributes, CreationLow, CreationHigh, AccessLow, AccessHigh;
    public uint WriteLow, WriteHigh, VolumeSerial, SizeHigh, SizeLow;
    public uint Links, IndexHigh, IndexLow;
  }
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern SafeFileHandle CreateFile(string name, uint access, uint share,
    IntPtr security, uint disposition, uint flags, IntPtr templateFile);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool GetFileInformationByHandle(SafeFileHandle handle, out FileInfo info);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern uint GetFileType(SafeFileHandle handle);
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  static extern uint GetFinalPathNameByHandle(SafeFileHandle handle, System.Text.StringBuilder path,
    uint length, uint flags);
  public static byte[] Read(string name) {
    const int max = 1048576;
    string full = Path.GetFullPath(name);
    string walk = full;
    while (true) {
      if ((File.GetAttributes(walk) & FileAttributes.ReparsePoint) != 0)
        throw new IOException("Reparse point in snapshot path");
      string parent = Path.GetDirectoryName(walk);
      if (String.IsNullOrEmpty(parent) || parent == walk) break;
      walk = parent;
    }
    // FILE_FLAG_OPEN_REPARSE_POINT prevents a swapped leaf link from being followed.
    using (SafeFileHandle handle = CreateFile(full, 0x80000000, 1, IntPtr.Zero, 3,
                                             0x00200000, IntPtr.Zero)) {
      if (handle.IsInvalid) throw new IOException("Cannot open snapshot");
      FileInfo info;
      if (!GetFileInformationByHandle(handle, out info) || GetFileType(handle) != 1 ||
          (info.Attributes & 0x410) != 0 || info.SizeHigh != 0 || info.SizeLow > max)
        throw new IOException("Snapshot is not a bounded regular file");
      var finalPath = new System.Text.StringBuilder(32768);
      uint n = GetFinalPathNameByHandle(handle, finalPath, (uint)finalPath.Capacity, 0);
      if (n == 0 || n >= finalPath.Capacity) throw new IOException("Cannot verify snapshot path");
      string actual = finalPath.ToString();
      if (actual.StartsWith(@"\\?\UNC\", StringComparison.OrdinalIgnoreCase))
        actual = @"\\" + actual.Substring(8);
      else if (actual.StartsWith(@"\\?\", StringComparison.OrdinalIgnoreCase))
        actual = actual.Substring(4);
      if (!String.Equals(full, actual, StringComparison.OrdinalIgnoreCase))
        throw new IOException("Snapshot path resolved through a reparse point");
      using (var stream = new FileStream(handle, FileAccess.Read, 4096, false)) {
        using (var output = new MemoryStream()) {
          byte[] chunk = new byte[65536];
          int count;
          while ((count = stream.Read(chunk, 0, Math.Min(chunk.Length, max + 1 - (int)output.Length))) > 0) {
            output.Write(chunk, 0, count);
            if (output.Length > max) throw new IOException("Snapshot grew beyond 1 MiB");
          }
          return output.ToArray();
        }
      }
    }
  }
}
'@
    [byte[]]$bytes = [B3PinnedRead]::Read($SnapshotPath)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try { $got = [BitConverter]::ToString($hasher.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant() }
    finally { $hasher.Dispose() }
    if ($got -ne $Expected) { throw 'Passive transcript SHA-256 mismatch' }
    $utf8 = New-Object System.Text.UTF8Encoding($false, $true)
    $offset = 0
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) { $offset = 3 }
    $raw = $utf8.GetString($bytes, $offset, $bytes.Length - $offset)
    foreach ($key in @('AGNOS_VERSION','ARCH','ACTIVE_COMMIT','ONROAD_FLAG','OFFROAD_FLAG','IGNITION_FLAG')) {
      $values = [regex]::Matches($raw, "(?m)^$key=([^`r`n]*)`r?$")
      if ($values.Count -gt 1) { throw "Ambiguous $key in passive transcript" }
      if ($values.Count -ne 1) { Write-Output "$key=UNKNOWN" }
      else {
        $value = $values[0].Groups[1].Value.Trim()
        if ($key -in @('ONROAD_FLAG','OFFROAD_FLAG','IGNITION_FLAG') -and $value -notin @('0','1','UNKNOWN')) {
          $value = 'UNKNOWN'
        }
        Write-Output ("{0}={1}" -f $key, $value)
      }
    }
    Write-Output 'SNAPSHOT_SHA256_VERIFIED'
    Write-Output $Blocked
    exit 2
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
  # Strict host key checking is mandatory; no write or compile command is sent.
  $Remote | & ssh -T -i $IdentityFile -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 -o ConnectionAttempts=1 $HostAlias 'sh -s'
  if ($LASTEXITCODE -ne 0) { throw "Read-only SSH exited $LASTEXITCODE" }
  Write-Output 'READ_ONLY_SNAPSHOT_ONLY'
  Write-Output $Blocked
  exit 2
} catch {
  Write-Output ('READINESS_ERROR: ' + $_.Exception.Message)
  Write-Output $Blocked
  exit 2
}
