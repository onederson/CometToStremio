# Tarefa T: TV ao vivo que abre no Stremio + fileira na tela inicial + correção do áudio dos candidatos

## Problemas (relatados pelo usuário)
1. Ao clicar num canal (`type: tv`, id `cometlive:...`) o Stremio do usuário mostra "Nenhum streaming disponível". O log mostra que o app pediu `meta/tv/<id>` e `stream/tv/<id>` e o Comet respondeu 200, e o mesmo pedido feito à mão traz 1 stream HLS que toca. Ou seja: o app está descartando/ignorando.
2. A fileira `📺 TV ao vivo` (`comet_livetv`) está em último lugar entre 57 fileiras; o usuário não vê nada de TV na tela inicial.
3. No log: `audio_probe candidato extra <hash> falhou: torbox: No file matched requested episode.` — o laço de candidatos extras em `_preresolve_assistir_task` (`comet/api/endpoints/stream.py`, perto de `c_fidx = cand.get("file_index", "n")` e `c_deb.generate_download_link(...)`) passa `season`/`episode` `"n"` para filmes (o pré-resolve principal já normaliza com `_norm_se`).

## Contexto
- Comet no A71, chroot, `/opt/comet`. Arquivos: `comet/services/live_tv.py` (metas do catálogo ~linha 415–490, `get_live_tv_meta`, `get_live_tv_stream`), `comet/services/catalogs.py` (manifest de catálogos; `comet_livetv` ~linhas 332 e 727; Kids), `comet/api/endpoints/catalog.py`, `comet/api/endpoints/meta.py`, `comet/api/endpoints/stream.py`.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
### 1. Canal que o app aceita
Siga o formato dos addons de TV que funcionam no Stremio (ex.: o addon oficial de canais e os addons IPTV populares):
- Em **todo** meta de canal (catálogo e `meta/tv`): `"behaviorHints": {"defaultVideoId": "<mesmo id>", "hasScheduledVideos": false}`, `"releaseInfo": "Ao vivo"`, `"links": []` não precisa.
- No `meta/tv/<id>`: acrescente `"videos": [{"id": "<mesmo id>", "title": "📺 Assistir ao vivo", "released": "<agora ISO>", "thumbnail": <background>, "overview": <"Agora: … · Depois: …">}]`.
- No stream: `name` = `"📺 Ao vivo"`, `description` = `"<canal> · <Pluto TV|Canal aberto>"` (sem `title` duplicado), `url` = HLS, `behaviorHints`: `{"notWebReady": true}` para Pluto (o player web não toca o HLS deles sem proxy; no app nativo funciona) e `{"notWebReady": false}` nos abertos. Um stream por canal, só com `url`.
- Corrija o `title` dos canais abertos (hoje `get_live_tv_stream` escreve "· Pluto TV" quando o nome contém "pluto").
- O `stream` resource do manifest continua com `tv` e `cometlive:`.

### 2. Fileira na tela inicial
- Nova fileira `type: "tv"`, id `comet_livehome`, nome `📺 Ao vivo agora`, **sem extra obrigatório e sem `genre`/`search`** (só `skip` opcional), com **20 canais**: 4 de Filmes, 3 de Séries, 3 Infantil (no Kids: só infantis/animação, 20), 2 Notícias, 2 Esportes, 2 Anime & Geek, 2 Novelas/TV Brasileira, 2 Comédia (pegue os primeiros do Pluto por número em cada categoria; complete com outros se faltar). Mesmo formato de item (com o "Agora/Depois" na descrição e o `behaviorHints` do item 1).
- Posição: logo **depois** de `🆕 Lançamentos` (série) no manifest pessoal e logo depois da 1ª fileira no Kids.
- A fileira completa `📺 TV ao vivo` (com gênero e busca) continua no fim/Descobrir.

### 3. Áudio dos candidatos extras
No laço de candidatos extras, normalize `season`/`episode` do candidato igual ao `_norm_se` do principal antes de `generate_download_link`. Mude o log desse erro de `debug` para `PLAYBACK` com texto curto.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token)
1. `meta/tv/<id Pluto>`: tem `behaviorHints.defaultVideoId` = id e `videos[0].id` = id. `stream/tv/<id>`: 1 stream, HLS 200 `#EXTM3U`.
2. Manifest: `comet_livehome` logo depois de `comet_new` (série); os outros catálogos na mesma ordem relativa. Kids tem a sua.
3. `catalog/tv/comet_livehome.json`: 20 itens, categorias variadas (mostre nome + gênero). Kids: só infantis.
4. Peça a lista de um filme cujo `▶ Assistir` tem candidatos extras dublados (ex.: `tt2911666`, `tt0241527`): o log não tem mais `No file matched requested episode` para filmes e aparecem até 3 linhas `🔊 áudio`.
5. `scripts/regress.py`: no teste `livetv`, cheque também `defaultVideoId` e `comet_livehome` ≥ 15. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
