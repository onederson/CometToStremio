# Tarefa Z3: notas IMDb/Rotten/Metacritic + selo do Oscar + fileiras de prestígio

## Contexto
- Comet no A71, chroot, `/opt/comet`. Meta: `comet/services/meta_ptbr.py` (descrição, `links`, `trailerStreams`). Catálogos: `comet/services/catalogs.py` (capas `/art/...` com selo de texto `?b=` e de streaming `?p=`; helper único de selo em `comet/services/artwork.py`, `VALID_BADGES`). Madrugada: `comet/services/nightly.py`.
- `OMDB_API_KEY` já está no `.env` (plano grátis: **1000 consultas/dia**). `GET https://www.omdbapi.com/?i=<tt>&apikey=<chave>` → `imdbRating`, `imdbVotes`, `Metascore`, `Ratings[]` (`Rotten Tomatoes` "89%"), `Awards` ("Won 3 Oscars. …" / "Nominated for 7 Oscars. …").
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir a chave do OMDb, tokens ou URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env`; mexer em `comet/services/prefetch.py` e no começo da função `stream` de `stream.py`. Nada em segundo plano (seus comandos). Comandos com timeout ≤ 300 s.

## 1. Notas (OMDb com orçamento)
- `comet/services/omdb.py`: `models.py` `OMDB_API_KEY: str | None = None`, `OMDB_DAILY_BUDGET: int = 900`. Cache SQLite `omdb_cache(imdb_id TEXT PRIMARY KEY, data TEXT, fetched_at INT)`: 30 dias para filme/série com mais de 1 ano, 3 dias para lançamento; "não encontrado" também é guardado (7 dias). Contador diário em memória + arquivo `data/omdb_budget.json`; ao chegar no orçamento, só usa cache até meia-noite. Semáforo 4.
- Na **página do título** (meta filme e série): primeira linha da `description` vira `⭐ IMDb 9,3 · 🍅 89% · Ⓜ️ 82` (só o que existir; vírgula decimal) e, se ganhou Oscar, `🏆 Venceu 3 Oscars` (ou `🏆 Indicado a 7 Oscars`). Também `imdbRating` no meta.
- Não consulte o OMDb para listar catálogo inteiro: só no meta (quando o usuário abre o título) e na madrugada (item 3).

## 2. Selo do Oscar na capa
- Novo selo `oscar` (dourado, texto `🏆 OSCAR`, mesmo tamanho proporcional dos outros, canto **inferior esquerdo** para não brigar com o selo de texto e o logo do streaming).
- Aplicado nas capas montadas (`/art/...`) quando o título **ganhou** pelo menos um Oscar segundo o cache do OMDb (`Won N Oscar`). Sem dado em cache = sem selo (não consulta na hora de montar fileira).
- Versão do cache de capa sobe (ex.: `v3:`).

## 3. Fileiras de prestígio (link pessoal; no Kids só onde indicado)
Bloco logo depois das fileiras de mood, nesta ordem, capa deitada, dublados prontos primeiro:
| id | nome | tipo | fonte |
|---|---|---|---|
| `comet_oscar` | 🏆 Vencedores do Oscar de Melhor Filme | movie | lista fixa no código (tt ids) dos vencedores de 1990 até o mais recente, ordem do mais novo para o mais antigo |
| `comet_imdbtop` | ⭐ Os mais bem avaliados de todos os tempos | movie | TMDB `movie/top_rated` (pt-BR, várias páginas) filtrado por `vote_count ≥ 5000`, até 60 |
| `comet_classic_dub` | 📼 Clássicos dublados | movie | filmes lançados **antes de 2000** com `🇧🇷` no banco (mesmo critério do `⚡ Pronto dublado`, mas sem exigir ⚡), ordenados por popularidade TMDB; complete com `discover` (`primary_release_date.lte=1999-12-31`, `vote_count ≥ 2000`) se tiver < 20. **Também no Kids** filtrando família/animação. |
- Madrugada: aqueça o OMDb dos itens dessas 3 fileiras e das 8 primeiras de cada fileira principal (respeitando o orçamento), para os selos de Oscar aparecerem.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); `git -C /opt/comet add -N` dos novos; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (sem imprimir chave/token)
1. `meta/movie/tt0111161`, `tt0068646` (O Poderoso Chefão), `tt15398776` (Oppenheimer) e `meta/series/tt0903747`: 1ª linha da descrição (notas + Oscar).
2. Contador do OMDb depois dos testes (quantas consultas usadas hoje).
3. As 3 fileiras: nº de itens e 6 primeiros; `comet_oscar` começa pelo vencedor mais recente.
4. Capa de um vencedor do Oscar (após cache): copie para `downloads/capas-teste/oscar.jpg` no PC.
5. `scripts/regress.py`: teste `notas` (meta de `tt0111161` tem `IMDb` e `🏆`) e as 3 fileiras ≥ 15 itens. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK` (em primeiro plano).

Responda em no máximo 8 linhas.
