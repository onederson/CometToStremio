# Tarefa P2: busca em português que entende frases de verdade

## Problema (relatado pelo usuário)
- `anime do pirata que estica` → nada (esperado: One Piece). Hoje `parse_query` trata "pirata que estica" como **pessoa** (`do <x>` → diretor) e o tema vira só `pirate`.
- `serie de medicos` → só "Série Saúde" (esperado: Grey's Anatomy, House, The Good Doctor, New Amsterdam…). Hoje `parse_query` devolve `None` porque "medicos" não está no dicionário `THEME_KEYWORDS`.
- O dicionário fixo nunca vai cobrir tudo.

## Contexto
- Comet no A71, chroot, `/opt/comet`. Arquivos: `comet/services/smart_search.py` (`parse_query`, `THEME_KEYWORDS`), `comet/services/catalogs.py` (onde o discover é chamado, ~linha 1900: `_fetch_discover`, junção com a busca por título, `🔎 busca inteligente`), `comet/services/sub_translate.py` (já chama o tradutor `translate.googleapis.com/translate_a/single?client=gtx`), cliente TMDB (`tmdb._get_json`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android (fora do chroot) não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token ou chave do TMDB; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento novo
1. **Pessoa** só quando: `com <nome>`; ou `do/da/de/dos <nome>` em que o `search/person` do TMDB acha alguém com `known_for_department` Acting/Directing, `popularity` ≥ 5 e nome parecido (todas as palavras da consulta aparecem no nome, sem acento). Senão, essas palavras viram **tema**.
2. **Tema genérico** (substitui depender só do dicionário):
   - Tire das palavras restantes as stopwords PT (de, do, da, dos, das, que, com, um, uma, o, a, os, as, e, em, no, na, pra, para, sobre, filme(s), serie(s), série(s), desenho(s), anime(s), tipo, onde, quando, sobre) e os sinais já reconhecidos (gênero, época, dublado, nacional, bem avaliado…).
   - Mantenha `THEME_KEYWORDS` como atalho; para o resto, traduza a frase restante PT→EN pelo mesmo endpoint gtx (`sl=pt&tl=en`), cache em memória 7 dias (reuse a função de requisição de `sub_translate.py`, não duplique).
   - Para cada palavra/expressão em inglês (singular; teste também a expressão inteira de 2 palavras), `search/keyword?query=…` no TMDB; pegue o id do 1º resultado cujo nome é igual ou contém a palavra. Sinônimos fixos para temas comuns que o TMDB nomeia diferente: doctor/medical → `doctor`, `hospital`, `medical drama`; lawyer → `lawyer`, `courtroom`; police → `police`, `detective`; school → `high school`; superhero → `superhero`; pirate → `pirate`.
   - Discover com `with_keywords`: primeiro **E** entre conceitos diferentes (`,`) com **OU** entre sinônimos do mesmo conceito (`|`); se vier < 5 resultados, tente só **OU** entre todos; se ainda < 5, use só o conceito com mais resultados.
   - Ordene por `popularity.desc`, mas com `vote_count.gte=50` (filme) / `vote_count.gte=20` (série) para tirar lixo.
3. Se o discover com tema der resultado, a busca por **título** da frase inteira entra só **depois** e só itens com `vote_count ≥ 20` (para não vir "Série Saúde" na frente de Grey's Anatomy).
4. Busca por título simples (`batman`, `matrix`, `one piece`) continua exatamente igual (`parse_query` → `None`).
5. Log: `🔎 busca inteligente "<texto>" → tema [<palavras EN>] keywords [<ids>] ...: <n>`.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, `catalog/<tipo>/comet_search/search=<frase>.json`; mostre nº e os 8 primeiros nomes)
Obrigatórios (todos têm que passar):
- série `anime do pirata que estica` → **One Piece** entre os 3 primeiros.
- série `serie de medicos` → pelo menos 2 de {Grey's Anatomy, House, The Good Doctor, New Amsterdam, Plantão Médico/ER, Scrubs} entre os 8 primeiros.
- filme `filme de advogado` → ≥ 10 resultados de tribunal/advogado.
- série `desenho do cachorro detetive` → Scooby-Doo entre os 8 primeiros.
- filme `filme com Tom Hanks dos anos 90` → igual a hoje (Forrest Gump etc.).
- série `serie policial bem avaliada`, filme `terror de zumbi`, filme `filme de tubarao` → não pioram (compare com hoje).
- `batman` e `one piece` → mesma lista de hoje.
Depois: acrescente esses 4 primeiros casos ao teste `busca_inteligente` de `scripts/regress.py` (FAIL se não passar) e rode `.\scripts\smoke.ps1` → `SMOKE OK` e `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 8 linhas: arquivos alterados e o resultado de cada caso.
