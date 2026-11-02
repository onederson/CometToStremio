# Atualiza o Comet do A71 para a versão nova do original sem perder as nossas modificações.
# Se a reaplicação der conflito ou qualquer teste falhar, volta sozinho para a versão anterior.
#   .\scripts\update_comet.ps1 -Check     # só mostra se há versão nova
#   .\scripts\update_comet.ps1            # atualiza, reinicia, testa (smoke + regress) e confirma ou desfaz
param(
  [switch]$Check,
  [string]$Ref = 'origin/main',
  [string]$Device = '192.168.3.44:5555'
)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$sh = Join-Path $here 'update_comet.sh'
$txt = [IO.File]::ReadAllText($sh) -replace "`r", ''
$tmp = Join-Path $env:TEMP 'update_comet.sh'
[IO.File]::WriteAllText($tmp, $txt, (New-Object Text.UTF8Encoding $false))
adb -s $Device push $tmp /data/local/tmp/update_comet.sh | Out-Null
& "$here\a71.ps1" -Device $Device 'mkdir -p /data/debian/opt/comet-tools && mv /data/local/tmp/update_comet.sh /data/debian/opt/comet-tools/update_comet.sh && chmod 755 /data/debian/opt/comet-tools/update_comet.sh' | Out-Null

function Run-Upd([string]$verb) {
  $out = & "$here\a71.ps1" -Device $Device -Chroot "sh /opt/comet-tools/update_comet.sh $verb $Ref" 2>&1
  $out | Where-Object { $_ -notmatch 'file pushed' } | ForEach-Object { Write-Host "  $_" }
  return ($out -join "`n")
}

if ($Check) { Run-Upd 'check' | Out-Null; exit 0 }

Write-Host '== 1/4 Baixando a versão nova e reaplicando as modificações'
$prep = Run-Upd 'prepare'
if ($prep -match 'JA_ATUALIZADO') { Write-Host 'Já está na versão mais nova do original. Nada a fazer.' -ForegroundColor Green; exit 0 }
if ($prep -notmatch 'PREPARADO') { Write-Host 'Atualização cancelada (o Comet continua na versão anterior).' -ForegroundColor Yellow; exit 1 }

Write-Host '== 2/4 Reiniciando o Comet'
& "$here\a71.ps1" -Device $Device 'pkill -f "python -m comet.main"' | Out-Null
$up = & "$here\a71.ps1" -Device $Device -Chroot 'sleep 15; for i in $(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:8000/manifest.json && echo UP && break; sleep 3; done' 2>&1
if (($up -join '') -notmatch 'UP') {
  Write-Host 'O Comet não subiu com a versão nova: desfazendo.' -ForegroundColor Red
  Run-Upd 'rollback' | Out-Null
  & "$here\a71.ps1" -Device $Device 'pkill -f "python -m comet.main"' | Out-Null
  exit 1
}

Write-Host '== 3/4 Testes (smoke + regressão)'
& "$here\smoke.ps1" -Device $Device
$smokeOk = ($LASTEXITCODE -eq 0)
$regOk = $false
if ($smokeOk) { & "$here\regress.ps1" -Device $Device; $regOk = ($LASTEXITCODE -eq 0) }

if ($smokeOk -and $regOk) {
  Run-Upd 'finish' | Out-Null
  Write-Host '== 4/4 ATUALIZADO e testado. Regenere o patch (comet-patches) e faça o commit.' -ForegroundColor Green
  exit 0
}
Write-Host '== 4/4 Testes falharam: voltando para a versão anterior.' -ForegroundColor Red
Run-Upd 'rollback' | Out-Null
& "$here\a71.ps1" -Device $Device 'pkill -f "python -m comet.main"' | Out-Null
exit 1
