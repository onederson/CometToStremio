# Tarefa Q: página do título mais esperta (fillers de anime, "previamente em", maratona sem trocar de dublado) + 🎓 legenda PT+EN + 🎲 sorteio do dia

## Contexto
- Comet no A71, chroot, `/opt/comet`. Meta: `comet/services/meta_ptbr.py` (já preenche `videos[].overview` em PT pelo TMDB). Streams: `comet/api/endpoints/stream.py` (`bingeGroup` em `_apply_clean_layout`: `comet|{service}|{res}|{lang_tag}|{group}`; o `▶ Assistir` usa `comet|best`). Legendas: `comet/services/subtitles.py`, tradução em `comet/services/sub_translate.py` (`ensure_auto_translated`, `translate_srt`). Catálogos: `comet/services/catalogs.py`.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; imprimir respostas cruas do SubDL; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## 1. Fillers de anime
- Novo `comet/services/anime_filler.py`: para séries de anime (o meta já sabe que é anime: Kitsu/gênero animação + origem JP), busca a lista em `https://www.animefillerlist.com/shows/<slug>` (slug = nome em inglês minúsculo com hífens; tente o nome do Cinemeta e os aliases; cache 7 dias em SQLite `anime_filler(slug TEXT PRIMARY KEY, data TEXT, fetched_at INT)`; não achou = guarda vazio por 7 dias). Parse da tabela `table.EpisodeList`: nº absoluto do episódio + tipo (`Manga Canon`, `Mixed Canon/Filler`, `Filler`, `Anime Canon`).
- No meta: episódio filler ganha no `title`/`name` o sufixo ` · 🟡 Filler` e misto ` · 🟠 Misto`; canon fica igual. Use o mapeamento absoluto que o Comet já tem (`episode_index.py::get_absolute_episode`) para casar S:E com o nº absoluto.
- Verifique com One Piece `tt0388629` e Naruto Shippuden `tt0988824`.

## 2. "Previamente em…" no 1º episódio de cada temporada
No meta, para o episódio 1 de cada temporada ≥ 2, acrescente ao final do `overview` um parágrafo `\n\n📺 Na temporada anterior: <resumo>` montado com as sinopses PT dos 3 últimos episódios da temporada anterior (frases inteiras, máx. 400 caracteres). Só se houver sinopse.

## 3. Maratona sem trocar de dublado
- O `▶ Assistir` hoje tem `bingeGroup = "comet|best"`. Troque para `comet|best|<lang_tag>` (`pt` se for dublado, senão o idioma), para o próximo episódio automático do Stremio continuar no dublado.
- Nos demais streams o formato atual fica.

## 4. 🎓 Legenda PT+EN (para aprender inglês)
Em `search_subtitles`, quando houver uma inglesa compatível com o arquivo, acrescente 1 entrada `{"id": "dual-<provider>-<id>", "url": f"{base_url}/subs/dual/<provider>/<id>/<S>/<E>.srt", "lang": "pob"}` **depois** das PT-BR. Rota nova `/subs/dual/...`: pega a inglesa, traduz com `ensure_auto_translated` (mesmo cache) e monta um SRT em que cada fala tem a linha PT em cima e a inglesa embaixo em itálico (`<i>...</i>`), tempos da inglesa. Arquivo PT (dublado) continua devolvendo lista vazia.

## 5. 🎲 Sorteio do dia
Catálogo novo (filme e série, links pessoal e Kids, logo depois do Top 10 no manifest): id `comet_lucky`, nome `🎲 Sorteio do dia`, 10 itens escolhidos ao acaso **mas fixos no dia** (semente = data + tipo) entre: dublados prontos (`⚡ Pronto dublado`) com nota TMDB ≥ 7 que **não** estão no histórico do Stremio (`stremio_library`). Kids: só da lista Kids. Mesma capa deitada das outras fileiras.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (polling `curl` no `manifest`); `git -C /opt/comet add -N` dos novos; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem URL/token)
1. Meta One Piece: 5 episódios filler conhecidos (ex.: absolutos 54–61 são filler) com `🟡 Filler`; 3 canon sem sufixo. Naruto Shippuden idem. Uma série não-anime (`tt0903747`) sem nenhum sufixo.
2. Meta Breaking Bad S02E01: overview com `📺 Na temporada anterior:`.
3. `bingeGroup` do `▶ Assistir` de Ben 10 `tt2293002:1:2` = `comet|best|pt`.
4. Legendas de um filme com arquivo inglês: entrada `dual-`; baixe: falas com 2 linhas (PT + `<i>EN</i>`), mesma contagem da inglesa.
5. `comet_lucky` filme e série: 10 itens, igual em 2 pedidos seguidos; nenhum do histórico.
6. Manifest: ordem dos catálogos antigos preservada (só o novo depois do Top 10).
7. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`. Acrescente em `scripts/regress.py` os testes `filler` (One Piece tem ≥ 1 `🟡 Filler`), `bingegroup` e `sorteio` e rode a suíte com eles.

Responda em no máximo 8 linhas: arquivos alterados e resultado da verificação.
