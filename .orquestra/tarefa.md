# Tarefa E: só listar o que toca (links diretos validados) e playback que nunca trava

## Contexto
- Código do Comet: A71, chroot, `/opt/comet` (Android: `/data/debian/opt/comet`). Arquivos: `comet/services/direct_addons.py`, `comet/api/endpoints/playback.py`, `comet/api/endpoints/stream.py`, `comet/debrid/stremthru.py`, `comet/core/models.py`.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (Android root) e `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian; `git` só existe aqui).
- Enviar arquivo: `adb -s 192.168.3.44:5555 push <arq> /data/local/tmp/<nome>` (um por vez), depois `mv` para `/data/debian/...`. Tudo em **LF**. Antes de `adb pull`, `chmod 644`.
- **PROIBIDO:** imprimir chaves/tokens (a chave do RD aparece nas URLs do `comet.log`), commit, instalar pacotes, mexer no AdGuard, no `.env` ou no `resolv.conf`. **NÃO rode tarefas em segundo plano.** Passos curtos.
- O chroot agora usa DNS público (`1.1.1.1`/`9.9.9.9`). Os aparelhos da casa (TV/celular com Stremio) usam o AdGuard `192.168.3.44`, que bloqueia TLDs inteiros (`.lat`, `.top`) e responde `0.0.0.0`. Exemplo real: FrostStream → `302 dbonline.tech-cdn.top` → `302 zjo.lat` (bloqueado na casa) → `206 video/mp4` em `*.workers.dev`. No Stremio vira `Failed to connect to zjo.lat/0.0.0.0:80`.

## 1. Validar links diretos antes de listar (`direct_addons.py`)
Depois de buscar os streams dos addons diretos, valide cada `url` (em paralelo, no máx. 8 ao mesmo tempo; limite total de 7 s para o lote, o que não terminar é descartado):
- Siga os redirecionamentos **manualmente** (no máx. 6 saltos, `allow_redirects=False`), `GET` com `Range: bytes=0-1023` e `User-Agent: ExoPlayerLib/2.19.1`, timeout de 5 s por salto. Leia só o 1º KB.
- Aceito se o fim for `200`/`206` com `Content-Type` `video/*`, `application/octet-stream` ou HLS (`application/vnd.apple.mpegurl`, `application/x-mpegurl`). O resto é descartado: 4xx/5xx, HTML, timeout, IP literal que não conecta.
- **DNS da casa:** para cada host da cadeia (inclusive o final), pergunte ao DNS `settings.HOUSE_DNS` (padrão `"192.168.3.44"`; `None`/vazio desliga a checagem) com uma consulta A em UDP feita em Python puro (`asyncio` datagram, timeout de 1 s, sem pacote novo). Se a resposta for `0.0.0.0` ou não tiver IP, o host está bloqueado na casa: descarte o link e logue **uma vez por host a cada 6 h** `🚫 DNS da casa bloqueia <host> (link direto <addon>)`. Cache por host: 30 min.
- Cache do resultado por URL: 10 min em memória (válido/inválido). Log de resumo por pedido: `🌐 diretos: <n válidos>/<n total>`.
- A `url` entregue ao Stremio continua a original.

## 2. Playback nunca trava (`playback.py`, `stremthru.py`)
Hoje há pedidos de playback que levam 30 s ou mais (`TimeoutError` em `generate_download_link`, troca do 451 passando por 5 ou mais candidatos a ~2 s cada; uma levou 35,9 s). O Stremio fica carregando.
- Orçamento total por pedido de playback: `settings.PLAYBACK_BUDGET` = 15 s, contado desde a chegada do pedido. Se acabar, devolva o vídeo de erro/aviso já existente do Comet, com texto claro (`"Não ficou pronto no Real-Debrid a tempo. Tente outra opção da lista."`). Não deixe nenhum `await` passar do orçamento.
- Torrent não cacheado no RD: não espere o download. Se o RD não devolver o link na hora, responda o aviso `"Baixando no Real-Debrid (<progresso>% se souber). Tente de novo em alguns minutos ou escolha um ⚡."` em ≤ 15 s.
- Troca do 451: dentro do mesmo orçamento; os candidatos que já estão marcados como 451 (precheck/banco) são pulados sem chamar o RD.

## 3. `▶ Assistir` só aponta para o que é certo (`stream.py`)
- Candidatos do `▶ Assistir`: link direto **validado** (item 1), ou torrent ⚡ (em cache no RD) cujo hash **não** está marcado como 451. Nunca ⬇️ ou P2P. Se não houver candidato, não crie o `▶ Assistir`.
- Logo depois de montar a lista, em background (sem atrasar a resposta), resolva o link do RD do `▶ Assistir` e guarde-o em memória por 10 min. Quando o player pedir, devolva o redirect na hora. Se der 451, marque o hash como 451, como o precheck já faz.

## Settings (`models.py`)
`HOUSE_DNS: str | None = "192.168.3.44"`, `PLAYBACK_BUDGET: float = 15.0`.

## Fora de escopo
Fontes de torrents, catálogos, legendas, meta, index.html, AdGuard.

## Aplicar
1. `py_compile` dos arquivos alterados.
2. Reinicie: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`; espere `http://127.0.0.1:8000/manifest.json` no chroot (polling com `curl`, sem `Start-Sleep`).
3. Patch: no chroot `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp/x.patch` (`chmod 644`), `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários com `unlink`. Zero `\r`.

## Verificação
- Config sem RD (veja a Seção 6 do HANDOFF): `stream/series/tt2293002:1:2.json` e `stream/movie/tt12042730.json`. Informe quantos diretos vieram e as linhas `🚫 DNS da casa bloqueia` do log (hoje devem aparecer `zjo.lat`, `aponteiecair.lat`, `telaplay93.top`, `cdn.vdcdpstop.lat`) e o resumo `🌐 diretos`.
- Com `HOUSE_DNS` vazio só no teste (variável de ambiente, sem mexer no `.env`): os diretos que respondem vídeo voltam.
- Tempo do pedido de stream: no máx. 8 s a mais do que antes nos 2 casos.
- Playback: chame um link `/playback/...` de um torrent ⬇️ (pegue da lista com o link pessoal **sem imprimir a URL**) e mostre só o código HTTP e o tempo: ≤ 15 s.

Responda em no máximo 5 linhas: arquivos alterados e resultado da verificação.
