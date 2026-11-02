# Tarefa L: madrugada "tudo instantâneo" + aviso de episódio dublado novo + fileira "🔔 Chegou dublado"

## Contexto
- Comet no A71, chroot, `/opt/comet`. Fuso do aparelho: -03. Arquivos: novo `comet/services/nightly.py`, `comet/services/stremio_library.py` (histórico: itens com `state.lastWatched`; o `state` do Stremio também tem `season`, `episode`, `video_id` do último assistido), `comet/services/prefetch.py` (`_find_next_episode`, `_get_series_videos`, `_is_future_release`: **reutilize**), `comet/services/catalogs.py` + `comet/api/endpoints/catalog.py` (catálogos pessoais `mylist`/`newep`/`foryou` como modelo), `comet/services/warmup.py` (como o warmup é iniciado na subida), `comet/core/models.py`, `comet/api/endpoints/status.py`, migrações SQLite (`schema_specs.py`/`schema_migrations.py`, como foi feito com `pt_filenames`).
- O cache de streams é a tabela `torrents`; um GET interno em `http://127.0.0.1:8000/<PERSONAL_LINK_TOKEN>/stream/<type>/<id>.json` popula o cache e dispara o pré-resolve do `▶ Assistir` (é o que `prefetch.py` faz).
- `NTFY_TOPIC` pode existir ou não no `.env` (hoje não existe). Sem ele, nada de push, o resto funciona.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano (seus comandos). Comandos com timeout ≤ 300 s.

## Comportamento
1. `models.py`: `NIGHTLY_WARM: bool = True`, `NIGHTLY_WARM_HOUR: int = 4`, `NIGHTLY_MAX_ITEMS: int = 40`, `NTFY_TOPIC: str | None = None`.
2. `nightly.py`, iniciado na subida igual ao warmup (task guardada). Roda 1 vez por dia às `NIGHTLY_WARM_HOUR` (hora local) e também 20 min depois de subir se a última execução (gravada em `/opt/comet/data/nightly_last.json`) tiver mais de 26 h.
3. Lista de trabalho (sem repetidos, no máx. `NIGHTLY_MAX_ITEMS`):
   a. **Séries do histórico** (vistas nos últimos 60 dias, mais recentes primeiro, máx. 25): o próximo episódio depois do último assistido (`state.season/episode`; se não houver, pule), e também o **último episódio já lançado** se for diferente. Nunca episódio com estreia futura.
   b. **Top 10 de hoje**: os 10 filmes e o S1E1 das 5 primeiras séries.
4. Execução: um por vez, pausa de 3 s entre eles, timeout 90 s cada. Antes de cada item, se `MemAvailable` (`/proc/meminfo`) < 600 MB, espere 60 s; se continuar, pare a rodada (log). Para cada item guarde: nº de streams, se tem `🇧🇷` com ⚡ ("dublado pronto").
5. Tabela SQLite nova `dub_watch(media_id TEXT PRIMARY KEY, imdb TEXT, season INT, episode INT, name TEXT, dub_ready INT, aired TEXT, first_ready_at INT, notified INT)`.
6. **Aviso**: episódio de série do histórico, lançado nos últimos 14 dias, que passou a `dub_ready=1` (antes 0 ou não existia) e `notified=0` → se `NTFY_TOPIC`: `POST https://ntfy.sh/<NTFY_TOPIC>` com título `🇧🇷 Episódio dublado chegou`, corpo `<Nome> T<S>E<E>`, header `Click: stremio:///detail/series/<imdb>/<imdb>:<S>:<E>`, e marque `notified=1`. Sem tópico: só log.
7. **Fileira `🔔 Chegou dublado`** (só link pessoal, `type: series`, id `comet_dubready`, logo depois de `🆕 Novos episódios` no manifest): séries com episódio `dub_ready=1` e `first_ready_at` nos últimos 14 dias, mais recentes primeiro, mesma capa deitada e selo `new_ep` dos Novos episódios. Vazia = lista vazia (sem erro).
8. Log: `🌙 madrugada: <n> itens, <d> dublados prontos, <a> avisos em <t>s`. Contadores no `/status` (seção nova **Madrugada**: última execução, itens, dublados, avisos, próxima execução).
9. Endpoint manual (para teste e para o usuário): `GET /<PERSONAL_LINK_TOKEN>/nightly/run` dispara uma rodada agora (se já houver uma rodando, responde que está rodando) e devolve JSON `{"started": true}`. Outro prefixo → 404.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (polling `curl` no `manifest`); `git -C /opt/comet add -N` dos novos; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token)
1. Dispare `/nightly/run`, espere terminar (polling no log ≤ 300 s) e mostre a linha `🌙 madrugada` e 5 linhas da tabela `dub_watch` (sem nada sensível).
2. Depois da rodada, a lista de streams de 2 itens da rodada vem em ≤ 3 s.
3. Simule o aviso sem tópico: ponha `dub_ready=0` num episódio recente, rode de novo, mostre o log do aviso e `notified`. Restaure.
4. `catalog/series/comet_dubready.json` → 200 (mostre quantos itens). Manifest tem o catálogo depois do `newep`. Kids **não** tem.
5. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
