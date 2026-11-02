# Helper: roda um comando no A71 como root (ou dentro do chroot Debian) sem dor de cabeca com aspas.
#   .\scripts\a71.ps1 'uptime; df -h /data'
#   .\scripts\a71.ps1 -Chroot 'apt-get update && python3 --version'
# Cada execucao usa um arquivo temporario proprio: dois processos (ex.: Claude e agy)
# podem rodar ao mesmo tempo sem um sobrescrever o comando do outro.
param(
  [Parameter(Mandatory = $true, Position = 0)][string]$Cmd,
  [switch]$Chroot,
  [string]$Device = '192.168.3.44:5555'
)
$id = [guid]::NewGuid().ToString('N').Substring(0, 12)
$name = "_cmd_$id.sh"
$tmp = Join-Path $env:TEMP "_a71cmd_$id.sh"
[IO.File]::WriteAllText($tmp, ($Cmd -replace "`r", '') + "`n", (New-Object Text.UTF8Encoding $false))
adb -s $Device push $tmp "/data/local/tmp/$name" | Out-Null
[IO.File]::Delete($tmp)
if ($Chroot) {
  adb -s $Device shell "su -c 'cp /data/local/tmp/$name /data/debian/tmp/$name && rm -f /data/local/tmp/$name && sh /data/comet/chroot.sh /tmp/$name; rc=`$?; rm -f /data/debian/tmp/$name; exit `$rc'"
} else {
  adb -s $Device shell "su -c 'sh /data/local/tmp/$name; rc=`$?; rm -f /data/local/tmp/$name; exit `$rc'"
}
