# Tarefa: nova fonte do Comet para 2 sites BR de dublado (`BrSitesScraper`)

Medido em 30/10/2026: `filmestorrent.tv` e `apachetorrents.com` trazem torrents dublados que o Comet ainda não acha (ex.: GoT S07E02 `[1080p] [DUAL] filmestorrent.tv`; Transformers O Início `1080p.WEB-DL.DUAL.5.1`). Cada post desses sites tem **vários magnets** (um por qualidade/áudio). Por isso a fonte é um scraper Python dentro do Comet, e não um indexador do Prowlarr.

## Contexto
- Código do Comet: A71, chroot, `/opt/comet` (Android: `/data/debian/opt/comet`). Edite lá.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (Android root) e `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian; `git` só existe aqui).
- Enviar arquivo: `adb -s 192.168.3.44:5555 push <arq> /data/local/tmp/<nome>` (um por vez, nome completo), depois mova. Tudo em **LF**.
- Os scrapers são descobertos sozinhos por `comet/scrapers/manager.py`: classe `XxxScraper(BaseScraper)` em `comet/scrapers/xxx.py` é ligada por `settings.SCRAPE_XXX`. Use **`comet/scrapers/peerflix.py`** como modelo (usa `impersonate = "chrome"` e `self.session`). Veja também como `SCRAPE_PEERFLIX` aparece em `comet/core/models.py` (lista na linha ~62 e campo na ~250) e repita para `SCRAPE_BRSITES`.
- `ScrapeRequest` (`comet/scrapers/models.py`): `media_type`, `media_only_id`, `title`, `year`, `season`, `episode`, `query_titles` (inclui o título em português quando existe).
- Retorno: lista de dicts `ScrapeResult` (`title`, `infoHash` hex minúsculo de 40 chars, `fileIndex` None, `seeders` None, `size` None, `tracker`, `sources` = lista de `tracker:...` do magnet).
- **PROIBIDO:** imprimir chaves (RD, Prowlarr, DuckDNS; a chave do RD aparece nas URLs do `comet.log`, não mostre essas linhas), commit, mexer no AdGuard. **NÃO rode tarefas em segundo plano.**

## O que fazer

### 1. `comet/scrapers/brsites.py` → `class BrSitesScraper(BaseScraper)`, `impersonate = "chrome"`
Sites (dict fixo no arquivo):
| site | busca | tracker |
|---|---|---|
| `https://filmestorrent.tv` | `/?s=<consulta>` | `BRSites|FilmesTorrent` |
| `https://apachetorrents.com` | `/index.php?busca=<consulta>` | `BRSites|ApacheTorrent` |

Fluxo por site (sites em paralelo com `asyncio.gather`):
1. **Consultas:** cada título de `request.query_titles` (máx. 2), sem o ano e sem pontuação. Em série, não acrescente `SxxEyy` (os sites não acham assim).
2. **Página de busca:** colete os links de posts do próprio domínio cujo slug contenha todas as palavras significativas do título normalizado (minúsculo, sem acento, palavras com 3+ letras; se o título só tiver palavras curtas, use todas). Ignore links de categoria/tag/page. Máximo **4 posts** por site.
   - **Filme:** se `request.year` existir e o slug ou o texto do post tiver outro ano entre 1900 e 2099 diferente de `year` e `year±1`, descarte o post.
3. **Post:** extraia todos os `magnet:?` (troque `&amp;` por `&`). `infoHash` = btih em hex minúsculo (se vier em base32 de 32 chars, converta). `title` = `dn` decodificado (`urllib.parse`), limpo:
   - remova no começo `[ACESSE ...]` e prefixos de domínio como `HIDRATORRENTS.ORG..`, `VEMTORRENT.COM.`, `COMOEUBAIXO.COM.`, `VAMOSTORRENT.COM.` (regex `^\s*\[?ACESSE [^\]]*\]\s*` e `^(?:[A-Za-z0-9-]+\.(?:org|com|net|tv|to|biz))\.*\s*`, sem diferenciar maiúsculas);
   - **mantenha** palavras como `DUBLADO`, `DUAL-AUDIO`, `LEGENDADO` (transforme `-DUBLADO-DUAL-AUDIO-.` em ` DUBLADO DUAL AUDIO `) para a detecção PT-BR funcionar;
   - se o `dn` estiver vazio, use o título do post (`<h1>` ou `<title>`).
   `sources` = os `tr=` do magnet, no formato `tracker:<url>`.
