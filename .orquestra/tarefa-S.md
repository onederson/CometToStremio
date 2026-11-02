# Tarefa S: clicar numa saga abre a saga inteira (todos os filmes em ordem)

## Problema (relatado pelo usuário)
A fileira `🎬 Sagas` (`comet_saga`, `comet/services/catalogs.py`, `SAGAS`, `_fetch_saga_items`) mostra o **1º filme** de cada coleção com o id dele (`tt…`). Clicar abre só esse filme. O usuário esperava ver todos os filmes da saga.

## Contexto
- Comet no A71, chroot, `/opt/comet`. Meta: `comet/api/endpoints/meta.py` + `comet/services/meta_ptbr.py`. Streams: `comet/api/endpoints/stream.py`. Legendas: `comet/api/endpoints/subtitles.py`. Manifest: `comet/api/endpoints/manifest.py` (já tem prefixo `cometlive:` como exemplo de prefixo próprio). Playback/prefetch/regress podem depender de `media_type`.
- Coleções do TMDB: `collection/<id>?language=pt-BR` → `parts` (cada um com `id`, `title`, `release_date`, `overview`, `poster_path`, `backdrop_path`); imdb via `movie/<id>/external_ids` (já existe `resolve_imdb` com cache `_IMDB_MAP`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android (fora do chroot) não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
1. **Fileira:** cada item da fileira `🎬 Sagas` (sem filtro de gênero) vira **a saga**: `id = "cometsaga:<collection_id>"`, `type = "series"`, `name` = nome PT da coleção (sem "Coleção"/"Collection"), `poster` = pôster da coleção (ou do 1º filme), `background` = backdrop, `description` = `<n> filmes · <ano 1º>–<ano último>` + sinopse PT da coleção. Com o filtro `genre=<saga>` no Descobrir: continua listando os filmes daquela saga (como hoje).
2. **Meta** `meta/series/cometsaga:<id>.json`: `type: "series"`, `name`, `poster`, `background`, `logo` (se houver), `description`, `genres` (do 1º filme), `releaseInfo` (`<ano1>–<anoN>`), e `videos` = os filmes **lançados** em ordem de lançamento: `{"id": "<tt do filme>", "title": "<nº>. <título PT> (<ano>)", "season": 1, "episode": <nº>, "released": <ISO>, "thumbnail": <backdrop w780>, "overview": <sinopse PT>}`. Filme sem imdb → fora. Cache 24 h.
3. **Streams de um filme da saga:** o Stremio vai pedir `stream/series/<tt>.json` (tipo da saga + id do vídeo, **sem** `:S:E`). Quando `type == "series"` e o id é um `tt…` **sem** `:`, trate exatamente como `stream/movie/<tt>.json` (mesma lista, mesmo `▶ Assistir`, mesmos rótulos, mesmo cache). Idem para legendas (`subtitles/series/<tt>.json` → como filme) e para o playback (não pode tentar achar episódio). Não dispare a pré-busca de "próximo episódio" para isso (ou, se for fácil, pré-busque o próximo filme da saga).
4. Manifest: `cometsaga:` em `idPrefixes` de `meta` (os de stream/subtitles continuam `tt`).
5. Nada muda para séries de verdade (`tt…:S:E`) nem para filmes.

## Fora de escopo
Tudo o resto. Não mexa na lista `SAGAS` além do necessário.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token)
1. `catalog/movie/comet_saga.json`: 20 itens `cometsaga:…` com nome e descrição (mostre 5). Com `genre=Harry Potter`: os 8 filmes (como hoje).
2. `meta/series/cometsaga:1241.json` (Harry Potter): 8 vídeos em ordem (mostre títulos); `cometsaga:10` (Star Wars) e `cometsaga:9485` (Velozes) idem com nº de vídeos.
3. `stream/series/tt0241527.json` (Pedra Filosofal) = mesma quantidade de streams e mesmo 1º nome que `stream/movie/tt0241527.json`; o `▶ Assistir` dele abre (seguindo com `User-Agent: ExoPlayerLib/2.19.1` e `Range: bytes=0-1023` → 200/206 vídeo).
4. `subtitles/series/tt0241527.json` → 200 (mesma coisa que o de filme).
5. Série normal `stream/series/tt0903747:1:1.json` e filme normal continuam iguais.
6. Acrescente em `scripts/regress.py` o teste `saga` (itens 2 e 3) e rode `.\scripts\smoke.ps1` → `SMOKE OK` e `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
