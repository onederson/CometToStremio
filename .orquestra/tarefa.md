# Tarefa U: selos das capas maiores + selo do streaming (Netflix, Prime, Disney+…)

## Pedido do usuário
1. "A tag 'novo episódio' quase não dá pra ler": aumentar esse selo **e todos os outros** (`new`, `dub`, `top10`, e qualquer um futuro).
2. Um selo novo dizendo **de qual streaming** é o título.

## Contexto
- Comet no A71, chroot, `/opt/comet`. Capas: `comet/services/artwork.py` (`_draw_badge`, `VALID_BADGES = {"new_ep","new","dub","top10"}`, fontes 11–20 px em `_get_font`; `_render_landscape_pillow`, `_render_poster_pillow`, cache de disco com chave `land:<backdrop>:<logo>:<badge>`), rota em `comet/api/endpoints/artwork.py`, URLs montadas em `comet/services/catalogs.py` e `comet/services/stremio_library.py` (`?b=`). Fontes: Liberation/DejaVu Bold.
- TMDB tem `movie/<id>/watch/providers` e `tv/<id>/watch/providers` → `results.BR.flatrate[]` (`provider_id`, `provider_name`, `logo_path`, `display_priority`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token ou chave do TMDB; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
### 1. Selos maiores (todos)
- Tamanho proporcional à imagem, não fixo: altura do selo ≈ **11 % da altura** na capa deitada e ≈ **7 % da altura** no pôster; fonte bold ≈ 62 % da altura do selo; margem interna proporcional; cantos arredondados; leve sombra/contorno escuro para ler sobre fundo claro. Na prática, numa capa deitada de ~780×439 o texto fica com ~30 px (hoje 13).
- O `top10` cresce na mesma proporção.
- Toda função que desenha selo usa um helper único (`_badge_metrics(canvas, is_poster)`), para selos futuros já nascerem grandes.
- Mude a versão da chave de cache (ex.: prefixo `v2:`) para as capas antigas serem refeitas.

### 2. Selo do streaming
- Novo parâmetro de capa `?p=<provider_id>` (pode vir junto com `?b=`). Desenhe o **logo oficial do serviço** (`https://image.tmdb.org/t/p/w92<logo_path>`, cache em disco) num quadrado arredondado no **canto superior direito** (o selo de texto fica no canto superior esquerdo, como hoje), tamanho ≈ 16 % da altura na capa deitada / 10 % no pôster.
- Escolha do provedor: `results.BR.flatrate`, o de menor `display_priority`, preferindo esta lista quando presente: Netflix (8), Amazon Prime Video (119), Disney Plus (337), Max (1899/384), Apple TV+ (350), Paramount Plus (531), Globoplay (307), Crunchyroll (283), Star Plus (619). Sem `flatrate` no BR → sem selo.
- Cache SQLite `watch_provider(media_key TEXT PRIMARY KEY, provider_id INT, logo_path TEXT, fetched_at INT)` (7 dias; "nenhum" também é guardado), consulta em paralelo com semáforo 8.
- Onde aplicar: em **todas** as fileiras que já usam capa montada (`/art/...`), filmes e séries. Nas fileiras de um serviço específico (ex.: `⭐ Originais Netflix`), use o provedor da fileira sem consultar.
- Itens cujo pôster é o original do TMDB (sem `/art/`): passe a usar `/art/poster/...` com `?p=` só se a fileira já monta capas; não troque o formato das fileiras que hoje usam pôster puro.
- Kids: igual.

## Fora de escopo
Tudo o resto (ordem das fileiras, textos, metas).

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token)
1. Baixe 4 capas reais (uma de `🆕 Novos episódios` com `new_ep`, uma de `🆕 Lançamentos`, uma do Top 10, uma de `⭐ Originais Netflix`) para `/data/local/tmp/` e copie com `adb pull` para `downloads/capas-teste/` no PC (pasta já ignorada? se não, não versione). Informe as dimensões e a altura do selo em px antes/depois.
2. Mostre quantos itens de 3 fileiras ganharam `?p=` e quais provedores apareceram (nomes).
3. Capa sem provedor no BR: sem selo de streaming e sem erro.
4. Tempo da 1ª carga de uma fileira com 40 itens (≤ 5 s) e da 2ª (cache).
5. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK` (acrescente ao teste `capa`: a capa de um item com `?p=` responde `image/*`).

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