4. Em série, **não** filtre por episódio aqui: o Comet já filtra depois. Mas descarte magnets cujo título claramente não é do seriado (o título limpo precisa conter a 1ª palavra significativa do título da série).
5. Deduplique por `infoHash`.
- **Tempo:** timeout de 8 s por requisição; o scraper inteiro não pode passar de **12 s** (`asyncio.wait_for`; se estourar, devolva o que já tiver). Erros: `log_scraper_error("BRSites", url, request.media_id, e)` e siga com o outro site.
- Só para IMDb (`media_only_id` começando com `tt`); para kitsu/anime devolva `[]`.

### 2. Configuração
- `comet/core/models.py`: `SCRAPE_BRSITES: bool | str = False` e acrescente `"SCRAPE_BRSITES"` na mesma lista em que está `"SCRAPE_PEERFLIX"`.
- `config/.env` (PC) **e** `/data/debian/opt/comet/.env` (A71): acrescente `SCRAPE_BRSITES=live`. Os dois arquivos precisam ficar iguais (confira MD5) e em LF; no A71 mantenha `chmod 600`.

### 3. Aplicar
1. `py_compile` dos arquivos alterados.
2. Reinicie o Comet: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`; espere o `manifest.json` voltar com loop de polling (sem `Start-Sleep`).
3. Regenere o patch: no chroot `git -C /opt/comet add -N comet/scrapers/brsites.py` e depois `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /tmp/x.patch`; copie para `/data/local/tmp/x.patch`, `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários com `unlink`. Zero `\r`.

## Fora do escopo
Qualquer outra mudança (detecção PT-BR, ordenação, outros scrapers, Prowlarr, watchdog, UI, README/HANDOFF).

## Verificação (rode e mostre)
Use um script Python no chroot (`/opt/comet/.venv/bin/python`, gravado em `/var/tmp/`, apagado no fim) que, para cada pedido, roda `DELETE FROM torrents WHERE media_id=?` em `/opt/comet/data/comet.db`, chama `http://127.0.0.1:8000/<b64>/stream/<tipo>/<id>.json` com o config `{"debridServices":[],"enableTorrent":true,"cachedOnly":false,"removeTrash":true,"maxResultsPerResolution":0}` e mostra: total, quantos com `🇧🇷` no `name`, tempo, e quantos streams têm `BRSites` no `description` (ou no `sources`/tracker; descubra onde o Comet mostra a fonte).
Pedidos e o esperado (valores de antes entre parênteses):
1. `movie/tt22084616` (total 671, PT-BR 21) → PT-BR **maior** que 21, tempo < 15 s.
2. `series/tt0944947:7:2` (PT-BR 10) → PT-BR **maior** que 10, tempo < 30 s.
3. `series/tt0944947:6:5` (PT-BR 16) → PT-BR **maior** que 16.
4. `series/tt2861424:6:1` (PT-BR 3) → não pode cair.
5. `movie/tt12042730` (PT-BR 17) → não pode cair.
Falsos positivos: liste os títulos dos streams `BRSites` de cada pedido e confirme que todos são do filme/episódio certo (nenhum de outro filme/temporada aparecendo no lugar errado).
Também: `.\scripts\a71.ps1 'grep -c "BRSites" /data/comet/comet.log'` sem erros em loop, e `MemAvailable` do A71 acima de 1,5 GB.

Responda em no máximo 5 linhas: arquivos alterados e os números de cada pedido (antes → depois, tempo).
