# Tarefa: tela inicial mais variada (estilo Netflix), versão automática do manifest e página do título mais rica

## Contexto
- Código do Comet: A71, chroot, `/opt/comet` (Android: `/data/debian/opt/comet`). Arquivos: `comet/services/catalogs.py`, `comet/services/meta_ptbr.py`, `comet/api/endpoints/manifest.py`.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (Android root) e `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian; `git` só existe aqui).
- Enviar arquivo: `adb -s 192.168.3.44:5555 push <arq> /data/local/tmp/<nome>` (um por vez, nome completo), depois `mv` para `/data/debian/...`. Tudo em **LF**.
- **PROIBIDO:** imprimir chaves/tokens (a chave do RD aparece nas URLs do `comet.log`), commit, instalar pacotes, mexer no AdGuard ou no `.env`. **NÃO rode tarefas em segundo plano.** Divida o trabalho em passos curtos.

## 1. Versão automática do manifest (`manifest.py`)
O Stremio só atualiza um addon instalado quando a `version` do manifest muda; hoje ela é fixa `"2.0.0"` e o usuário ficou com a lista antiga. Troque por `"2.1.<n>"`, com `n = int(hashlib.sha1(json.dumps(<catalogs + resources>, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:6], 16)`, calculado sobre o manifest **antes** de colocar nome/descrição da config (o mesmo para qualquer config).

## 2. Fileiras novas (`catalogs.py`)
Todas com `language=pt-BR`; as de tema usam `watch_region=BR&with_watch_providers=<ids de CATALOG_PROVIDERS juntos com |>`, `sort_by=popularity.desc`, `vote_count.gte=200` (salvo indicação), extra só `skip`, pôster em pé.
- `comet_top10` filme e série `"🔟 Top 10 de hoje"`: `trending/{movie|tv}/day`, **só os 10 primeiros**, sem `skip`.
- `comet_br` filme e série `"🇧🇷 Nacionais"`: `with_origin_country=BR`, `vote_count.gte=20`.
- `comet_action` filme `"💥 Ação e aventura"`: `with_genres=28|12`.
- `comet_comedy` filme `"😂 Comédias"`: `with_genres=35`.
- `comet_horror` filme `"👻 Terror"`: `with_genres=27`.
- `comet_crime` série `"🕵️ Crime e suspense"`: `with_genres=80|9648`, `without_genres=10763,10764,10766,10767`.
- `comet_kdrama` série `"🇰🇷 Doramas"`: `with_original_language=ko`, `without_genres=16,10764,10767`, `vote_count.gte=50`.
- `comet_family` filme `"🧸 Para a família"`: `with_genres=10751`.
- `comet_docs` filme `"🌍 Documentários"`: `with_genres=99`, `vote_count.gte=50`.
- Pôster de **todos** os catálogos: `w500` (hoje `w342`; mais nítido na TV). Fileiras deitadas continuam `w780`.

## 3. Nova ordem (tela variada, alternando serviços e temas)
1. `🔟 Top 10 de hoje` filme, série
2. `🔥 Em alta` filme, série (deitadas)
3. `🆕 Lançamentos` filme, série (deitadas)
4. Depois, intercale: um **bloco de serviço** (`⭐ Originais X` se houver, `X` série, `X` filme) seguido de **um** tema, na ordem dos temas: `🇧🇷 Nacionais` (filme e série juntos), `💥 Ação e aventura`, `🕵️ Crime e suspense`, `😂 Comédias`, `🇰🇷 Doramas`, `👻 Terror`, `🧸 Para a família`, `🌍 Documentários`. Se sobrarem temas, vão depois do último serviço; se sobrarem serviços, seguem sem tema.
5. `🏆 Aclamados` filme, série
6. `🍥 Animes`
7. `comet_search` filme, série (como hoje)

## 4. Página do título mais rica (`meta_ptbr.py`)
Na mesma chamada de detalhes, acrescente ao `append_to_response`: `watch/providers` e `release_dates` (filme) / `content_ratings` (série).
- `background` = backdrop do TMDB em `original` (sem texto; `backdrop_path` dos detalhes).
- Primeira linha da `description` (antes da sinopse, seguida de linha em branco), juntando com ` · ` só o que existir:
  - classificação indicativa BR: filme = primeira `certification` não vazia de `release_dates` com `iso_3166_1 == "BR"`; série = `rating` de `content_ratings` com `BR`. Formato `🔞 16` (ou `🟢 Livre` para `L`).
  - `📺 Netflix, Prime Video` = nomes dos `flatrate` de `watch/providers.results.BR` (no máx. 3; use os nomes curtos do `PROVIDERS` de `catalogs.py` quando o `provider_id` bater).
- Filme: `runtime` = `"2h 10min"` a partir do `runtime` do TMDB (se > 0).

## Fora de escopo
Não mexer em stream, filtragem, legendas, busca, index.html.

## Aplicar
1. `py_compile` dos arquivos alterados.
2. Reinicie: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`; espere `http://127.0.0.1:8000/manifest.json` no chroot (polling com `curl`, sem `Start-Sleep`).
3. Regenere o patch: no chroot `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp/x.patch`, `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários com `unlink`. Zero `\r`.

## Verificação (no chroot, contra `http://127.0.0.1:8000`)
- `manifest.json`: `version` no formato `2.1.N`; liste `name-tipo` de todos os catálogos na ordem.
- Cada catálogo novo (`comet_top10`, `comet_br`, `comet_action`, `comet_comedy`, `comet_horror`, `comet_crime`, `comet_kdrama`, `comet_family`, `comet_docs`): quantidade e 4 primeiros nomes; `comet_top10` = 10.
- `meta/movie/tt31193180.json` (Pecadores) e `meta/series/tt4574334.json` (Stranger Things): mostre a primeira linha da `description`, `runtime`, `background`.

Responda em no máximo 5 linhas: arquivos alterados e resultado da verificação.
