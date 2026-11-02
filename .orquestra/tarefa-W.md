# Tarefa W (experimento): fundo animado ao focar a capa + trailer garantido

## Pedido do usuário
Ao focar uma capa, o Stremio (sobretudo na TV) mostra a imagem de fundo (`background`) parada; ele queria "tipo Netflix, um vídeo curto". O protocolo de addons não tem campo de vídeo para o foco. Vamos **testar** se o app dele anima um fundo animado (WebP/GIF) e garantir trailer na página do título.

## Contexto
- Comet no A71, chroot, `/opt/comet`. Capas: `comet/services/artwork.py` (Pillow 11.3, cache em disco, rotas em `comet/api/endpoints/artwork.py`). Catálogos: `comet/services/catalogs.py`. Meta: `comet/services/meta_ptbr.py` (`_apply_tmdb_logo_and_trailer` já põe `trailerStreams` quando acha). TMDB: `movie|tv/<id>/images` (backdrops) e `/videos`.
- Memória do A71 é limitada: gere animações só sob demanda, uma por vez (semáforo 1), e guarde em disco.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes (nada de ffmpeg/yt-dlp); mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## 0. Sagas: tipo da fileira igual ao tipo do item (antes de tudo)
Hoje a fileira `🎬 Sagas` é `type: movie` (`comet_saga`) mas cada item é `type: series` (`cometsaga:<id>`). Alguns apps do Stremio estranham. Faça:
- Fileira da tela inicial: novo catálogo `type: "series"`, id `comet_sagas`, nome `🎬 Sagas`, na **mesma posição** em que está o `comet_saga` de filme hoje, com os itens `cometsaga:<id>` (`type: series`).
- O `comet_saga` de filme continua existindo **só para o Descobrir**: `genre` passa a `isRequired: true` (lista os filmes de uma saga escolhida) e sai da tela inicial.
- `meta/movie/cometsaga:<id>` e `meta/series/cometsaga:<id>` continuam respondendo (o de movie igual ao de series).
- Verifique: manifest com `series/comet_sagas` na posição antiga e `movie/comet_saga` com `genre` obrigatório; `catalog/series/comet_sagas.json` = 20 sagas; `meta/series/cometsaga:1241.json` = 8 vídeos; teste `saga` do `regress.py` ajustado.
## 1. Fundo animado (rota nova)
`GET /art/anim/<movie|tv>/<tmdb_id>.<webp|gif>`: pega até 6 backdrops do TMDB (`images?include_image_language=null,pt,en`, os de maior `vote_average`, sem texto), 780×439, e monta um loop de ~9 s: cada cena 1,2 s parada com leve zoom lento (Ken Burns, 3 %), transição em fusão de 0,3 s, ~10 fps. WebP com `quality=70`, `method=4`; GIF com paleta adaptativa. Cache em disco (`anim-<tipo>-<id>.<ext>`), tamanho alvo ≤ 1,5 MB (WebP) / ≤ 3 MB (GIF); se passar, reduza fps/cenas. Log: `🎞️ fundo animado <id>: <n> cenas, <kb> KB em <t>s`.

## 2. Fileira de teste (temporária)
Catálogo `comet_previewtest` (`type: movie`, nome `🧪 Teste: fundo animado`, só link pessoal, **primeira** posição do manifest) com 4 itens populares:
- A: `background` = WebP animado, `poster` normal;
- B: `background` = GIF animado, `poster` normal;
- C: `background` normal, `poster` = WebP animado (pôster 342×513 montado igual, a partir de 4 pôsteres/backdrops recortados);
- D: controle (tudo normal).
Nome de cada item com a letra no fim (ex.: `Duna (A · WebP)`), para o usuário dizer qual animou. Ligar/desligar por `PREVIEW_TEST_ROW: bool = True` em `models.py`.

## 3. Trailer garantido na página do título
Em `meta_ptbr.py`: se o TMDB não tem trailer `pt-BR`, use o de `en` (Trailer > Teaser), e coloque os dois quando existirem: `trailerStreams = [{"title": "Trailer dublado"/"Trailer legendado"/"Trailer", "ytId": …}]` (PT primeiro). Também `links` com categoria `Trailer` não precisa.

## Fora de escopo
Aplicar o fundo animado nas fileiras de verdade (só depois do resultado do teste).

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação
1. Gere os 4 itens: tempo e tamanho de cada animação; copie 1 WebP e 1 GIF para `downloads/anim-teste/` no PC.
2. Pico de memória do processo durante a geração (RSS antes/depois) e `MemAvailable`.
3. `meta/movie/<3 filmes>` e `meta/series/<2 séries>`: `trailerStreams` (quantos e títulos).
4. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK` (em primeiro plano, espere terminar).

Responda em no máximo 8 linhas.
