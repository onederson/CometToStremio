# Tarefa F: TorBox como 2º debrid (cobre o que o RD bloqueia com 451)

## Contexto
- Comet no A71, chroot, `/opt/comet` (Android `/data/debian/opt/comet`). Arquivos prováveis: `comet/core/models.py`, `comet/core/config_validation.py` (onde o `PERSONAL_LINK_TOKEN` vira a config), `comet/api/endpoints/stream.py` (`_apply_clean_layout`, montagem por `debrid_stream_specs`/`entry_index`), `comet/api/endpoints/playback.py` (`_try_playback_fallback_on_451`), `comet/services/catalogs.py` (`⚡ Pronto dublado`, `_fetch_ready_items`).
- O Comet já aceita vários debrids (`debridServices` é lista; `comet/debrid/manager.py` tem `"torbox": {"extension": "TB"}`) e hoje lista **cada torrent uma vez por serviço**.
- Medido: dos 31 torrents dublados que o RD bloqueia (tabela `debrid_blocked_hashes`), **28 estão em cache no TorBox**.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** para `/data/local/tmp/` + `mv` para `/data/debian/var/tmp/`. Tudo em LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env` (o usuário já colocou `TORBOX_API_KEY` lá; confira só que a linha existe, sem imprimir o valor). Nada em segundo plano. Comandos com timeout ≤ 120 s.

## 1. Ligar o TorBox no link pessoal
- `TORBOX_API_KEY: str | None = None` em `models.py`.
- Quando a config vier do `PERSONAL_LINK_TOKEN` (e do `KIDS_LINK_TOKEN`) e `TORBOX_API_KEY` existir, acrescente `{"service": "torbox", "apiKey": <chave>}` em `debridServices` **depois** do RD, se ainda não houver torbox. Configs vindas do `/configure` (b64) não mudam.

## 2. Uma linha por torrent (`stream.py`)
Com 2+ debrids, agrupe por `info_hash` (+ arquivo/episódio) e mantenha **uma** entrada, nesta prioridade:
1. RD em cache (⚡) e hash **não** marcado como 451 para o RD;
2. TorBox em cache (⚡);
3. RD não cacheado (⬇️) se não estiver marcado 451; senão TorBox não cacheado;
4. (P2P como hoje).
- Na descrição (layout `clean`), a 3ª linha ganha o serviço: `Real-Debrid` ou `TorBox`. No nome não muda nada além do que já existe (`⚡/⬇️ <res> ...`).
- Torrents que hoje viram `⚠️ P2P (bloqueado no RD)` passam a sair como TorBox ⚡ quando o TorBox tem em cache.
- `▶ Assistir`: candidatos ⚡ podem ser RD (sem 451) ou TorBox; mesma preferência de hoje (dublado, 1080p, ≤ 30 GB). O pré-resolve em background usa o serviço escolhido.

## 3. Playback (`playback.py`)
- Se o RD responder 451 para um hash e o TorBox estiver configurado: **antes** de tentar outros candidatos, tente o mesmo hash/arquivo no TorBox (dentro do `PLAYBACK_BUDGET`). Log `🔁 451 no RD → TorBox <hash curto>`.
- Na troca do 451 com outros candidatos, aceite candidatos do TorBox em cache.

## 4. `⚡ Pronto dublado` (`catalogs.py`)
Conta como "pronto" o que estiver em cache no RD (sem 451) **ou** no TorBox.

## Fora de escopo
Fontes de torrents, legendas, meta, catálogos (além do item 4), `index.html`, AdGuard.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, espere o `manifest` com polling `curl`); rode `.\scripts\smoke.ps1` (precisa dar `SMOKE OK`); regenere o patch (`git -C /opt/comet add -N <novos>`; `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`, apague os temporários; zero `\r`).

## Verificação (com o link pessoal, sem imprimir a URL)
1. `stream/series/tt2293002:1:2` (Ben 10 Omniverse) e `stream/series/tt35854736:1:1` (Avatar Seven Havens): quantos streams `Real-Debrid` ⚡, `TorBox` ⚡, ⬇️, P2P; quantos `🇧🇷` com ⚡; e que **não há hash repetido** na lista.
2. Mesmo título antes/depois: os que eram `⚠️ P2P (bloqueado no RD)` → quantos viraram TorBox ⚡.
3. Playback do `▶ Assistir` do Avatar Seven Havens S01E01: código HTTP e tempo, e seguindo com `User-Agent: ExoPlayerLib/2.19.1` e `Range: bytes=0-1023` → 200/206 vídeo.
4. Playback de um hash marcado 451 no RD que o TorBox tem: log `🔁 451 no RD → TorBox` e vídeo 200/206 em ≤ 15 s.
5. `catalog/series/comet_ready` (ou o id do Pronto dublado): quantos itens antes/depois.
6. `smoke.ps1` → `SMOKE OK`.

Responda em no máximo 5 linhas: arquivos alterados e resultado da verificação.
