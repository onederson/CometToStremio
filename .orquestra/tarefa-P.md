# Tarefa P: 🔎 Busca que entende português ("comédia anos 90 dublada", "terror com Jason", "filme de tubarão")

## Contexto
- Comet no A71, chroot, `/opt/comet`. A busca de hoje (`comet_search` e `comet_person` em `comet/services/catalogs.py`, `_fetch_person_items`, `_get_cached_search`) só procura pelo título ou pelo nome da pessoa no TMDB. Existe um cliente TMDB (`tmdb._get_json(path, label)`), `language=pt-BR`.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token ou chave do TMDB; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
1. Novo `comet/services/smart_search.py` com `parse_query(text) -> dict | None` (Python puro, sem rede) que reconhece, sem acento e sem diferenciar maiúsculas:
   - **Gêneros** PT → ids TMDB de filme e de série (comédia, terror, ação, aventura, animação/desenho, romance, drama, suspense, ficção científica/sci-fi, fantasia, documentário, crime/policial, guerra, faroeste, musical, mistério, família, anime → animação + idioma `ja`).
   - **Época**: `anos 80/90/2000`, `de 1994`, `2010s`, `antigo` (< 1990), `recente`/`novo`/`lançamento` (últimos 2 anos).
   - **Pessoa**: `com <nome>`, `do/da/de <diretor>` → `search/person` → `with_people`.
   - **Tema**: `de/sobre <palavra>` que não seja pessoa → `search/keyword?query=<palavra traduzida p/ inglês por um dicionário pequeno embutido de ~80 palavras comuns: tubarão→shark, zumbi→zombie, vampiro→vampire, espaço→space, dinossauro→dinosaur, robô→robot, assalto→heist, viagem no tempo→time travel, ...>` → `with_keywords`.
   - **Qualidade/idioma**: `dublado`/`dublada` → filtra depois só o que estiver com `🇧🇷` pronto (use o mesmo critério do `⚡ Pronto dublado`, `_fetch_ready_items`/banco, sem buscar streams ao vivo); `nacional`/`brasileiro` → `with_origin_country=BR`; `bem avaliado`/`melhores` → `vote_average.gte=7.5` e `vote_count.gte=500`; `curto` → `with_runtime.lte=100` (filme).
   - Devolve `None` quando não reconhece **nenhum** desses sinais (aí a busca é a de hoje).
2. Em `comet_search`: se `parse_query` devolver filtros, chame `discover/movie` ou `discover/tv` (`sort_by=popularity.desc`, `language=pt-BR`, até 2 páginas) e **junte** com a busca por título de hoje: resultados do discover primeiro, depois os do título que não estiverem repetidos (máx. 60). Cache igual ao de hoje.
3. Log: `🔎 busca inteligente "<texto>" → <filtros resumidos>: <n>`.

## Fora de escopo
Tudo o resto. A busca por título simples ("batman") tem que dar o mesmo resultado de hoje.

## Aplicar
`py_compile`; reinicie (polling `curl` no `manifest`); `git -C /opt/comet add -N comet/services/smart_search.py`; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal)
1. Unidade: `parse_query` para 12 frases (as 3 do título + `ação anos 80`, `série policial bem avaliada`, `filme brasileiro de comédia`, `anime recente`, `desenho dublado`, `terror de zumbi`, `filme com Tom Hanks dos anos 90`, `batman` → None, `matrix` → None) — mostre os filtros.
2. Busca real (filme e série conforme fizer sentido) para 6 dessas: nº de resultados e os 5 primeiros nomes.
3. `batman` antes/depois: mesma lista (mostre os 5 primeiros).
4. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`. Acrescente em `scripts/regress.py` o teste `busca_inteligente` (`terror de zumbi` filme ≥ 10 e o 1º resultado tem gênero terror no meta; unidade de `parse_query` para 4 frases) e rode a suíte com ele.

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
