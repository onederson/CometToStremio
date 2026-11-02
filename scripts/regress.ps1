# Executa os testes de regressao do Comet no A71.
# Uso: .\scripts\regress.ps1 [-Only <nome>] [-SaveBaseline] [-SkipUnit]
param(
  [string]$Device = '192.168.3.44:5555',
  [string[]]$Only = @(),
  [switch]$SaveBaseline,
  [switch]$SkipUnit
)

$ErrorActionPreference = 'Stop'

# Garante que scripts/regress.py esta instalado em /data/debian/opt/comet-tools/regress.py
$localRegress = Join-Path $PSScriptRoot 'regress.py'
if (Test-Path $localRegress) {
  adb -s $Device push $localRegress /data/local/tmp/regress.py | Out-Null
  & "$PSScriptRoot\a71.ps1" -Device $Device @'
mkdir -p /data/debian/opt/comet-tools
cp /data/local/tmp/regress.py /data/debian/opt/comet-tools/regress.py
chmod 755 /data/debian/opt/comet-tools/regress.py
rm -f /data/local/tmp/regress.py
'@ | Out-Null
}

$pyArgs = @()
if ($Only) {
  $onlyVal = ($Only -join ',')
  $pyArgs += "--only $onlyVal"
}
if ($SaveBaseline) {
  $pyArgs += "--save-baseline"
}
if ($SkipUnit) {
  $pyArgs += "--skip-unit"
}
$pyArgsStr = $pyArgs -join ' '

$envSelftest = if ($env:REGRESS_SELFTEST -eq '1') { '1' } else { '0' }

$cmd = @"
export REGRESS_SELFTEST=$envSelftest

touch /data/debian/var/tmp/comet.log
grep -q " /data/debian/var/tmp/comet.log " /proc/mounts || mount -o bind /data/comet/comet.log /data/debian/var/tmp/comet.log 2>/dev/null || true
offset=`$(stat -c %s /data/comet/comet.log 2>/dev/null || echo 0)

sh /data/comet/chroot.sh -c "REGRESS_SELFTEST=`$REGRESS_SELFTEST /opt/comet/.venv/bin/python /opt/comet-tools/regress.py --log-file /var/tmp/comet.log --log-offset `$offset $pyArgsStr"
res=`$?
exit `$res
"@

& "$PSScriptRoot\a71.ps1" -Device $Device $cmd
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
