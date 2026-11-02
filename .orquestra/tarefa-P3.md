# Tarefa P3: busca inteligente — corrigir os padrões de erro (bateria de 25 frases)

## Contexto
- Comet no A71, chroot, `/opt/comet`. Arquivos: `comet/services/smart_search.py`, `comet/services/catalogs.py` (discover/junção), `comet/services/sub_translate.py` (tradutor). A Tarefa P2 já faz: tirar stopwords, traduzir PT→EN, `search/keyword`, discover com E/OU, fallback.
- Bateria rodada contra o Comet real (resultado atual: nº de itens | 6 primeiros):
  - série `serie de bombeiros` → 1 (Cortina de Fumaça). **Esperado:** 9-1-1, Chicago Fire, Station 19 entre os 8 primeiros.
  - série `anime de cozinha` → 1. **Esperado:** Food Wars (Shokugeki no Soma) entre os 8.
  - série `serie de cozinha competicao` → Survivor, Big Brother… **Esperado:** MasterChef / Hell's Kitchen / Top Chef entre os 8.
  - filme `filme de cachorro que fala` → Supergirl, Superman… **Esperado:** filmes de cachorro falante (ex.: A Caminho de Casa/Homeward Bound, Beethoven, Marley & Eu não precisa) ≥ 3 entre os 8.
  - filme `filme espacial com astronauta perdido` → 0. **Esperado:** Perdido em Marte entre os 8 (Gravidade, Interestelar bem-vindos).
  - filme `terror em hospital abandonado` → 2. **Esperado:** ≥ 8 resultados de terror.
  - série `serie de policia brasileira` → 1. **Esperado:** ≥ 4 séries policiais brasileiras.
  - série `anime de ninja` → títulos em japonês (忍たま乱太郎). **Esperado:** nenhum título só em escrita não latina; Naruto no topo.
  - filme `filme do cara que acorda sempre no mesmo dia` → Drácula. **Esperado:** Feitiço do Tempo (Groundhog Day) / No Limite do Amanhã / A Morte Te Dá Parabéns entre os 8.
  - filme `filme de dinossauro` → 1º "O Fim da Rua" (estranho). **Esperado:** Jurassic Park/World nos 3 primeiros.
  - Estavam bons e **não podem piorar**: `filme de viagem no tempo`, `filme de assalto a banco`, `fim do mundo`, `serie de vampiro adolescente`, `filme de boxe`, `anime de futebol`, `filme de natal para familia`, `serie de advogado`, `filme sobre a segunda guerra`, `desenho de super heroi`, `serie de zumbi`, `comedia romantica dos anos 2000`, `filme de tubarao assassino`, `filme de corrida de carro`, `anime de robo gigante`, e os da P2 (`anime do pirata que estica`, `serie de medicos`, `filme de advogado`, `desenho do cachorro detetive`, `batman`, `one piece`, `filme com Tom Hanks dos anos 90`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token ou chave do TMDB; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Corrija os PADRÕES (não frase por frase)
1. **Candidatos de keyword:** para cada conceito, tente nesta ordem: a frase restante inteira em inglês, os pares de palavras (bigramas), as palavras soltas; cada termo também no **singular** (firefighters→firefighter, dogs→dog). Para cada termo, considere os **3 primeiros** resultados do `search/keyword` cujo nome contém o termo e junte com OU (`|`). Prefira o bigrama quando ele existir como keyword (`talking dog`, `cooking competition`).
2. **Tradução contextual:** traduza a frase inteira (não palavra por palavra) e também, quando o tipo é anime/desenho/série de comida, aceite sinônimos de domínio: cozinha → `cooking`, `chef`, `food`; polícia → `police`, `detective`; espaço/espacial → `space`, `astronaut`; bombeiro → `firefighter`, `fire department`.
3. **Cadeia de alternativas que funciona sempre:** E entre conceitos → OU entre todos → só o conceito com mais resultados → mesmo de novo com `vote_count.gte` reduzido a 5 → por fim `search/movie|tv` com a tradução inglesa. Pare na 1ª que der ≥ 8 resultados. Hoje a cadeia está parando com 0–2. Junte resultados das etapas sem repetir até 40.
4. **Votos mínimos:** `vote_count.gte` 50 (filme) / 20 (série), mas **5** quando há `with_origin_country=BR` ou idioma original `pt`.
5. **Título:** item cujo `name/title` em pt-BR está só em escrita não latina → use o título en-US (`translations` ou nova chamada com `language=en-US`, em lote, com cache); se nem assim, descarte.
6. **Enredos comuns** (frases que descrevem a história): tabela pequena de padrões PT → keyword TMDB, reconhecendo variações (regex sem acento): "mesmo dia"/"dia se repete"/"preso no tempo" → `time loop`; "troca de corpo(s)" → `body swap`; "perde a memória"/"amnésia" → `amnesia`; "invasão alienígena"/"et invade" → `alien invasion`; "casa assombrada" → `haunted house`; "vingança" → `revenge`; "viagem de carro"/"pé na estrada" → `road trip`; "fim do mundo"/"apocalipse" → `apocalypse`; "ilha deserta"/"náufrago" → `deserted island`; "baseado em fatos reais"/"história real" → `based on true story`; "inteligência artificial"/"robô que pensa" → `artificial intelligence`; "serial killer"/"assassino em série" → `serial killer`; "luta de rua"/"artes marciais" → `martial arts`. Mantenha a tabela em um dict de fácil extensão.
7. **Relevância:** ordene por `popularity` mas suba itens cujo conjunto de keywords bate com **mais** conceitos da frase (ex.: Jurassic Park acima de "O Fim da Rua" em "filme de dinossauro").

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação
1. Rode a bateria inteira (as 10 com "Esperado" + as 22 que não podem piorar) pelo `catalog/<tipo>/comet_search/search=<frase>.json` do link pessoal e mostre, para cada uma: nº de itens e os 6 primeiros nomes. **Meta:** ≥ 9 das 10 com "Esperado" atendidas e **nenhuma** das 22 piorando.
2. Coloque a bateria em `scripts/regress.py` como teste `busca_bateria`: cada frase com um critério simples (ex.: algum de {nomes} nos 8 primeiros, ou ≥ N itens); o teste é PASS se ≥ 90 % das frases passam, WARN entre 75 % e 90 %, FAIL abaixo.
3. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 10 linhas: arquivos alterados, quantas das 10 passaram (e quais falharam), e se alguma das 22 piorou.
