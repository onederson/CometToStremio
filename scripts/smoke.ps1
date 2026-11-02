# Executa o smoke test do Comet no A71 e exibe o resultado das checagens.
# Uso: .\scripts\smoke.ps1
param(
  [string]$Device = '192.168.3.44:5555',
  [switch]$ForceFail,
  [switch]$FakeChanged
)

$ErrorActionPreference = 'Stop'

$envForce = if ($ForceFail -or ($env:SMOKE_FORCE_FAIL -eq '1')) { '1' } else { '0' }
$envFake  = if ($FakeChanged -or ($env:SMOKE_FAKE_CHANGED -eq '1')) { '1' } else { '0' }

# Garante que scripts/smoke.py esta instalado em /data/debian/opt/comet-tools/smoke.py
$localSmoke = Join-Path $PSScriptRoot 'smoke.py'
if (Test-Path $localSmoke) {
  adb -s $Device push $localSmoke /data/local/tmp/smoke.py | Out-Null
  & "$PSScriptRoot\a71.ps1" -Device $Device @'
mkdir -p /data/debian/opt/comet-tools
cp /data/local/tmp/smoke.py /data/debian/opt/comet-tools/smoke.py
chmod 755 /data/debian/opt/comet-tools/smoke.py
rm -f /data/local/tmp/smoke.py
'@ | Out-Null
}

$cmd = 'export SMOKE_FORCE_FAIL=' + $envForce + '; export SMOKE_FAKE_CHANGED=' + $envFake + @'

if [ -f /data/debian/opt/comet/data/smoke.disable ]; then
  echo "smoke.disable presente (pulando smoke)"
  exit 0
fi

touch /data/debian/var/tmp/comet.log
grep -q " /data/debian/var/tmp/comet.log " /proc/mounts || mount -o bind /data/comet/comet.log /data/debian/var/tmp/comet.log 2>/dev/null || true
offset=$(stat -c %s /data/comet/comet.log 2>/dev/null || echo 0)

sh /data/comet/chroot.sh -c "SMOKE_FORCE_FAIL=$SMOKE_FORCE_FAIL SMOKE_FAKE_CHANGED=$SMOKE_FAKE_CHANGED /opt/comet/.venv/bin/python /opt/comet-tools/smoke.py --log-file /var/tmp/comet.log --log-offset $offset"
res=$?
tail -c +$((offset + 1)) /data/comet/comet.log > /data/debian/var/tmp/smoke_log.txt 2>/dev/null || true
exit $res
'@

& "$PSScriptRoot\a71.ps1" -Device $Device $cmd
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
