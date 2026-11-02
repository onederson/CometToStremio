# Tarefa X: fileiras de "mood", 🎌 Animes dublados e 📅 Estreias da semana

## Contexto
- Comet no A71, chroot, `/opt/comet`. Catálogos: `comet/services/catalogs.py` (manifest de catálogos, `get_catalog`, capas deitadas `_build_landscape_meta`/`/art/...` com selos `?b=` e streaming `?p=`, `_get_ready_tt_list` / `⚡ Pronto dublado`, cache de catálogo), `comet/api/endpoints/catalog.py`, `comet/services/stremio_library.py` (histórico), `comet/services/nightly.py` (madrugada, `dub_watch`), `comet/services/smart_search.py` (keywords TMDB com cache). Kids tem lista própria de catálogos.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token ou chave do TMDB; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano (seus comandos): rode tudo em primeiro plano e espere. Comandos com timeout ≤ 300 s.
- **Mudança de manifest:** não crie prefixo de id novo (use `tt…`), para não exigir nada além de reinstalar uma vez.

## 1. Fileiras de "mood" (link pessoal; no Kids só as marcadas)
Bloco logo depois de `📺 Ao vivo agora` no manifest pessoal, nesta ordem, cada uma com ~30 itens, capa deitada com logo (igual às outras), selos de streaming (`?p=`), e **ordem que muda todo dia** (embaralhar com semente = data entre os 100 melhores do discover), com os **dublados prontos primeiro**:
| id | nome | tipo | critério (TMDB discover, `language=pt-BR`) |
|---|---|---|---|
| `comet_mood_cry` | 😭 Para chorar no domingo | movie | drama (18) + keywords que existam no TMDB entre `tearjerker`, `grief`, `terminal illness`, `loss of loved one`, `based on true story` (OU); `vote_average ≥ 7.2`, `vote_count ≥ 800` |
| `comet_mood_twist` | 🤯 Plot twist de explodir a cabeça | movie | keywords `plot twist`, `twist ending`, `unreliable narrator`, `mind bending` (OU); `vote_average ≥ 7`, `vote_count ≥ 1000` |
| `comet_mood_binge` | ⚡ Séries curtas pra maratonar num dia | series | `with_type=2` (minissérie) ou `number_of_seasons=1` com ≤ 8 episódios (confira em `tv/<id>`; cache 7 dias); `vote_average ≥ 7.5`, `vote_count ≥ 300` |
| `comet_mood_light` | 😌 Comédia leve pra desligar | movie | comédia (35), **sem** terror (27), thriller (53), crime (80), guerra (10752); `with_runtime.lte=115`; `vote_average ≥ 6.8`, `vote_count ≥ 800` |
| `comet_mood_family` | 👨‍👩‍👧 Sessão em família (**também no Kids**) | movie | família (10751) ou animação (16) sem terror; `vote_average ≥ 7`, `vote_count ≥ 1000` |
| `comet_mood_night` | 🌙 Suspense pra ver à noite | movie | thriller (53) ou mistério (9648); `vote_average ≥ 7`, `vote_count ≥ 1000` |
Keywords: resolva os ids pelo `search/keyword` uma vez e guarde (reuse o cache da `smart_search`). Cache do catálogo 6 h.

## 2. 🎌 Animes dublados (pessoal e Kids, `type: series`, id `comet_anime_dub`)
- Logo depois de `🔥 Animes da temporada` (ou a fileira de anime que já existe) no manifest.
- Itens: animes (gênero animação + origem/idioma `ja`) que têm **🇧🇷 com ⚡** no banco (mesmo critério do `⚡ Pronto dublado`), mais recentes primeiro, até 40.
- Se tiver < 15, complete com os animes mais populares do TMDB que têm PT no banco (mesmo que não ⚡), marcando-os depois.
- Madrugada: acrescente à lista de trabalho o S1E1 dos 20 animes mais populares (discover animação `ja`, `vote_count ≥ 200`) que ainda não estão no banco, para a fileira crescer sozinha (respeite `NIGHTLY_MAX_ITEMS` aumentando-o para 60).
- Kids: só os de classificação livre/infantil (os do discover com `certification` BR ≤ 12 ou sem violência; use o mesmo filtro que o Kids já usa).

## 3. 📅 Estreias da semana (link pessoal, `type: series`, id `comet_week`)
- Logo depois de `🔔 Chegou dublado`.
- Episódios com estreia de **segunda a domingo da semana atual** (fuso -03): (a) das séries do histórico (últimos 90 dias; via `videos` do meta), e (b) das 30 mais populares do `tv/on_the_air` (região BR).
- Um item por série (o episódio desta semana mais recente), ordenado por data (hoje primeiro, depois os próximos, depois os que já saíram). `description`: `📅 <Dia da semana> DD/MM · T<S>E<E> · <🇧🇷 dublado pronto | legendado | ainda não saiu>` (o status vem de `dub_watch`/banco; sem dado = `legendado` se já saiu). Selo `new_ep` só nos que já saíram.
- Cache 1 h.

## Fora de escopo
Tudo o resto. Não mude a ordem das fileiras existentes (só insira as novas nas posições acima).

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal e Kids, sem imprimir URL/token)
1. Manifest pessoal: posições das 8 fileiras novas e a ordem relativa das antigas inalterada. Kids: `comet_mood_family` e `comet_anime_dub`.
2. Cada fileira: nº de itens e os 6 primeiros nomes; 2 pedidos no mesmo dia = mesma ordem.
3. `comet_mood_light` sem nenhum item de terror/thriller (confira os gêneros no meta de 10).
4. `comet_anime_dub`: quantos ⚡ dublados; Kids sem anime adulto (mostre os nomes).
5. `comet_week`: 8 itens com a descrição completa.
6. Tempo da 1ª carga de cada fileira (≤ 6 s) e da 2ª (cache).
7. `scripts/regress.py`: teste `fileiras_novas` (cada uma ≥ 10 itens, menos `comet_week` ≥ 3). `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 10 linhas.
