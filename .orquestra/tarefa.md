# Tarefa: capas montadas estilo Netflix (Top 10 com número gigante e capa deitada com logo)

## Contexto
- Código do Comet: A71, chroot, `/opt/comet` (Android: `/data/debian/opt/comet`). Pillow 11.3.0 **já está instalado** no venv (`/opt/comet/.venv`). Fontes: `/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf`, `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`.
- Arquivos: `comet/services/catalogs.py`, `comet/api/endpoints/catalog.py`, `comet/api/app.py`; novos `comet/services/artwork.py` e `comet/api/endpoints/artwork.py`.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (Android root) e `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian; `git` só existe aqui).
- Enviar arquivo: `adb -s 192.168.3.44:5555 push <arq> /data/local/tmp/<nome>` (um por vez, nome completo), depois `mv` para `/data/debian/...`. Tudo em **LF**.
- **PROIBIDO:** imprimir chaves/tokens (a chave do RD aparece nas URLs do `comet.log`), commit, instalar pacotes, mexer no AdGuard ou no `.env`. **NÃO rode tarefas em segundo plano.** Divida o trabalho em passos curtos.
- URL pública: `settings.PUBLIC_BASE_URL` (está definido no `.env`); se vazio, `f"{request.url.scheme}://{request.url.netloc}"`.

## 1. Gerador de imagens (`comet/services/artwork.py`)
- Baixa as imagens **só** de `https://image.tmdb.org/t/p/...` (aiohttp, timeout 10 s). Nome de arquivo aceito: regex `^[A-Za-z0-9_-]+\.(jpg|png)$`; qualquer outro → erro 404 (sem buscar nada).
- Geração com Pillow em `asyncio.to_thread`, no máximo 2 ao mesmo tempo (semáforo). Saída JPEG qualidade 85, `optimize=True`.
- Cache em disco `/opt/comet/data/img_cache/` (nome = sha1 dos parâmetros + `.jpg`; gravação atômica). Se existe, devolve direto. Apague arquivos com mais de 30 dias quando o tamanho da pasta passar de 300 MB (checagem no máx. 1 vez por hora).
- **Top 10** `render_top10(rank: int, poster_file: str) -> bytes`: tela **500×500**, fundo `#141414`. Pôster (`w500`) redimensionado para altura 500 (≈333×500), colado **encostado à direita**. Número `rank` (1–10) em LiberationSans-Bold bem grande (altura ≈ 470 px; para "10" reduza para caber), alinhado embaixo à esquerda, **começando atrás do pôster** (o pôster cobre um pedaço do número, como na Netflix): preenchimento `#141414` com contorno cinza claro `#bfbfbf` de 8 px (`stroke_width`/`stroke_fill`). Desenhe o número **antes** de colar o pôster.
- **Deitada com logo** `render_landscape(backdrop_file: str, logo_file: str | None) -> bytes`: tela **780×439**. Fundo = backdrop `w780` (preencher cortando ao centro). Gradiente escuro de baixo para cima (preto 85% → 0% na metade inferior) e outro da esquerda (preto 60% → 0% no terço esquerdo). Logo (`w500`, png com transparência) redimensionado para caber em 45% da largura × 32% da altura, mantendo proporção, colado embaixo à esquerda com margem 28 px. Sem logo → só backdrop + gradientes.

## 2. Rotas (`comet/api/endpoints/artwork.py`, registrar em `app.py` como `catalog`)
- `GET /art/top10/{rank}/{poster_file}` e `GET /art/land/{backdrop_file}` e `GET /art/land/{backdrop_file}/{logo_file}` (as duas últimas para com/sem logo). Também com prefixo `/{b64config}` não é necessário.
- Resposta `image/jpeg`, `Cache-Control: public, max-age=2592000, immutable`. Erro de download/arquivo inválido → 404.

## 3. Usar nas fileiras (`catalogs.py` + `catalog.py`)
- `get_catalog` recebe `base_url` (passado pela rota do catálogo; a chave do cache não muda).
- `comet_top10` (filme e série): `posterShape: "square"`, `poster = f"{base_url}/art/top10/{posição 1..10}/{poster_path sem /}"`.
- Fileiras deitadas (`comet_trending`, `comet_new`, com `CATALOG_LANDSCAPE`): troque a busca de imagens para `include_image_language=pt,en,null` e guarde no `landscape_map.json` (formato novo: `{"backdrop": <arquivo sem texto (iso null) preferido; senão qualquer>, "logo": <png pt > en, maior vote_average; ignore .svg> }`; entradas antigas no formato velho devem ser refeitas). `poster = f"{base_url}/art/land/{backdrop}/{logo}"` (ou sem logo). Mantém `posterShape: "landscape"`. Sem backdrop → pôster normal sem `posterShape`.

## Fora de escopo
Não mexer em stream, filtragem, legendas, meta, busca, index.html.

## Aplicar
1. `py_compile` dos arquivos alterados.
2. Reinicie: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`; espere `http://127.0.0.1:8000/manifest.json` no chroot (polling com `curl`, sem `Start-Sleep`).
3. Regenere o patch: no chroot `git -C /opt/comet add -N comet/services/artwork.py comet/api/endpoints/artwork.py` e `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp/x.patch`, `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários com `unlink`. Zero `\r`.

## Verificação
- `catalog/movie/comet_top10.json`: 10 itens com `posterShape` `square` e `poster` em `/art/top10/`. `catalog/series/comet_trending.json`: `poster` em `/art/land/`, diga quantos têm logo.
- Baixe no chroot 3 imagens: o `poster` do 1º e do 10º item do Top 10 de filmes e o do 1º item de `comet_trending` série, salve como `/var/tmp/art_top1.jpg`, `/var/tmp/art_top10.jpg`, `/var/tmp/art_land.jpg`; copie para `/data/local/tmp/` e `adb pull` para `.orquestra/` (mesmos nomes). **Não apague esses 3** (o revisor vai olhar).
- Tempo da 1ª geração e da 2ª (cache) de uma imagem.
- `/art/top10/1/..%2F..%2Fetc%2Fpasswd` e `/art/land/x.gif` → 404.

Responda em no máximo 5 linhas: arquivos alterados e resultado da verificação.
