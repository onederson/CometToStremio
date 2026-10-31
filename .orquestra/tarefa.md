# Tarefa: legendas, etapa 2: sincronia automática + cota do OpenSubtitles

A etapa 1 já existe e funciona: `comet/services/subtitles.py` (busca OpenSubtitles/SubSource/SubDL, nota por semelhança com o `filename`, download preguiçoso com cache em `/opt/comet/data/subs_cache`) e `comet/api/endpoints/subtitles.py` (rotas `/subtitles/...json` e `/subs/{provider}/{sub_id}/{season}/{episode}.srt`). Leia esses dois arquivos antes de mexer e **mantenha o estilo**.

## Contexto
- Código do Comet: A71, chroot, `/opt/comet` (Android: `/data/debian/opt/comet`). Edite lá.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (Android root) e `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian; `git` só existe aqui).
- Enviar arquivo: `adb -s 192.168.3.44:5555 push <arq> /data/local/tmp/<nome>` (um por vez, nome completo), depois mova. Tudo em **LF**.
- **PROIBIDO:** imprimir chaves; logar/imprimir respostas cruas das APIs ou URLs (o SubDL põe a chave no campo `url`); instalar pacotes (pip/cargo/apt) ou baixar código externo; commit; mexer no AdGuard ou no `.env`. **NÃO rode tarefas em segundo plano.** Divida o trabalho em passos curtos.
- Não há numpy no venv: tudo em Python puro.

## O que fazer

### 1. Cota do OpenSubtitles (conta grátis: 20 downloads/dia)
- O `POST /download` devolve `remaining` e `reset_time_utc`; quando a cota acaba, responde **406** (ou `remaining` ≤ 0).
- Guarde em memória `os_remaining` e `os_reset_at` (datetime UTC). Ao receber 406 ou `remaining` ≤ 0: marque esgotado até `reset_time_utc` (se não vier, até a próxima 00:00 UTC).
- Na lista de `search_subtitles`: enquanto esgotado, **retire** os itens do OpenSubtitles que ainda **não** estão no cache em disco (eles dariam erro). Os que já estão no cache continuam.
- Em qualquer caso, item do OpenSubtitles já em cache em disco ganha +40 na nota (não gasta cota).

### 2. Sincronia automática por legenda de referência (`comet/services/subtitle_sync.py`, novo)
Ideia: quando a melhor legenda PT-BR **não** é da mesma release do arquivo, mas existe uma legenda (em qualquer idioma) **da mesma release**, usamos os tempos dessa como régua para corrigir os tempos da PT-BR.

**Definições**
- **Release exata** de uma legenda em relação ao `filename`: `moviehash_match` verdadeiro, **ou** mesmo grupo (+300 na nota atual) **e** mesmo tipo de fonte (WEB vs BluRay vs HDTV). Exponha isso como um booleano calculado junto da nota.

**Busca de referência (em `search_subtitles`)**
- Além da busca PT-BR atual, busque também em **inglês** no SubSource (`language=english`) e no SubDL (`languages=EN`). **Não** use o OpenSubtitles para referência (gasta cota). Use o mesmo cache em memória de 6 h (chave separada).
- Referência = a legenda inglesa (ou PT-BR) com **release exata** de maior nota. Se o `filename` não veio, não há referência.
- Se a 1ª PT-BR da lista **não** for release exata **e** houver referência: insira **no topo** uma variante sincronizada das 2 melhores PT-BR não exatas: `{"id": "sync-<fonte>-<id>", "url": "<base>/subs/sync/<fonte>/<id>/<S>/<E>/<ref_fonte>/<ref_id>.srt", "lang": "pob"}`. As originais continuam logo abaixo. Limite total continua 12.
- Se a 1ª PT-BR já for release exata: nada muda.

**Alinhamento (`def align_srt(target_srt: str, reference_srt: str) -> tuple[str, dict] | None`)**
1. Parse dos dois SRT em listas de `(início_ms, fim_ms)` (+ texto no alvo). Ignore blocos inválidos.
2. Converta cada lista em máscara de bits com resolução de **100 ms** (um `int` Python: bit `i` = 1 se há fala no intervalo `[i*100, (i+1)*100)`).
3. Para cada razão de velocidade em `{1.0, 25/23.976, 23.976/25, 24/23.976, 23.976/24, 25/24, 24/25}`: escale os tempos do alvo pela razão, monte a máscara, e para cada deslocamento `k` de −1200 a +1200 bins (±120 s) calcule `(ref & desloca(alvo, k)).bit_count()`. Guarde o melhor `(razão, k)`.
4. Refine: em volta do melhor `k` (±2 bins), repita com resolução de **20 ms** para achar o deslocamento fino.
5. Métrica `overlap = sobreposição / min(fala_total_ref, fala_total_alvo)` antes (razão 1, k 0) e depois.
6. Aceite só se `overlap_depois ≥ 0.55` **e** `overlap_depois ≥ overlap_antes + 0.05`. Senão devolva `None`.
7. Aplique `novo_t = t * razão + deslocamento_ms` a todos os blocos, corte negativos para 0, e reescreva o SRT (numeração 1..n, formato `HH:MM:SS,mmm`).
8. Devolva o SRT novo e um dict `{"ratio", "offset_ms", "before", "after"}`.
- Tem de rodar em < 5 s para um filme de 2 h no A71 (meça). Se ficar lento, reduza a faixa de `k` para ±60 s na 1ª passada.

**Rota** em `comet/api/endpoints/subtitles.py`: `GET /subs/sync/{provider}/{sub_id}/{season}/{episode}/{ref_provider}/{ref_id}.srt`
- Cache em disco `subs_cache/sync-<sha1(tudo)>.srt`.
- Baixa alvo e referência com o `fetch_subtitle` existente (cache dele vale). Roda `align_srt` em thread (`asyncio.to_thread`).
- Se `align_srt` devolver `None` ou der erro: sirva a legenda **original** (sem sincronia), sem erro para o player.
- Log uma linha: `🗒️ Sync <fonte>-<id> com ref <ref_fonte>-<ref_id>: razão X, desloc Y ms, encaixe A→B` ou `... não aplicado (A→B)`.

### 3. Aplicar
1. `py_compile` dos arquivos alterados.
2. Reinicie o Comet: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`; espere o `manifest.json` voltar (loop de polling, sem `Start-Sleep`).
3. Regenere o patch: no chroot `git -C /opt/comet add -N comet/services/subtitle_sync.py` e `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp/x.patch`, `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários com `unlink`. Zero `\r`.

## Fora do escopo
Busca PT-BR atual e pesos da nota (exceto o +40 do cache e o booleano de release exata), streams, scrapers, watchdog, UI, README/HANDOFF, `.env`.

## Verificação
1. **Teste unitário do alinhador** (`/var/tmp/ts.py`, apague no fim): pegue uma legenda PT-BR já em `subs_cache` (qualquer `.srt` com > 300 blocos). Gere uma cópia "estragada": todos os tempos × (25/23.976) + 3700 ms. Rode `align_srt(estragada, original)`. Esperado: razão `23.976/25`, deslocamento que desfaz o erro (o tempo do bloco 100 corrigido difere do original em < 150 ms), `after` > 0.8, tempo de execução impresso (< 5 s).
2. **Teste de ponta a ponta**: chame `/subtitles/movie/tt0816692/filename=Interstellar.2014.1080p.BluRay.x264-SPARKS.mkv.json` e `/subtitles/series/tt0944947:7:2/filename=Game.of.Thrones.S07E02.1080p.BluRay.x264-ROVERS.mkv.json`. Imprima os `id` (não as URLs). Se aparecer `sync-...`, baixe-a por `http://127.0.0.1:8000` + caminho e mostre status, nº de blocos e a linha de log `🗒️ Sync`. Diga quantos downloads do OpenSubtitles foram gastos no teste (procure `remaining` no estado em memória ou no log).
3. `grep -a "🗒️" /data/comet/comet.log | tail -8`: sem chave, sem URL, sem erro em loop.

Responda em no máximo 5 linhas: arquivos alterados e os números.
