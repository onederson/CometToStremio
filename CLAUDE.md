# Modo de trabalho

> **🧊 Congelado em 09/11/2026.** O trabalho continua só no Nuvio, na pasta `../NUVIO` (repo `onederson/NuvioComet`). Não mexa no A71 a partir daqui: ele roda a versão do Nuvio. Para voltar ao Stremio, veja a Seção 6 do `HANDOFF.md` do NUVIO (backup em `backups/stremio-20261109/`, tag `stremio-20261109`).

**Desde 02/11/2026 o usuário pediu: Claude implementa tudo diretamente.** Não delegar mais ao `agy` (CLI do Antigravity).
Quando a tarefa tiver partes independentes, Claude pode abrir subagentes (Agent tool) e trabalhar em paralelo; o usuário autorizou o gasto de tokens.

## Fluxo
1. Planejar em `.orquestra/tarefa-<letra>.md` quando a tarefa for grande (registro do que foi pedido e de como verificar).
2. Implementar direto no A71 (`.\scripts\a71.ps1`, scripts Python com `adb push` + `mv`, LF).
3. Verificar: `py_compile`, reiniciar, `.\scripts\smoke.ps1` e `.\scripts\regress.ps1`.
4. Regenerar `comet-patches/ptbr-first.patch` e fazer commit/push quando o usuário pedir ou ao fechar uma leva aprovada.

## Cuidados
- Enquanto se mexe no Comet, a restauração automática do smoke pode desfazer trabalho: crie `data/smoke.disable` no A71 durante o trabalho e apague ao terminar.
- Dois processos mexendo no mesmo arquivo do A71 se atropelam: subagentes devem trabalhar em arquivos diferentes.
- Histórico: até 02/11/2026 o fluxo era delegar ao `agy` (gemini flash) e revisar; as especificações antigas estão em `.orquestra/`.
