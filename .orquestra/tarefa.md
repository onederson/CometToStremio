# Tarefa: episódio não lançado, legenda só sem áudio PT, e Comet substituindo o Cinemeta (meta + busca)

## Contexto
- Código do Comet: A71, chroot, `/opt/comet` (Android: `/data/debian/opt/comet`). Edite lá.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (Android root) e `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian; `git` só existe aqui).
- Enviar arquivo: `adb -s 192.168.3.44:5555 push <arq> /data/local/tmp/<nome>` (um por vez, nome completo), depois `mv` para `/data/debian/...`. Tudo em **LF**.
- **PROIBIDO:** imprimir chaves/tokens (a chave do RD aparece nas URLs do `comet.log`: não mostre essas linhas; troque `/eyJ...` por `/<cfg>`), commit, instalar pacotes, mexer no AdGuard ou no `.env`. **NÃO rode tarefas em segundo plano.** Divida o trabalho em passos curtos.

## Parte A: episódio ainda não lançado
Problema: VisionQuest `tt23112594:1:7` (estreia 2026-11-04; hoje 2026-10-31) recebe packs da temporada (que não têm o E07) e um link do FrostStream "MegaEmbed" falso (só áudio, vídeo carregando para sempre). O `DIGITAL_RELEASE_FILTER` está desligado e deve continuar desligado (ele bloquearia filmes de cinema).
1. Em `comet/services/media_search.py`, logo depois de obter `target_air_date` (log `📅 Episode target air date`): se for **série**, com `target_air_date` válido e **maior que a data de hoje** (`datetime.date.today()`), devolva `MediaSearchResult(MediaSearchStatus.UNRELEASED, ...)` igual ao bloco do `DIGITAL_RELEASE_FILTER` (mesmos campos), e guarde a data no resultado (novo campo opcional `air_date: str | None = None` em `MediaSearchResult`). Log: `⏳ <media_id> ainda não lançado (estreia <data>)`.
2. Em `comet/api/endpoints/stream.py`, no bloco `UNRELEASED`:
   - Aviso em PT-BR: `name` `"[⏳] Comet"`, `description` = `"Episódio ainda não lançado.\nEstreia em DD/MM/AAAA."` quando houver `air_date`, senão `"Ainda não lançado."`.
   - Para **série** com `air_date` (caso novo): **não** inclua os links diretos (são falsos nesse caso). Para os demais casos (filme pelo filtro antigo) mantenha o comportamento atual.

## Parte B: legenda só quando o áudio não é português
1. `comet/services/direct_addons.py`: ao montar `behavior_hints`, se não houver `filename`, defina `behavior_hints["filename"] = f"{curto}.direct.{'PTBR' if is_pt else 'XX'}"` (links diretos PT são dublados ou com legenda embutida; nunca precisam de legenda).
2. `comet/api/endpoints/subtitles.py`, antes de chamar `search_subtitles`: se `filename` indicar áudio português, devolva `{"subtitles": []}` (mesmo header). "Indicar português" = `".direct.PTBR"` no nome **ou** `"pt" in (parse(filename).languages or ())` usando o `parse` do RTN, igual a `comet/api/endpoints/stream.py` linha ~600 (`is_pt = "pt" in (getattr(rtn_data, "languages", None) or ())`). Log curto: `🗒️ Legendas puladas (áudio PT): <filename[:80]>`.
3. Sem filename, ou áudio não-PT: segue como hoje.

## Parte C: Comet no lugar do Cinemeta (o usuário vai desinstalar o Cinemeta)
### C1. Recurso `meta` em PT-BR (novo `comet/services/meta_ptbr.py` + rota em novo `comet/api/endpoints/meta.py`)
- Rotas `/meta/{type}/{id}.json` e `/{b64config}/meta/{type}/{id}.json` (registrar como `catalog`/`subtitles` em `comet/api/app.py`). Só `type` `movie`/`series` e `id` `tt...`; outro caso → `{"meta": null}`.
- Base = meta do Cinemeta: `https://v3-cinemeta.strem.io/meta/{type}/{id}.json` (timeout 8 s). **Nunca** mude `id`, `season`, `episode`, `released` nem a lista de `videos` (o Comet busca os torrents por essa numeração).
- Sobreposição TMDB pt-BR (`TMDBApi` de `comet/metadata/tmdb.py`; `get_tmdb_id_from_imdb`; `movie/{id}?language=pt-BR` ou `tv/{id}?language=pt-BR`):
  - `name` = título pt-BR; `description` = `overview` se não vazio; `poster` = `https://image.tmdb.org/t/p/w500<poster_path>` se houver; `genres` = nomes pt-BR do TMDB.
  - Séries: para cada temporada ≥ 1 presente nos `videos` do Cinemeta, `tv/{id}/season/{S}?language=pt-BR` (semáforo 5). **Só** se o número de episódios do TMDB naquela temporada for igual ao do Cinemeta: para cada vídeo com mesmo S/E, troque `name` **e** `title` pelo nome do TMDB (se não vazio e não for genérico tipo `Episódio 7`) e `overview` pelo do TMDB (se não vazio).
