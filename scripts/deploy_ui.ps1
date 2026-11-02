# Implanta a interface traduzida (/configure) do Comet no Galaxy A71 e reinicia o processo.
# Uso: .\scripts\deploy_ui.ps1
param(
  [string]$Device = '192.168.3.44:5555'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$uiFile = Join-Path $root 'comet-ui\index.html'

# Garante que o arquivo local esta em LF puro (zero CR) antes de enviar
if (([IO.File]::ReadAllBytes($uiFile) -eq 13).Count -gt 0) {
  throw "ERRO: comet-ui\index.html contem caracteres CR (\r). Converta para LF antes de implantar."
}

# Envia um unico arquivo especificando o caminho completo (evita bug do adb push no Windows)
adb -s $Device push $uiFile /data/local/tmp/index.html

# Faz backup unico do original (.orig), aplica o template traduzido, ajusta permissao, limpa tmp e reinicia o Comet
& "$PSScriptRoot\a71.ps1" -Device $Device @'
TPL=/data/debian/opt/comet/comet/templates/index.html
[ -f "${TPL}.orig" ] || cp "$TPL" "${TPL}.orig"
cp /data/local/tmp/index.html "$TPL"
chmod 644 "$TPL"
rm -f /data/local/tmp/index.html
pkill -f "python -m comet.main" || true
'@

Write-Host "Template aplicado! Executando smoke test..."
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
