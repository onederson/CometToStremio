# Reaplica o patch Python "PT-BR primeiro" no Comet (/opt/comet) e reinicia o processo.
# Uso: .\scripts\deploy_patches.ps1
param(
  [string]$Device = '192.168.3.44:5555'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$patchFile = Join-Path $root 'comet-patches\ptbr-first.patch'

# Garante que o patch local esta em LF puro (zero CR)
if (([IO.File]::ReadAllBytes($patchFile) -eq 13).Count -gt 0) {
  throw "ERRO: comet-patches\ptbr-first.patch contem caracteres CR (\r). Converta para LF antes de aplicar."
}

# Envia um unico arquivo com caminho completo (evita bug do adb push no Windows)
adb -s $Device push $patchFile /data/local/tmp/ptbr-first.patch

# Copia para o chroot, aplica se ainda nao estiver aplicado, limpa temporarios e reinicia o Comet
& "$PSScriptRoot\a71.ps1" -Device $Device @'
set -e
cp /data/local/tmp/ptbr-first.patch /data/debian/tmp/ptbr-first.patch
rm -f /data/local/tmp/ptbr-first.patch
sh /data/comet/chroot.sh -c '
  set -e
  trap "rm -f /tmp/ptbr-first.patch" EXIT
  if git -C /opt/comet apply --reverse --check /tmp/ptbr-first.patch >/dev/null 2>&1; then
    echo "Patch ptbr-first.patch ja estava aplicado (pulando)."
  else
    git -C /opt/comet apply --check /tmp/ptbr-first.patch
    git -C /opt/comet apply /tmp/ptbr-first.patch
    echo "Patch ptbr-first.patch aplicado com sucesso."
  fi
'
pkill -f "python -m comet.main" || true
'@
if ($LASTEXITCODE -ne 0) {
  throw "ERRO ao aplicar ptbr-first.patch no A71."
}

Write-Host "Concluido! Executando smoke test..."
& "$PSScriptRoot\smoke.ps1" -Device $Device

Write-Host "Executando testes de regressao..."
& "$PSScriptRoot\regress.ps1" -Device $Device
if ($LASTEXITCODE -ne 0) {
  $failedStr = ""
  try {
    $lastJsonRaw = adb -s $Device shell "cat /data/debian/opt/comet/data/regress_last.json 2>/dev/null"
    if ($lastJsonRaw) {
      $lastData = $lastJsonRaw | ConvertFrom-Json
      $failedList = @($lastData.tests | Where-Object { $_.status -eq 'FAIL' } | ForEach-Object { $_.name })
      if ($failedList.Count -gt 0) {
        $failedStr = $failedList -join ', '
      }
    }
  } catch {}
  if (-not $failedStr) {
    $failedStr = "verifique os logs"
  }
  Write-Host "REGRESSÃO: $failedStr" -ForegroundColor Red
  exit 1
}
