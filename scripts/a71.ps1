# Helper: roda um comando no A71 como root (ou dentro do chroot Debian) sem dor de cabeca com aspas.
#   .\scripts\a71.ps1 'uptime; df -h /data'
#   .\scripts\a71.ps1 -Chroot 'apt-get update && python3 --version'
param(
  [Parameter(Mandatory = $true, Position = 0)][string]$Cmd,
  [switch]$Chroot,
  [string]$Device = '192.168.3.44:5555'
)
$tmp = Join-Path $env:TEMP '_a71cmd.sh'
[IO.File]::WriteAllText($tmp, ($Cmd -replace "`r", '') + "`n", (New-Object Text.UTF8Encoding $false))
adb -s $Device push $tmp /data/local/tmp/_cmd.sh | Out-Null
if ($Chroot) {
  adb -s $Device shell "su -c 'cp /data/local/tmp/_cmd.sh /data/debian/tmp/_cmd.sh && sh /data/comet/chroot.sh /tmp/_cmd.sh'"
} else {
  adb -s $Device shell "su -c 'sh /data/local/tmp/_cmd.sh'"
}