- Falha do TMDB → devolve o meta do Cinemeta sem mudança. Falha do Cinemeta → `{"meta": null}`.
- Cache em memória 12 h (máx. 500). Header `Cache-Control: public, max-age=21600`.
- Manifest: acrescente `{"name":"meta","types":["movie","series"],"idPrefixes":["tt"]}` em `resources` quando `CATALOGS_ENABLED`.

### C2. Busca
- `comet/services/catalogs.py`, em `build_manifest_catalogs`, no fim: `{"type":"movie","id":"comet_search","name":"Busca","extra":[{"name":"search","isRequired":true}]}` e o mesmo para `series` (com `isRequired` eles não aparecem na tela inicial, só na pesquisa).
- `get_catalog` com `comet_search` e `extra["search"]`: TMDB `search/{movie|tv}?query=<q>&language=pt-BR&page=1` (mapa IMDb como nos outros catálogos), **mais** a busca do Cinemeta `https://v3-cinemeta.strem.io/catalog/{type}/top/search=<q url-encoded>.json`: acrescente no fim os itens do Cinemeta que não vieram do TMDB (mesmo `id`). Ordem: TMDB primeiro. Cache 1 h. Sem `search` → `[]`.

## Fora de escopo
Não mexer em filtragem de torrents, ordenação, legendas (além da Parte B), index.html.

## Aplicar
1. `py_compile` dos arquivos alterados.
2. Reinicie: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`; espere `http://127.0.0.1:8000/manifest.json` no chroot (polling com `curl`, sem `Start-Sleep`).
3. Regenere o patch: no chroot `git -C /opt/comet add -N comet/services/meta_ptbr.py comet/api/endpoints/meta.py` e `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp/x.patch`, `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários com `unlink`. Zero `\r`.

## Verificação (no chroot, contra `http://127.0.0.1:8000`, config sem debrid igual a `/var/tmp/vq2.py`, que já existe)
- `/var/tmp/vq2.py`: `1:7` e `1:8` → **um único** stream, o aviso `[⏳]` com "Estreia em 04/11/2026" / "11/11/2026"; `1:3` continua com ~225 streams.
- Legendas: `subtitles/series/tt23112594:1:1/filename=VisionQuest.S01E01.2160p.DSNP.WEB-DL.DDP5.1.Atmos.DV.HDR.H.265.DUAL-BiOMA.mkv.json` → vazio; `filename=VisionQuest.S01E01.No.Strings.1080p.DSNP.WEB-DL.AAC2.0.H.264-playWEB.mkv` → não vazio; `filename=FrostStream.direct.PTBR` → vazio. Os streams diretos de `1:3` têm `behaviorHints.filename`.
- Meta: `meta/series/tt0944947.json` (Game of Thrones) → `name` "Game of Thrones", `description` em português, `videos` com mesma quantidade e mesmos `id` do Cinemeta, nome do `tt0944947:1:1` em português. `meta/movie/tt0120737.json` → "O Senhor dos Anéis: A Sociedade do Anel". `meta/series/tt0434665.json` (Bleach, numeração diferente no TMDB) → `videos` idênticos ao Cinemeta em id/season/episode. Diga o tempo da 1ª e da 2ª chamada.
- Busca: `catalog/movie/comet_search/search=senhor%20dos%20aneis.json` e `catalog/series/comet_search/search=bleach.json` não vazios (mostre os 5 primeiros nomes). `manifest.json`: 21 catálogos e recursos `stream`, `subtitles`, `catalog`, `meta`.

Responda em no máximo 5 linhas: arquivos alterados e resultado da verificação.
