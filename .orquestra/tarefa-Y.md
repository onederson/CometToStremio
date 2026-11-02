# Tarefa Y: baixar no Real-Debrid, com antecedência, o próximo episódio dublado que ainda não está em cache

## Contexto
- Comet no A71, chroot, `/opt/comet`. Ao dar play num episódio, `comet/services/prefetch.py` (`trigger_prefetch_next_episode`) já faz um GET interno da lista do **próximo** episódio (`/<token>/stream/series/<imdb>:<S>:<E>.json`). Isso só ajuda quando o próximo já está em cache (⚡).
- Hoje, quando o usuário toca num stream **não cacheado** (⬇️), o `playback.py` manda o magnet para o RD (via StremThru) e responde o aviso "Baixando no Real-Debrid…". Reuse exatamente esse caminho (não duplique a lógica de adicionar magnet).
- Hashes bloqueados (451) ficam em `debrid_blocked_hashes`; o TorBox é o 2º debrid (`entry_index`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token ou links do RD/TorBox; commit; instalar pacotes; mexer no AdGuard ou no `.env`; contornar o 451 do RD (hash marcado 451 nunca vai para o RD). Nada em segundo plano (seus comandos). Comandos com timeout ≤ 300 s.

## Comportamento
1. `models.py`: `PREDOWNLOAD_NEXT_EPISODE: bool = True`, `PREDOWNLOAD_MAX_PER_DAY: int = 10`.
2. Em `prefetch.py`, depois de obter a lista do próximo episódio:
   - Se ela **já tem** algum stream `🇧🇷` com ⚡ (RD ou TorBox) → nada (log debug).
   - Senão, escolha o melhor `🇧🇷` **⬇️** (não cacheado) que **não** esteja em 451 para o serviço: preferência 1080p → 720p → 4K, tamanho ≤ 15 GB, mais seeders; RD primeiro, TorBox se o hash estiver 451 no RD.
   - Dispare o mesmo pedido que um play faria nesse stream: GET interno no `url` do stream (trocando o domínio público por `127.0.0.1:8000`), com `Range: bytes=0-1`, timeout 20 s, só para o Comet adicionar o magnet. Ignore a resposta.
   - Se não houver `🇧🇷` nenhum (nem ⬇️), não faça nada (não baixe áudio original).
3. Limites: 1 pré-download por série a cada 12 h (memória + gravação em `data/predownload.json`), no máx. `PREDOWNLOAD_MAX_PER_DAY` por dia, nunca 2 ao mesmo tempo.
4. Log: `📥 pré-download <imdb> T<S>E<E>: <serviço> <res> <tam> (<hash curto>)` e, quando pular, o motivo curto em `debug`.
5. `/status`: na seção **Playback**, linha "Pré-downloads hoje: N" com os 5 últimos (nome da série e episódio, sem link).

## Fora de escopo
Tudo o resto (fontes, ordem da lista, playback).

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token/link)
1. Ache um episódio cujo **seguinte** tem `🇧🇷` só ⬇️ (nenhum ⚡ PT) — procure em séries brasileiras/dubladas menos populares; mostre o que achou (contagem ⚡/⬇️ PT do seguinte).
2. Chame o playback do `▶ Assistir` (ou de um stream) do episódio atual; mostre a linha `📥 pré-download` no log.
3. Mostre que o magnet foi adicionado (o pedido seguinte da lista do próximo episódio, depois de alguns minutos, ou a resposta do StremThru para aquele hash em `downloading`/`downloaded`).
4. Episódio cujo seguinte já tem ⚡ PT → sem pré-download. Hash 451 no RD → vai para o TorBox ou é pulado (nunca RD).
5. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK` (em primeiro plano).

Responda em no máximo 8 linhas.
