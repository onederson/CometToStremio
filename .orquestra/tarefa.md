# Tarefa: Séries dubladas PT-BR — achar e corrigir onde o Comet perde temporadas/episódios BR

Contexto: PowerShell em `C:\Users\Vendel\Desktop\Projetos\a71\STREMIO`. Comandos no A71: `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Comet em `/opt/comet` (git com patch local; veja `git -C /opt/comet diff --stat`). Use `.venv/bin/python`. Reinício: `pkill -f "python -m comet.main"` (watchdog religa ≤30 s). `RTN_FILTER_DEBUG=True` no `.env` liga logs `_log_exclusion` (use só durante o diagnóstico e REMOVA ao final).

## Evidências (orquestrador, não refaça — parta daqui)
Série teste: Breaking Bad `tt0903747`, episódio `1:1`.
- Torrentio cru (`https://torrentio.strem.fun/stream/series/tt0903747:1:1.json`) retorna 77 streams, incluindo:
  - linha1 `Breaking Bad 2008 - 1ª Temporada Completa [4k] WWW.BLUDV.COM` / linha2 (arquivo) `Breaking.Bad.S01E01.4K.2160p.WEB-DL.5.1.x264.DUAL-WWW.BLUDV.COM.mkv` / `⚙️ Comando`
  - linha1 `Breaking Bad 1 Temporada BDRip blruay 720p dublado - derew` / linha2 `1 - Piloto.mp4` / `⚙️ ThePirateBay`
- O Comet recebe os 77 (log `found 77`), mas NENHUM dos dois chega à tabela `torrents` nem à resposta (`PT-BR: 0` na lista; banco só tem 55 linhas para tt0903747).
- `filter_worker` isolado (chamado direto em Python com title="Breaking Bad", year=2008, year_end=2013, media_type="series", aliases={}) ACEITA os dois e marca `pt` — então a perda ocorre em outra etapa (aliases reais? `TitleMatcher` com aliases TMDB? checagem de season/episode? global RTN filtering com `rtn_settings_default`? ranking `is_fetchable`? dedup? armazenamento?).
- `comet/scrapers/torrentio.py::_parse_stream` usa como `title` só a linha do ARQUIVO (última linha antes de `\n💾`), descartando o nome do torrent (linha 1). Para `1 - Piloto.mp4` isso perde o nome da série.
- RTN `parse()` classifica títulos BR com "Temporada"/"Completa" como `languages=['es']` (ex.: `Breaking Bad 2ª Temporada Completa 1080p Dual Audio` → `['es']`), mas extrai `seasons` corretamente.

## Passo A — Rastrear a perda (obrigatório, com prova)
Com `RTN_FILTER_DEBUG=True`, faça a busca real de `series/tt0903747:1:1` (config b64 modo torrent: `{"debridServices":[],"enableTorrent":true,"cachedOnly":false,"removeTrash":true,"maxResultsPerResolution":0}`; se houver cache, apague as linhas `torrents` de `tt0903747` antes) e encontre EXATAMENTE em que etapa/arquivo/linha cada um dos dois títulos acima é descartado. Instrumente temporariamente se necessário (logs extras), e remova a instrumentação depois. Relate a causa com o trecho de log.

## Passo B — Corrigir (mudanças mínimas, no patch existente)
1. Corrigir a(s) causa(s) encontrada(s) no Passo A.
2. `torrentio.py::_parse_stream`: quando a linha do arquivo NÃO contém o nome/título reconhecível (ex.: `1 - Piloto.mp4`) e a linha 1 (nome do torrent) contém, usar a linha 1 como `title` (o `fileIndex` continua apontando o arquivo certo). Não mude o comportamento para os casos em que a linha do arquivo já é boa. Explique a heurística.
3. Na detecção PT-BR (`apply_ptbr_detection`): se o título tem marcador BR de temporada (`\d+ª Temporada`, `Temporada \d+`, `\d+ Temporada`, `Temporada Completa`) E (marcador PT explícito OU tracker BR OU `dual`), garantir `pt` e REMOVER o `es` falso que veio só de "Temporada/Completa" (só remova `es` se não houver marcador espanhol real: `latino|castellano|spanish|esp\b|lat\b`).
4. Garantir que pacotes de temporada (`seasons=[N]`, `episodes=[]`) apareçam para pedidos de episódio daquela temporada (o Comet já suporta packs — confirme que não há regressão).

## Passo C — Validar (modo torrent, sem RD)
Para cada um, PT-BR antes → depois e até 5 títulos PT-BR:
- `series/tt0903747:1:1` (Breaking Bad), `series/tt0903747:3:5`
- `series/tt0944947:1:1` (Game of Thrones)
- `series/tt0121955:1:1` (South Park)
- `series/tt2861424:1:1` (Rick and Morty)
- um anime: `series/tt0388629:1:1` (One Piece)
- regressão filmes: `movie/tt12042730` deve manter ≥13 PT-BR e ordem PT-BR→resolução.
Confirme 0 falsos positivos (nenhum `Latino`/`Castellano`/`Spanish` marcado PT-BR) e que o `es` foi removido só quando falso.

## Passo D — Limpeza, patch, README
- Remova `RTN_FILTER_DEBUG` do `.env` (PC e A71) e qualquer instrumentação temporária; reinicie o Comet.
- `py_compile` dos arquivos alterados.
- Regenere `comet-patches\ptbr-first.patch` (TODO o diff Python, excluindo `comet/templates/index.html`; via `/data/local/tmp` + `adb pull`; LF; apague temporários).
- README Seção 0: nota curta sobre a correção de séries PT-BR.

## Regras
- Não altere `scripts/`, `comet-ui/`, Caddy, StremThru, Prowlarr, AdGuard.
- Não imprima chaves.

## Resposta final (máx. 12 linhas)
Causa exata da perda (etapa/arquivo/linha + log), correções feitas (arquivos), tabela PT-BR antes→depois por título, exemplos, falsos positivos, pendências.
