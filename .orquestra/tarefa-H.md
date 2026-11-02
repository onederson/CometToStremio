# Tarefa H: próximo episódio instantâneo (pré-busca ao dar play)

## Contexto
- Comet no A71, chroot, `/opt/comet`. Arquivos: `comet/api/endpoints/playback.py`, novo `comet/services/prefetch.py`, `comet/core/models.py`.
- Hoje a 1ª busca de cada episódio leva ~18 s (Prowlarr + fontes ao vivo); depois vem do cache (tabela `torrents`). O `▶ Assistir` já é pré-resolvido em background quando a lista é montada (`_preresolve_assistir_task` em `stream.py`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv` para `/data/debian/var/tmp/`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com config ou token; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 120 s.

## Comportamento
- Quando um pedido de **playback de série** (`/playback/...` com `season` e `episode`) chega, agende em background (sem atrasar a resposta) a pré-busca do **próximo episódio**:
  - Próximo = `E+1` na mesma temporada; se `E` for o último da temporada (use o meta já disponível: Cinemeta/`meta_ptbr`, a lista `videos`), `S+1:1`. Se não houver próximo, ou se a data de estreia dele for futura, não faz nada.
  - A pré-busca faz um GET interno em `http://127.0.0.1:8000/<mesmo prefixo de config do pedido>/stream/series/<imdb>:<S>:<E>.json` (o prefixo é o 1º segmento do caminho do playback: token pessoal/kids ou b64). Isso popula o cache e dispara o pré-resolve do `▶ Assistir`.
- Limites (`models.py`): `PREFETCH_NEXT_EPISODE: bool = True`; no máx. 1 pré-busca por série a cada 20 min (chave `imdb:S:E` alvo, memória); no máx. 2 ao mesmo tempo (semáforo); timeout de 60 s; erro → `logger.warning` curto.
- Log: `⏭️ pré-busca <imdb> S<S>E<E>: <n> streams em <t>s` (sem config/token).
- Anime com numeração absoluta: use o mesmo `S:E` que o Stremio usa (o do pedido), não o absoluto.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); `.\scripts\smoke.ps1` → `SMOKE OK`; patch (`git -C /opt/comet add -N comet/services/prefetch.py`; `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários; zero `\r`).

## Verificação (link pessoal, sem imprimir URL)
1. **Não apague nada do banco.** Escolha um episódio cujo seguinte ainda não está na tabela `torrents` (consulte por `media_id` + `season` + `episode`; ex.: The Last of Us `tt3581920`, temporada 2) e mostre a contagem de linhas do seguinte antes do teste (deve ser 0).
2. Peça a lista do episódio, chame o playback do `▶ Assistir` dele, e mostre a linha `⏭️ pré-busca` no log.
3. Depois, peça a lista do episódio seguinte: tempo (deve ser ≤ 3 s, contra ~18 s sem pré-busca) e se o `▶ Assistir` dele abre na hora (código + tempo).
4. Último episódio de uma temporada → pré-busca vai para `S+1:1`. Episódio cujo seguinte ainda não estreou → sem pré-busca.
5. `smoke.ps1` → `SMOKE OK`.

Responda em no máximo 5 linhas: arquivos alterados e resultado da verificação.
