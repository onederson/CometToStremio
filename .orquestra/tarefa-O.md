# Tarefa O: 📺 TV ao vivo grátis dentro do Comet (Pluto TV BR + canais abertos)

## Contexto
- Comet no A71, chroot, `/opt/comet`. Catálogos: `comet/services/catalogs.py` + `comet/api/endpoints/catalog.py`; meta: `comet/api/endpoints/meta.py` (`meta_ptbr.py`); streams: `comet/api/endpoints/stream.py`; manifest com versão automática.
- **Fontes legais e gratuitas:**
  - Pluto TV (oficial, grátis com anúncios): `GET https://api.pluto.tv/v2/channels?start=<ISO>&stop=<ISO>` a partir do A71 devolve **181 canais do Brasil** (geolocalização pelo IP), cada um com `_id`, `name`, `number`, `category`, `summary`, `logo`/`colorLogoPNG`/`featuredImage` (`.path`), `stitched.urls[0].url` (HLS) e, com `start/stop`, `timelines` (programação: `title`, `start`, `stop`, `episode.description`).
  - Canais abertos do iptv-org: `https://iptv-org.github.io/iptv/countries/br.m3u` (~400; muitos fora do ar).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env`; qualquer fonte de TV paga/pirata (só as duas acima). Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
1. `models.py`: `LIVE_TV: bool = True`, `LIVE_TV_IPTV_ORG: bool = True`.
2. Novo `comet/services/live_tv.py`:
   - **Pluto:** busca canais + programação das próximas 6 h; cache 30 min em memória. Na URL do stream, preencha `deviceId` com um UUID fixo gerado uma vez e guardado em `/opt/comet/data/pluto_device_id`, `sid` com UUID novo por pedido, `appName=web`, `deviceMake=Chrome`, `deviceType=web`, `deviceVersion=unknown`, `clientTime` atual; mantenha o resto da query.
   - **iptv-org:** baixa o M3U 1×/dia; valida cada canal (GET com timeout 5 s, 10 em paralelo, aceita se 200 e o corpo começa com `#EXTM3U`; segue redirecionamentos e respeita o DNS da casa como `direct_addons.py` faz: host bloqueado = descartado); guarda só os vivos em `/opt/comet/data/iptv_alive.json`. Na subida usa o arquivo; revalida em background 1×/dia (tarefa guardada; memória: pare se `MemAvailable` < 600 MB).
   - Ids: `cometlive:pluto:<_id>` e `cometlive:iptv:<sha1 curto da url>`.
3. **Catálogo** (só links pessoal e Kids; no Kids, apenas categorias infantis: `Kids`, `Infantil`, `Animação`/equivalentes do Pluto): `type: "tv"`, id `comet_livetv`, nome `📺 TV ao vivo`, extra `genre` (opções = categorias do Pluto + `Canais abertos`) e `search`. Itens: `poster` = logo colorido (fundo escuro se for PNG transparente: use o `featuredImage` como `background`), `posterShape: "square"`, `name` = nome do canal, `description` = `▶ Agora: <programa> (até HH:MM)` + `⏭ Depois: <programa> (HH:MM)`. Ordem: número do canal do Pluto, depois abertos por nome. Na tela inicial ele aparece no fim da lista de fileiras (depois de todas as atuais).
4. **Meta** `meta/tv/cometlive:...json`: nome, logo, background, descrição com a programação das próximas 6 h (`HH:MM  Título`), `genres` = categoria.
5. **Stream** `stream/tv/cometlive:...json`: 1 stream `{"name": "📺 Ao vivo", "title"/"description": "<canal> · Pluto TV", "url": <HLS>, "behaviorHints": {"notWebReady": false}}`. Para Pluto, gere a URL na hora (sid novo). Canal inexistente → lista vazia.
6. O manifest passa a ter `tv` em `types` e o prefixo `cometlive:` em `idPrefixes` dos recursos meta/stream (sem quebrar os `tt`/kitsu de hoje).
7. `/status`: seção **TV ao vivo**: nº de canais Pluto, nº de abertos vivos, hora da última validação.

## Fora de escopo
Tudo o resto. Não mexa nos catálogos existentes (só acrescente o novo no fim).

## Aplicar
`py_compile`; reinicie (polling `curl` no `manifest`); `git -C /opt/comet add -N` dos novos; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token)
1. `catalog/tv/comet_livetv.json`: nº de itens; 3 nomes + descrições "Agora/Depois". Com `genre=Filmes` (ou uma categoria real): nº de itens. `search=cine`: nº.
2. `meta/tv/<1 id Pluto>.json`: 200 com a programação.
3. `stream/tv/<id Pluto>.json` → baixe a URL HLS com `User-Agent: ExoPlayerLib/2.19.1`: 200 e `#EXTM3U`; baixe a 1ª variante e 1 segmento: 200 e bytes > 0. O mesmo para 1 canal aberto do iptv-org.
4. Kids: catálogo só com categorias infantis (mostre as categorias presentes).
5. Manifest: os catálogos antigos continuam na mesma ordem (compare a lista de ids antes/depois; só um novo no fim).
6. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`. Acrescente em `scripts/regress.py` um teste `livetv` (catálogo ≥ 20 itens, 1 stream Pluto responde `#EXTM3U`) e rode a suíte com ele.

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
