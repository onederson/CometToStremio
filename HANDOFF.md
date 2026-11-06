# HANDOFF: Comet Stremio no Galaxy A71 (para outra IA continuar)

*Última atualização: 05/11/2026 (horário de Brasília)*

Este é o documento de passagem. Ele resume **tudo o que foi feito, o estado real verificado, as regras do projeto, como testar e o que vem a seguir**. O `README.md` (Seção 0 e Mapa de arquivos) tem os detalhes da instalação. A Fase 1 (AdGuard) está em `README adguard contexto.md`.

---

## 1. Regras obrigatórias (leia primeiro)

### Modo de trabalho (do `CLAUDE.md`)
- A IA principal é **orquestradora**. Ela escreve a especificação em `.orquestra/tarefa.md`, delega ao `agy` (CLI do Antigravity) e revisa com `git diff --stat` / `git diff`, além de uma verificação independente no aparelho. Se aprovar, faz `git add -A`.
- **Quem roda o `agy`:** desde 30/10/2026 o usuário autorizou a IA a rodá-lo **ela mesma, em segundo plano** (PowerShell com `run_in_background`, saída redirecionada para um log). A IA roda etapa por etapa, revisa cada uma, corrige e **entrega só o resultado final**. Se o ambiente bloquear, peça ao usuário para rodar com `! agy ...`. Comando padrão:
  ```
  agy -p "Execute exatamente o que está em .orquestra/tarefa.md. Não faça nada fora do escopo. Ao terminar, rode a verificação descrita e responda em no máximo 5 linhas: arquivos alterados e resultado da verificação." --model gemini-3.8-flash-high --dangerously-skip-permissions --print-timeout 900s
  ```
  Para tarefas difíceis, use `--model gemini-4-argon-high` (cota esgotada em 30/10/2026, volta em ~5 dias). Para continuar a mesma conversa, use `-c`. Nunca use os modelos `claude-*` do agy.
- **Lições sobre o agy (flash):**
  - Tarefas grandes estouram o tempo: divida em etapas e use `--print-timeout 1800s`.
  - Ele às vezes dispara tarefas em segundo plano e sai no meio. Escreva no prompt: "NÃO rode tarefas em segundo plano".
  - Ele relata "aprovado" mesmo quando a própria validação falha. **Sempre confira no aparelho** antes do `git add -A`.
- Mudanças triviais (menos de ~20 linhas) a IA faz direto. No máximo 3 rodadas por tarefa; depois disso a IA corrige diretamente.
- **Commit só quando o usuário pedir.** Escreva a mensagem num arquivo temporário e use `git commit -F arquivo`.

### Segurança e restrições
- **Nunca imprima nem versione:**
  - o token do DuckDNS (`config/duckdns.token`, que está no `.gitignore`);
  - a chave do Real-Debrid;
  - a API key do Prowlarr.
- Use somente o domínio DuckDNS **`a71comet.duckdns.org`**. A conta tem 2 domínios; não mexa no outro.
- E-mail do git **só neste repo** (config local): `wandersonks02@gmail.com`.
- **Não mexa no AdGuard Home nem em nada da Fase 1.** Única exceção: o watchdog do Comet escreve `-1000` em `/proc/<pid>/oom_score_adj` do processo do AdGuard (pedido do usuário), sem tocar em arquivos de `/data/adguard/`.
- **Não contorne o bloqueio 451 do Real-Debrid** (DMCA, `infringing_file`). O usuário pediu duas vezes e foi recusado. O que existe é legítimo: troca automática para outro torrent e fallback P2P rotulado. Não proponha truques para fazer o RD servir um hash bloqueado.
- **Não sugerir outro debrid nem outra assinatura**: o usuário não vai assinar.
- Idioma das respostas ao usuário: **PT-BR**, linguagem simples.

### Pegadinhas do ambiente (Windows + PowerShell)
- **Comandos no A71:**
  - Rode tudo via `.\scripts\a71.ps1 '<cmd>'` (root Android) ou `.\scripts\a71.ps1 -Chroot '<cmd>'` (dentro do Debian).
  - `git` só existe dentro do chroot.
- **Comandos que o classificador bloqueia:**
  - Comandos contendo `rm /tmp...`. Use `unlink` ou scripts que se apagam sozinhos.
  - `Start-Sleep`. Use loops de polling.
- **Arquivos enviados ao A71:**
  - `adb push`: envie **um arquivo por vez** com o nome final completo. Com vários arquivos de uma vez, o Windows trunca o último caractere do nome.
  - Scripts, `.env` e patch precisam estar em **LF** (zero `\r`). O `deploy_patches.ps1` recusa CR.

---

## 2. Objetivo do usuário

Um addon Stremio próprio (Comet + Real-Debrid), rodando no Galaxy A71, com a seguinte ordem de resultados:

1. **Primeiro, conteúdo PT-BR** (dublado / dual áudio), agrupado por **4K → 1080p → 720p** e com o rótulo **🇧🇷 PT-BR**.
2. Depois, todo o resto.
3. Quando não houver PT-BR, inglês serve. Em anime, japonês.

Torrents bloqueados pelo RD (451) não aparecem como RD: viram troca automática ou `⚠️ P2P (bloqueado no RD)`. O usuário quer **"todos os conteúdos possíveis"**: dublados, lançamentos, séries e anime. Ele achava que o RD "tinha tudo" e se frustrou ao ver que não; já foi explicado que o RD só tem o que existe em torrents que o addon encontra. O caminho para mais conteúdo é **achar mais torrents** (ver Seção 8).

Comet, StremThru, Prowlarr, Caddy e AdGuard **não podem ser fechados pelo Android**. Se faltar memória, o Android deve matar coisas dele mesmo (apps em segundo plano) e o FlareSolverr.

---

## 3. Arquitetura (estado verificado em 30/10/2026)

| Componente | Onde | Porta | Observação |
|---|---|---|---|
| Galaxy A71 | `192.168.3.44`, ADB Wi-Fi `:5555` | — | Android 14 (crDroid), Magisk root, ~3,4 GB disponíveis + swap |
| Debian 13 chroot | `/data/debian` | — | Montado por `/data/comet/chroot.sh` |
| **Comet** (`g0ldyy/comet` @ `f56677f`) | `/opt/comet` (chroot), `.venv`, Python 3.13, SQLite `data/comet.db` | 8000 | Patch local `comet-patches/ptbr-first.patch`: 19 arquivos Python |
| **Caddy** + DuckDNS (DNS-01, Let's Encrypt) | `/etc/caddy/Caddyfile` | 443 | `https://a71comet.duckdns.org` → 127.0.0.1:8000 |
| **StremThru** v0.105.4 local | `/usr/local/bin/stremthru` | 127.0.0.1:8080 (+ Caddy `:8443`) | Ponte Comet → Real-Debrid (a instância pública dava timeout). `STREMTHRU_FEATURE=torz,stremio_store`, `STREMTHRU_BASE_URL=https://a71comet.duckdns.org:8443`: addon **Store** (biblioteca do RD) em `https://a71comet.duckdns.org:8443/stremio/store/configure` |
| **Prowlarr** v2.7.0.5723 | `/opt/prowlarr`, dados em `/var/lib/prowlarr` | 127.0.0.1:9696 | Indexadores: Catálogo BeTor (BR), Knaben, TorrentsCSV; proxy FlareSolverr integrado |
| **FlareSolverr** v3.5.2 | `/opt/flaresolverr` (chroot), `.venv` | 127.0.0.1:8191 | Proxy anti-Cloudflare para Prowlarr; Chromium e chromedriver arm64 do sistema (`comet-patches/flaresolverr-arm64.patch`); watchdog mata se passar de 1200 MB PSS; oom 200 (morre antes dos serviços) |
| **Watchdog** | `/data/comet/watchdog.sh` (= `scripts/watchdog.sh`, MD5 conferido) | — | A cada 30 s religa serviços; proteção oom (-1000/200), free_mem e cap de logs a 5 MB |
| Boot | `/data/adb/service.d/comet.sh` | — | Sobe o watchdog. Reboot já validado |
| Apps do Android | `/data/comet/android-apps.sh` (= `scripts/android-apps.sh`) | — | `disable` aplicado: GameSpace, OmniJaws, Settings Intelligence, Emergency. `enable` reverte. Alertas da Defesa Civil mantidos de propósito |

- **Logs:** `/data/comet/{comet,caddy,stremthru,prowlarr,flaresolverr,watchdog}.log`.
- **Reiniciar o Comet:** `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`. O watchdog religa em até 30 s.
- **Memória (watchdog):**
  - A cada volta, `protect()` põe `oom_score_adj=-1000` em Comet (e filhos/forkserver), StremThru, Prowlarr, Caddy, AdGuardHome, os dois watchdogs; e `200` no FlareSolverr/Chromium.
  - `free_mem()` roda `am kill-all` se `MemAvailable` < 600 MB (no máximo 1x a cada 5 min).
  - `check_flaresolverr_mem()` mata o FlareSolverr se a soma de **PSS** passar de 1200 MB. Use PSS e não RSS: RSS conta várias vezes a memória compartilhada do Chromium e dava 1,25 GB falsos logo na subida.
- **Reiniciar o watchdog** (depois de trocar `/data/comet/watchdog.sh`): `kill -9 $(cat /data/comet/watchdog.pid)` e depois `nohup /system/bin/sh /data/comet/watchdog.sh >/dev/null 2>&1 &`. Um `kill` simples só age quando termina o `sleep 30`, e o novo watchdog sai sozinho se o antigo ainda estiver vivo.

**Fontes de scraping** (`config/.env`, que está no `.gitignore` e é instalado em `/opt/comet/.env`):

| Fonte | Configuração | Situação |
|---|---|---|
| Torrentio | — | Principal |
| MediaFusion | midnightignite | ✅ Ativo (`mediafusionfortheweebs.midnightignite.me`, parsing corrigido) |
| Zilean | — | Ativo |
| StremThru scrape | público | Ativo |
| TorrentsDB | — | ❌ Desligado (`SCRAPE_TORRENTSDB=False`, origem 502) |
| Nyaa | anime only | Ativo |
| SeaDex | anime only | ✅ Ativo |
| Peerflix | — | ✅ Ativo (`impersonate="chrome"`) |
| Comet | feels.legal + Midnight | ✅ Ativo: `COMET_URL=["https://comet.feels.legal","https://cometfortheweebs.midnightignite.me"]`. A Midnight tem índice próprio (inclui BitMagnet/DHT): GoT `7:2` 771→1059 (PT-BR 14→18), Ben 10 `1:2` PT-BR 17→22, sem custo de tempo |
| Prowlarr | `PROWLARR_INDEXERS=["1","2","3"]` | Ativo |
| Addons | `SCRAPE_ADDONS=live`, `ADDONS_URL=[BeTor v3, BestCine]` | ✅ Ativo (`comet/scrapers/addons.py`). Ganho pequeno (+1 por título). O BestCine põe o título em PT ("Transformers: O Início") e marca "Dual" até em YTS em inglês: por isso o título sintético usa `request.title` e não leva rótulos de idioma, e o rótulo `[bludv]` do BeTor não entra no tracker. Sem isso, os falsos PT-BR contaminavam o mesmo hash nas outras fontes (Transformers One 4→16 falsos) |
| BRSites | `SCRAPE_BRSITES=live` | ✅ Ativo: scraper próprio (`comet/scrapers/brsites.py`) de `filmestorrent.tv` e `apachetorrents.com`, todos os magnets de cada post |

Flags importantes do `.env`:
- `PTBR_FIRST=True`
- `SMART_LANGUAGE_DETECTION=True`
- `INDEXER_LANGUAGES=["pt","en"]`
- `DOWNLOAD_GENERIC_TRACKERS=True`
- `STREMTHRU_URL=http://127.0.0.1:8080`
- `HIDE_DEBRID_BLOCKED`: padrão True no patch
- `P2P_FALLBACK_FOR_BLOCKED=True`
- `DEMOTE_CAM`: padrão True no patch (CAM/TS/TC/SCR no fim da lista com `🎦 CAM`)
- `DEBRID_PRECHECK=True`
- `DEBRID_PRECHECK_MAX_PER_HOUR=20`

**No Stremio:** o usuário configura o RD pela página `/configure` (traduzida para PT-BR em `comet-ui/index.html`). A chave RD fica só na URL do manifest instalado.

---

## 4. Histórico do que foi feito (em ordem)

1. **Fase 2 base** (commit `cbe21b8`):
   - Rootfs Debian, `setup_comet.sh` (Python 3.13, Rust, `uv`) e `.env` SQLite / 1 worker.
   - Caddy + DuckDNS HTTPS.
   - Watchdog + boot Magisk, com reboot validado.
2. **PT-BR primeiro** (commit `17cec22`):
   - Detecção ampliada (trackers BR, marcadores no título, `PTBR_RELEASE_GROUPS`).
   - Ordenação PT-BR no topo por resolução, preservada no corte de `maxResultsPerResolution`.
   - Rótulo `🇧🇷 PT-BR`.
   - `/configure` traduzida.
3. **StremThru local + correções de reprodução** (commit `372e0e8`):
   - `magnet_error` no RD acontecia porque os hashes chegavam sem trackers. Agora usa 20 trackers públicos (`ngosang/trackerslist`).
   - StremThru compilado e rodando localmente.
4. **Filtro 451** (itens 4 a 7 no commit `6615563`):
   - Tabela SQLite `debrid_blocked_hashes`, criada pela migração `2026102901_debrid_blocked_hashes`.
   - O 451 é gravado em `comet/debrid/stremthru.py` e logado como `🚫 RD bloqueou (451)`.
   - `comet/api/endpoints/stream.py` esconde esses hashes daquele debrid; o P2P continua intacto.
5. **Prowlarr**: instalado e integrado (`SCRAPE_PROWLARR=live`, busca também por título PT). Ganho em filmes: `tt12042730` 11→13 PT-BR, `tt22084616` (na verdade *Spider-Man: Brand New Day*, não Transformers) 16→17. A lista de indexadores excluídos e o motivo está no README, Seção 0.
6. **Watchdog**: supervisão do Prowlarr + cap de logs.
7. **Séries dubladas PT-BR**. Causa encontrada:
   - **(a)** `torrentio.py` testava `"\n💾" in title_full` e falhava quando havia a linha de seeders (`\n👤 7 💾`). Também usava só o nome do arquivo (ex.: `1 - Piloto.mp4`), que não contém o nome da série.
   - **(b)** O RTN marca títulos BR com "Temporada/Completa" como `es`.
   - **(c)** Pacotes de temporada (`seasons=[N], episodes=[]`) eram descartados por `reject_unknown_episode_files=True`, em `match_parsed_episode_target` (`comet/utils/parsing.py`).

   Correções:
   - `torrentio.py`: `METADATA_SPLIT_PATTERN`, `BARE_EPISODE_PREFIX_PATTERN` e `_select_stream_title`. Usa o arquivo quando ele é reconhecível; senão cai para a linha 1 (nome do torrent), mantendo o `fileIndex`.
   - `filtering.py::apply_ptbr_detection`: `_PTBR_SEASON_RE`, com marcador de temporada BR + PT, tracker BR, `dual` ou grupo BR → `pt`. Remove o `es` falso, mas não quando há `latino`, `castellano`, `spanish`, `español` ou `spa`.
   - `orchestration.py::TorrentManager`: `_is_matching_season_pack`, `_matches_requested_scope`, `_live_torrent_priority`, dedup que une `pt` e `sources`, e `_append_cache_file_infos` passou a manter os packs.
8. **451 sem perder o conteúdo** (commit `7642b2a`): `P2P_FALLBACK_FOR_BLOCKED` (hash bloqueado vira stream P2P rotulado), `DEBRID_PRECHECK` (`comet/services/debrid_precheck.py`, testa até 3 hashes PT-BR em segundo plano, máx. 20/h, tabela `debrid_verified_hashes`), e troca automática no playback (`_try_playback_fallback_on_451` em `playback.py`, até 3 candidatos, mesma resolução + PT primeiro).
9. **Anime** (commit `7642b2a`): episódio absoluto (`episode_index.py::get_absolute_episode`), packs/batches sem temporada, filtro de arcos (Seção 7, item 2) e busca ao vivo por episódio (Seção 7, item 3).
10. **Fontes** (commit `7642b2a`): MediaFusion (Midnight) com parsing corrigido, Peerflix, Comet `feels.legal`, SeaDex; TorrentsDB desligado.
11. **Memória + FlareSolverr** (commit seguinte ao `7642b2a`):
    - Watchdog com `protect()`, `free_mem()` e `check_flaresolverr_mem()` (Seção 3).
    - `scripts/android-apps.sh` desativando 4 apps do Android.
    - FlareSolverr v3.5.2 em `/opt/flaresolverr` com Chromium/chromedriver do Debian (`comet-patches/flaresolverr-arm64.patch`), proxy criado no Prowlarr com a tag `flaresolverr` (id 1).
    - Experimento de indexadores sem ganho, desfeito (Seção 7, item 5).
12. **CAM no fim da lista** (`DEMOTE_CAM=True`): `filtering.py::is_cam_release` (usa `parsed.quality` do RTN: `CAM`, `TeleSync`, `TeleCine`, `SCR`). Em `stream.py`, a ordem fica avisos → PT bons → outros bons → PT CAM → outros CAM, com `🎦 CAM` no nome e aviso na descrição; o corte por resolução e o precheck também os deixam por último. Em `playback.py`, a troca do 451 só usa CAM se não houver outro candidato (antes ela escolhia CAMRip com marca d'água "1xbet"). Com "Remover lixo" ligado no `/configure` (o usuário usa assim), os CAM nem aparecem na lista, mas a troca do 451 lê o banco direto.
13. **Biblioteca do RD:** StremThru com o addon Store ligado e exposto pelo Caddy em `:8443` (`config/Caddyfile`, `scripts/watchdog.sh`).
15. **Mais fontes (30/10/2026, noite):** Comet Midnight como 2ª instância (ganho real) e scraper `Addons` (BeTor v3 + BestCine, ganho pequeno). Testados e descartados: Torrentio com todos os provedores (o padrão já inclui os BR), Brazuca Torrents (fora do ar), NekoBT (zero ganho, +11 s no One Piece), AnimeTosho (API fechada, 403; `feed.animetosho.org` não existe mais), DMM ingest (baixa GBs e duplica o Zilean), MediaFusion ElfHosted (0 resultados), BitMagnet próprio (a Comet Midnight já traz BitMagnet), outros addons BR mortos (KingVOD, Magneto, BluDV stream, Animes BR, Skyflix, AnimesDigital, MyCine, CineTorrent e Mico-Leão vazios).
16. **Links diretos dentro do Comet (`DIRECT_ADDONS_URL`):** FenixFlix (`https://fenixflix.fenixhub.online`) e FrostStream (`https://froststream.cloutteam.com`) servem vídeo HTTP direto (não é torrent nem RD, então o 451 não se aplica). Em vez de instalá-los no Stremio, o Comet busca os streams deles ao vivo, em paralelo com o scraping (`comet/services/direct_addons.py`, cache em memória de 10 min, nada no banco, timeout `DIRECT_ADDONS_TIMEOUT=8`), e os mescla com rótulo `🌐 <addon>`. Ordem: PT-BR em cache no RD (⚡) → diretos PT-BR → PT-BR não cacheados/P2P → outros → diretos não PT → CAM. Conferido: Ben 10 Omniverse `1:2` passa a abrir com 5 dublados diretos no topo (antes só RD⬇️ bloqueados), Devoradores de Estrelas com 20 diretos (4K dublado), Demon Slayer `1:1` com 12. Se os links mudarem/caírem, basta tirar a URL do `.env`.
17. **Legendas PT-BR dentro do Comet (31/10/2026):** o manifest ganhou o recurso `subtitles` (o usuário precisa reinstalar o addon). `comet/services/subtitles.py` busca PT-BR em OpenSubtitles (API REST com login; conta **grátis, 20 downloads/dia**), SubSource (`language=brazilian_portuguese`, um `movieId` por temporada) e SubDL (`BR_PT`, pouca cobertura). Dá nota pela semelhança com o `filename` que o Stremio manda (hash +1000, grupo +300, serviço/tipo de fonte ±150/100, resolução, Jaccard; episódio errado é descartado). Download só quando o player pede (`/subs/<fonte>/<id>/<S>/<E>.srt`), cache em disco em `data/subs_cache` (30 dias), sempre UTF-8. Cota do OpenSubtitles: com 406/`remaining` 0, os itens dele fora do cache somem da lista até o `reset_time_utc`.
    - **Sincronia** (`comet/services/subtitle_sync.py`, Python puro, sem numpy): se a 1ª PT-BR não é da mesma release do arquivo e há legenda inglesa/PT-BR da mesma release no SubSource/SubDL (referência; o OpenSubtitles não é usado para não gastar cota), entram no topo 2 variantes `sync-...` (`/subs/sync/...`). Alinha por máscara de fala de 100 ms → 20 ms, testando razões de fps (25/23,976/24) e deslocamento de ±120 s; só aplica se o encaixe ficar ≥ 0,55 e melhorar ≥ 0,05, senão serve a original. Não corrige cortes diferentes no meio. Conferido: GoT `7:2` BluRay, legenda 73 s atrasada, encaixe 0,63→0,97; teste sintético (25 fps + 3,7 s) volta com 12 ms de erro, em 0,09 s.
    - O `alass` (sincronizador em Rust) foi descartado: o modo automático bloqueou baixar/compilar código externo.
    - **Cuidado:** o SubDL devolve a chave da API dentro do campo `url`. Nunca imprima respostas cruas dele. O id `subdl-<base64>` guarda só o caminho, sem a chave.
18. **Spin-off/continuação misturados (31/10/2026):** em Bleach (`tt0434665`) S01E01 o Comet entregava Thousand-Year Blood War S01E01 (14 de 50 streams). Causa: os aliases de `tt0434665` (`media_metadata_cache.aliases_json`) vêm contaminados com nomes do TYBW, porque a fonte de aliases trata o TYBW como continuação. Correção (`comet/metadata/siblings.py`): "irmãos" = outras obras do **mesmo tipo** na busca do Cinemeta cujo nome é o nosso título + palavras extras (ex.: `tt14986406` Bleach: Thousand-Year Blood War; Naruto → Shippuden; Ben 10 → Omniverse/Alien Force/Ultimate Alien). O nome deles e os aliases deles com esse prefixo viram nomes bloqueados (igualdade exata do `scrub`): saem dos nossos aliases e o torrent com esse `parsed_title` é rejeitado no `TitleMatcher` (vale também para torrents já salvos no banco). Arcos da mesma entrada do IMDb não são afetados (Demon Slayer T3 "Entertainment District Arc" segue aceito). Cache de 24 h em memória. Resultado: Bleach `1:1` 50→36 sem TYBW; TYBW, Demon Slayer `3:1`, Naruto, Shippuden, Ben 10 e Omniverse sem mudança relevante.
    - Não resolvido: obras com **o mesmo nome** exato (ex.: Doctor Who 2005 recebe 4 arquivos "60th Anniversary Specials S01E01", que o RTN lê como "Doctor Who").
    - O FenixFlix/FrostStream e as legendas respeitam o ID pedido; quando o usuário abre o Bleach de 2004 por engano, eles trazem 2004 (certo para o ID).
19. **Frontpage estilo Netflix (31/10/2026):** o Comet agora tem 19 catálogos (`comet/services/catalogs.py`, rota `comet/api/endpoints/catalog.py`): "Em alta" (filmes e séries, TMDB trending da semana), uma fileira de séries e uma de filmes por streaming (Netflix, Prime Video, Disney+, HBO Max, Apple TV+, Paramount+, Globoplay, Crunchyroll; TMDB `discover` com `watch_region=BR`) e "Animes". Tudo em pt-BR (nome, pôster, sinopse); os itens usam o ID do IMDb, então stream/legendas/links diretos funcionam igual.
    - Fileira padrão: popularidade; séries só com episódio nos últimos 2 anos, `vote_count >= 200` e sem jornal/reality/novela/talk show; filmes dos últimos 4 anos. Em "Descobrir" há filtro: Lançamentos, Mais bem avaliados e gêneros em PT-BR (aí entram os títulos antigos).
    - `.env`: `CATALOGS_ENABLED`, `CATALOG_REGION`, `CATALOG_LANGUAGE`, `CATALOG_PROVIDERS` (lista e ordem das fileiras). Mapa TMDB→IMDb em `/opt/comet/data/catalog_cache/imdb_map.json`; resultado em memória por 6 h (vazio não é guardado).
    - Limites do Stremio: a tela inicial é só fileiras de catálogos (sem banner gigante/trailer automático); a ordem é a ordem dos addons instalados; a página de detalhes continua vindo do Cinemeta. Para o Comet aparecer primeiro e tirar as fileiras do Cinemeta é preciso reordenar/editar os addons (Stremio Addon Manager).
    - **Comet no lugar do Cinemeta:** recurso `meta` próprio (`comet/services/meta_ptbr.py`, rota `meta.py`): pega o meta do Cinemeta (numeração de temporadas/episódios intacta) e troca título, sinopse, pôster, gêneros e nomes/sinopses de episódio pelo TMDB pt-BR (episódios só quando a temporada tem a mesma contagem dos dois lados; anime como One Piece fica com os nomes do Cinemeta). Cache 12 h. Busca: catálogos `comet_search` (filme/série, `search` obrigatório) = TMDB pt-BR + Cinemeta. Com isso o usuário pode desinstalar o Cinemeta e o Trakt.
    - **Visual estilo Netflix (31/10/2026):** 31 catálogos na ordem 🔥 Em alta → 🆕 Lançamentos (últimos 120 dias) → por serviço: ⭐ Originais X (séries por `with_networks`: Netflix 213, Disney+ 2739, Prime 1024, HBO Max `3186|49`, Apple 2552, Paramount+ 4330; Globoplay/Crunchyroll sem) + X séries + X filmes → 🏆 Aclamados → 🍥 Animes → Busca. "Em alta" e "Lançamentos" são fileiras deitadas (`posterShape: landscape`, backdrop w780 com o nome escrito quando o TMDB tem; cache em `data/catalog_cache/landscape_map.json`). A página do título ganhou logo oficial (png, pt > en) e trailer PT-BR (YouTube, pt > en). `.env`: `CATALOG_ORIGINALS`, `CATALOG_LANDSCAPE`, `CATALOG_PROVIDERS` (quais serviços e a ordem).
    - Cinemeta não pode ser desinstalado (addon protegido): no Stremio Addon Manager, colocar o Comet acima dele e remover todos os catálogos do Cinemeta.
    - **Rodada 2 do visual (31/10/2026):** 42 catálogos. Ordem: 🔟 Top 10 de hoje (trending/day, 10 itens) → 🔥 Em alta → 🆕 Lançamentos → blocos de serviço (⭐ Originais, séries, filmes) intercalados com temas (🇧🇷 Nacionais, 💥 Ação e aventura, 🕵️ Crime e suspense, 😂 Comédias, 🇰🇷 Doramas, 👻 Terror, 🧸 Para a família, 🌍 Documentários; Ação/Comédias/Terror sem animação/família) → 🏆 Aclamados → 🍥 Animes. Pôsteres w500.
    - **Versão do manifest automática:** `2.1.<hash dos catálogos/recursos>`. Com a versão fixa `2.0.0` o Stremio do usuário ficou com a lista antiga; agora qualquer mudança de catálogo muda a versão e o Stremio atualiza o addon.
    - Página do título: fundo `original`, 1ª linha da sinopse com classificação BR colorida (🟢 Livre, 🔵 10, 🟡 12, 🟠 14, 🔴 16, ⚫ 18) e `📺` onde está disponível (assinatura no BR), duração `2h 18min`.
    - **Capas montadas (31/10/2026):** Pillow 11.3.0 instalado no venv (`uv pip install`, também no `scripts/setup_comet.sh`). `comet/services/artwork.py` + rotas `/art/top10/{n}/{poster}` (500×500, número contornado atrás do pôster; `posterShape: square`) e `/art/land/{backdrop}/{logo}` (780×439, backdrop sem texto + gradiente + logo oficial). Só baixa de `image.tmdb.org`, nomes validados por regex, cache em `/opt/comet/data/img_cache` (limpa >30 dias acima de 300 MB), 2 gerações por vez (~0,7 s; do cache ~17 ms).
22. **Link pessoal (31/10/2026):** `.env` tem `PERSONAL_LINK_TOKEN` (token curto) e `PERSONAL_LINK_CONFIG` (a config completa do usuário em base64, com a chave do RD). `config_check` troca o token pela config, então `https://a71comet.duckdns.org/<token>/manifest.json` instala o Comet já configurado (RD, idiomas, filtros) sem passar pelo `/configure`. Token desconhecido continua dando "❌ | Comet". **Segredo:** quem tiver o link usa o RD do usuário; nunca versionar nem imprimir. Para mudar a config: configurar no `/configure`, usar uma vez, e copiar o novo b64 do log para `PERSONAL_LINK_CONFIG`.
    - Reinstalar um addon com a mesma URL não atualiza a cópia guardada no Stremio: é preciso desinstalar, fechar o Stremio e instalar de novo (a versão automática do manifest deve evitar isso daqui pra frente).
23. **Rodada "ouro" (01/11/2026):**
    - **Lista de fontes (`STREAM_LAYOUT=clean`):** 1ª opção `▶ Assistir` (cópia da melhor: dublado pronto no RD, 1080p e ≤ 30 GB preferidos → link direto PT → pronto no RD original; `bingeGroup comet|best`). Nomes `⚡/⬇️/⚠️ <res>` + `🇧🇷 Dublado/Dual áudio/PT-BR` ou `🌐 Original`; descrição de 3 linhas. `bingeGroup` dos torrents = `comet|<serviço>|<res>|<pt|xx>|<grupo>` (próximo episódio automático). `classic` volta ao formato antigo. Detecção PT: "Castellano ... por EliteTorrent" não é mais PT.
    - **Conteúdo:** `⚡ Pronto dublado` (RD + PT pelo banco, 30 dias) com pré-aquecimento (`comet/services/warmup.py`, `CATALOG_WARMUP`: 5 min após subir e a cada 12 h busca os streams de Top 10 + Em alta pelo link pessoal, 20 s entre títulos), `🎬 Sagas` (20 coleções do TMDB; filtro por saga), `👤 Atores e diretores` (busca por pessoa; séries sem talk show/participações < 3 episódios), `🌸 Animes da temporada`.
    - **Link Kids:** `KIDS_LINK_TOKEN` no `.env` → `https://a71comet.duckdns.org/<KIDS_LINK_TOKEN>/manifest.json` (id `.kids`, "Comet Kids"): Família, Animações, Desenhos (gênero Kids do TMDB), Disney+; filmes com `certification.lte=12` BR; busca filtrada.
    - **Visual:** capa deitada com logo em todas as fileiras menos Top 10, Originais, Sagas, buscas e Kids. Selos desenhados na capa (`?b=`): `new_ep` NOVO EPISÓDIO (≤ 10 dias), `new` NOVIDADE (filme ≤ 30 dias), `dub` DUBLADO (está em Pronto dublado), `top10`. Rota `/art/poster/` para pôster em pé com selo.
    - **Pessoal (`comet/services/stremio_library.py`):** com `STREMIO_AUTH_KEY` no `.env` (só leitura via `api.strem.io/api/datastoreGet`): `📌 Minha lista`, `🆕 Novos episódios` (14 dias), `💡 Recomendados para você` (TMDB recommendations dos 5 últimos assistidos). Sem a chave as fileiras não aparecem.
24. **Só lista o que toca + playback sem travar (01/11/2026):**
    - **DNS:** o AdGuard da casa bloqueava TLDs inteiros (`.lat`, `.top`: lista "HaGeZi's The World's Most Abused TLDs"; `zjo.lat` também no 1Hosts Xtra). Os links do FrostStream redirecionam por `zjo.lat`, `aponteiecair.lat`, `telaplay93.top`, `cdn.vdcdpstop.lat` → no Stremio: `Failed to connect to zjo.lat/0.0.0.0:80`. O usuário criou exceções `@@||...^$important` no AdGuard (também `fenixhub.online`, `tech-cdn.top`). O AdGuard também bloqueava fontes do Comet (Midnight, `comet.feels.legal`, BestCine, SubSource: erro TLS, porque `0.0.0.0` cai no Caddy local). O chroot agora usa `1.1.1.1`/`9.9.9.9` (`/etc/resolv.conf`, backup `resolv.conf.adguard.bak`; `scripts/install_rootfs.sh` atualizado).
    - **Links diretos validados** (`direct_addons.py`): segue os redirecionamentos (até 6, `Range 0-1023`, UA ExoPlayer, 5 s por salto, lote de 7 s) e só lista se terminar em `200/206` de vídeo/HLS. Cada host da cadeia é consultado no DNS da casa (`HOUSE_DNS=192.168.3.44`, UDP puro); `0.0.0.0`/sem IP → descartado e log `🚫 DNS da casa bloqueia <host>` (aí basta liberar o host no AdGuard). Sem resposta do DNS → mantém. Log `🌐 diretos: válidos/total`. Sem User-Agent o FrostStream responde 403 (normal).
    - **Playback** (`playback.py`, `stremthru.py`): orçamento `PLAYBACK_BUDGET=15` s por pedido; não cacheado → aviso "Baixando no Real-Debrid…" na hora; troca do 451 pula hashes já marcados e respeita o orçamento.
    - **`▶ Assistir`:** só direto validado ou ⚡ sem 451 (nunca ⬇️/P2P); o link do RD é pré-resolvido em background e guardado 10 min (`get_preresolved_link`).
    - **Fileiras sem capa (corrigido):** o warmup chamava get_catalog() sem ase_url e o cache (6 h) guardava pôsteres relativos (/art/top10/...): Top 10/Em alta/Lançamentos sumiam no PC e davam EmptyContent no celular. Agora get_catalog usa PUBLIC_BASE_URL quando ase_url vem vazio. Os catálogos saem com Cache-Control: max-age=600 (era 3600): o Stremio guarda a resposta e nem reiniciar o app a renova, então uma resposta ruim dura no máx. 10 min.
    - Revisão: o agy deixou um `NameError: aliases` no pré-resolve (quebrava o pedido de stream com RD) e tratava DNS sem resposta como bloqueio; os dois corrigidos à mão.
25. **Rodada "tinindo" (01/11/2026):**
    - **Teste automático** (`scripts/smoke.py` → `/opt/comet-tools/smoke.py`; `scripts/smoke.ps1` no PC, chamado pelos `deploy_*.ps1`): manifest, 4 fileiras (capas absolutas que abrem), stream de filme e série, play do `▶ Assistir` até o vídeo, e `Traceback`/`NameError` no log. O watchdog roda 3 min após o Comet subir e a cada 60 min (`SMOKE OK`/`SMOKE FALHOU`/`RESTAURADO` no `watchdog.log`). Passou → snapshot `/opt/comet/data/last_good.tar.gz` (+`.sha1`). Falhou **por código** (manifest, catálogos, log, stream 5xx/sem conexão) com código diferente do snapshot → restaura, reinicia e testa de novo; falha externa (poucos streams, link fora) só avisa. `data/smoke.disable` pausa. `NTFY_TOPIC` no `.env` (opcional) manda push pelo ntfy.sh. Resultado em `data/smoke_last.json`.
    - **TorBox como 2º debrid** (`TORBOX_API_KEY` no `.env`; entra só nos links pessoal/Kids, depois do RD). Uma linha por torrent: RD ⚡ sem 451 → TorBox ⚡ → RD ⬇️ → TorBox ⬇️. Descrição mostra `Real-Debrid`/`TorBox`. Playback: 451 no RD tenta o mesmo hash no TorBox antes de trocar (`🔁 451 no RD → TorBox`). `Pronto dublado` conta os dois. Medido: dos 31 dublados bloqueados no RD, 28 estão no TorBox; Ben 10 Omniverse `1:2` 0 → 8 dublados ⚡; Avatar Seven Havens TorBox 1 → 76 ⚡.
      - Correção na revisão (`media_search.py`): o cache `debrid_availability` só guarda positivos, e o Comet só consultava torrents novos quando *algum* serviço já tinha positivo → o TorBox nunca era consultado para torrents já conhecidos. Agora `_CHECKED` (memória, 12 h) guarda o que cada serviço já checou e `select_debrid_refresh_hashes(..., services=)` consulta o que falta.
      - O TorBox recusa (403) pedidos sem `User-Agent`.
    - **Próximo episódio instantâneo** (`comet/services/prefetch.py`, `PREFETCH_NEXT_EPISODE=True`): ao dar play num episódio, busca em background a lista do seguinte (ou `S+1:1`; não se ainda não estreou), 1 por série/20 min, 2 ao mesmo tempo. Severance `2:3` → `2:4`: 17 s → 0,5 s. Log `⏭️ pré-busca`.
    - **Página de status:** `https://a71comet.duckdns.org/<PERSONAL_LINK_TOKEN>/status` (outros caminhos → 404): memória, teste automático, fontes (6 h, sucesso/erro/último erro sem URL), hosts bloqueados pelo DNS da casa, 451/TorBox, plays. Contadores em memória (zeram ao reiniciar, no máx. 5000 eventos).
    - **Memória de arquivo dublado persistente:** tabela `pt_filenames` (90 dias, 50 mil); legendas continuam vazias para arquivo PT depois de reiniciar.
    - **Fileiras pessoais ligadas** (`STREMIO_AUTH_KEY` no `.env`): o usuário assiste sem salvar na biblioteca (todos os itens `removed/temp`), então `Novos episódios` e `Recomendados` usam o histórico (`lastWatched`) mesmo de itens removidos; `Minha lista` só mostra o que foi salvo (hoje vazia).
    - Não feito: limite do OpenSubtitles (20/dia, conta grátis) e obras com o mesmo nome exato (Doctor Who).
26. **Grande update + grande upgrade (02/11/2026)** (especificações em `.orquestra/tarefa-J.md` … `tarefa-Q.md`):
    - **Testes de regressão** (`scripts/regress.py` → `/opt/comet-tools/regress.py`; `scripts/regress.ps1`; os `deploy_*.ps1` rodam depois do smoke e saem com código 1 se falhar): 16 de unidade + ~20 integrados (manifest, todos os catálogos e capas absolutas, busca, meta, streams sem hash repetido/CAM no topo, Kids, legendas, `/status` sem segredo, `/configure`, play até o vídeo, TV ao vivo, busca inteligente, filler, bingeGroup, sorteio, log). Linha de base em `data/regress_baseline.json` (`-SaveBaseline`): queda > 60 % = WARN, cair a 0 = FAIL. Teste HTTP que falha é repetido 1 vez após 15 s (aquecimento depois de reiniciar). Resultado em `data/regress_last.json` e no `/status`. `scripts/test_audio_probe.py`: teste do leitor MKV/MP4.
    - **Legenda traduzida** (`comet/services/sub_translate.py`, `AUTO_TRANSLATE_SUBS`): sem nenhuma PT-BR e com inglesa → entrada `auto-...` (`/subs/auto/...`), traduzida pelo Google `translate_a/single?client=gtx` (sem chave) em lotes, cache em disco, já começa em background quando a lista de legendas é pedida. The Penguin S01E07: 910 falas em 4,9 s, depois 0,01 s.
    - **Madrugada** (`comet/services/nightly.py`, `NIGHTLY_WARM_HOUR=4`): aquece o próximo episódio e o último lançado das séries do histórico (60 dias, 25) + Top 10, um por vez, para se `MemAvailable` < 600 MB. Tabela `dub_watch`. Episódio recente que vira dublado ⚡ → aviso ntfy (`NTFY_TOPIC`, hoje sem) e fileira `🔔 Chegou dublado` (`comet_dubready`, só pessoal, episódios lançados há ≤ 21 dias). Rodar já: `/<PERSONAL_LINK_TOKEN>/nightly/run`.
    - **Fonte caindo é pausada** (`comet/core/breaker.py`): 3 erros seguidos → pausa 10 min, depois 1 pedido de teste (se não voltar em 120 s, outro), falha → pausa em dobro (máx. 1 h). Nunca pausa RD/TorBox/StremThru/TMDB. Coluna "Estado" no `/status`.
    - **Áudio PT confirmado** (`comet/services/audio_probe.py`, tabela `audio_probe`): lê as faixas de áudio do MKV/MP4 (Range de 1–4 MB) do `▶ Assistir` pré-resolvido e de 2 candidatos dublados seguintes. `has_pt=1` → `🇧🇷✔` + `🔊 PT · EN`; dizia PT e não tinha → perde o `🇧🇷` e nunca vira `▶ Assistir`.
      - Correções na revisão: o pré-resolve mandava `season/episode = "n"` em filmes e o TorBox respondia "No file matched requested episode" (o `▶ Assistir` de filme no TorBox nunca era pré-resolvido); o agy tinha duplicado o disparo com `asyncio.create_task` sem referência; agora `_spawn_preresolve` guarda as tarefas, o pedido tem limite de 40 s e erros de debrid são logados.
    - **TV ao vivo** (`comet/services/live_tv.py`, `type: tv`, id `comet_livetv`, prefixo `cometlive:`): Pluto TV oficial (181 canais BR, grade "Agora/Depois", URL com `deviceId` fixo em `data/pluto_device_id`) + canais abertos do iptv-org validados 1×/dia (`data/iptv_alive.json`, 264 vivos). Kids só categorias infantis.
    - **Busca que entende português** (`comet/services/smart_search.py::parse_query`): gênero, época, pessoa ("com …"), tema ("de tubarão" → keyword em inglês), nacional, bem avaliado, curto, "dublado" (dublados prontos primeiro, sem esconder o resto). Busca por título simples igual à de antes.
    - **Página do título e extras:** fillers de anime (`comet/services/anime_filler.py`, animefillerlist.com, cache 7 dias: `🟡 Filler`/`🟠 Misto`), `📺 Na temporada anterior:` no 1º episódio de cada temporada, `▶ Assistir` com `bingeGroup comet|best|pt` (autoplay continua no dublado), legenda `🎓 PT+EN` (`/subs/dual/...`) e `🎲 Sorteio do dia` (`comet_lucky`, depois do Top 10).
27. **Ajustes pedidos pelo usuário (02/11/2026, tarde)** (`.orquestra/tarefa-P2.md`, `P3`, `S`, `T`, `U`):
    - **Busca abrangente:** frases livres → tira stopwords e sinais, traduz o resto PT→EN (gtx, cache 7 dias), `search/keyword` com singular, bigramas e 3 candidatos por termo, sinônimos de domínio e tabela de enredos (`time loop`, `body swap`…). Cadeia: E entre conceitos → OU → melhor conceito → votos 5 → `search/movie|tv`, completando até 40. Relevância = nº de conceitos cobertos, empate por popularidade. "do <x>" só vira pessoa se o TMDB achar alguém real. Títulos em escrita não latina → título en-US. Bateria de 25 frases no `regress.py` (`busca_bateria`, ≥ 90 % = PASS): hoje ~22/25 (fracas: "filme de dinossauro" com 1º fora do tema, "cachorro que fala" misturado, "polícia brasileira" só 4).
    - **Sagas:** a fileira mostra a saga (`cometsaga:<collection>`, `type: series`); o meta traz os filmes como `videos` (ids `tt…`, S1E1…En). `stream/series/<tt>` sem `:S:E` é tratado como filme (idem legendas e playback).
    - **TV ao vivo:** metas com `behaviorHints.defaultVideoId` e `videos` de 1 item; Pluto com `notWebReady: true`. Fileira `📺 Ao vivo agora` (`comet_livehome`, 20 canais variados) logo depois de `🆕 Lançamentos` (série); Kids só infantis. O usuário relatou "Nenhum streaming disponível" antes desta mudança, com o Comet respondendo 200 e 1 stream: **confirmar com ele se resolveu e em qual aparelho**.
    - **Selos:** tamanho proporcional à capa (texto ~48 px na deitada 780×439), helper único para selos futuros, cache `v2:`. Selo do streaming (`?p=<provider_id>`, logo oficial do TMDB no canto superior direito; tabela `watch_provider`, 7 dias), em todas as fileiras com capa montada.
    - Áudio dos candidatos extras também normaliza `season/episode` (`_norm_se`).
    - **Pluto TV:** o link antigo (`/stitch/hls/channel/<id>/master.m3u8?<query v1>`) devolve o vídeo de aviso "não está mais disponível" (segmentos `…_ptv_takedownslates_…`). Agora: `📺 Ao vivo` = sessão `boot.pluto.tv/v4/start` (JWT, `/v2/stitch/...`) e `opção 2` = `jmp2.uk/plu-<id>.m3u8`. `check_channel_chain` reprova slate; canal com slate nas duas sai (`data/pluto_alive.json`, 1×/dia). Canais abertos revalidados até o segmento.
    - **Sagas** viraram `series/comet_sagas` na tela inicial; `movie/comet_saga` só no Descobrir (`genre` obrigatório). Item novo com prefixo próprio (`cometsaga:`, `cometlive:`) só funciona depois que o usuário **reinstala** o addon (o app guarda o manifest antigo e nem pergunta ao Comet: "No information found about this").
    - **Fileiras novas (`.orquestra/tarefa-X.md`):** mood logo depois de `📺 Ao vivo agora` (`comet_mood_cry`, `_twist`, `_binge`, `_light`, `_family` — esta também no Kids —, `_night`; discover + keywords, ordem embaralhada por dia, dublados primeiro), `🎌 Animes dublados` (`comet_anime_dub`, depois de `comet_anime_season`; no Kids só classificação BR L/10 ou US TV-Y/TV-Y7/TV-G — hoje vazia lá) e `📅 Estreias da semana` (`comet_week`, depois de `🔔 Chegou dublado`).
    - **Pré-download do próximo episódio (`prefetch.py`, feito direto por mim):** a pré-busca do próximo episódio agora também dispara quando o usuário **abre** um episódio (`stream.py`, só pedido externo: tem `X-Forwarded-For` do Caddy; internos não encadeiam), porque `▶ Assistir` por link direto (FenixFlix/FrostStream) não passa pelo playback do Comet. Se o próximo não tem 🇧🇷 ⚡ nem 🌐 PT, faz GET interno (`Range 0-1`) no playback do melhor 🇧🇷 ⬇️ (1080p > 720p > 4K > 480p > SD, ≤ 15 GB, RD antes de TorBox) para o debrid começar a baixar. 1 por série/12 h, 10 por dia (`data/predownload.json`); linha no `/status`. Teste `unit_predownload_pick`.
28. **Leva "addon supremo" (02/11/2026, noite)** — a partir daqui Claude implementa direto (sem agy), ver `CLAUDE.md`:
    - **Tela inicial instantânea** (`comet/services/row_warm.py`, `ROW_WARM`): catálogo pedido de fora (com `X-Forwarded-For`) enfileira os 6 primeiros itens para aquecer (1 por vez, pausa 2 s, pula se `MemAvailable` < 700 MB ou se já há cache < 3 dias); madrugada até 120 itens incluindo os 8 primeiros das fileiras principais. Aquecidos abrem em 0,4–1,3 s.
    - **Notas e Oscar** (`comet/services/omdb.py`, `OMDB_API_KEY` no `.env`, orçamento 900/dia em `data/omdb_budget.json`, cache SQLite `omdb_cache`): 1ª linha da descrição do título `⭐ IMDb · 🍅 · Ⓜ️ · 🏆 Venceu/Indicado a N Oscars` (em `meta.py`, timeout 4 s). Selo dourado `OSCAR` nas capas (`o=1`, posto no `catalog.py` só com dado em cache; cache de capa `landv3`/`posterv3`). Madrugada aquece o OMDb das fileiras principais.
    - **Fileiras de prestígio** (dentro de `_fetch_mood_items`): `comet_mood_oscar` (lista fixa `OSCAR_BEST_PICTURE`, 1990–Anora; a cerimônia de 2026 não está na lista), `comet_mood_top` (`movie/top_rated` com ≥ 5000 votos), `comet_mood_classicdub` (antes de 2000, dublados primeiro; também no Kids só família/animação).
    - **Bot do Telegram** (`comet/services/telegram_bot.py`, `@comet_a71_casa_bot`, `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` no `.env`; guia em `COMO-CRIAR-BOT-TELEGRAM.md`): pedidos em texto livre ("Duna 2 dublado", "The Last of Us T2E3") → diz se o 🇧🇷 está pronto, ou manda o debrid baixar o melhor 🇧🇷 ⬇️ e avisa quando ficar ⚡ (checa a cada 5 min por até 4 h); `/status`, `/ajuda`; só responde ao chat do dono. Avisos: smoke falhou/restaurou (`scripts/smoke.py`), RD/TorBox vencendo em ≤ 7 dias (1×/dia), episódio dublado novo (madrugada).
    - **Fora de casa** (`stream.py`): o app do Stremio não manda User-Agent e, em casa, tudo chega do mesmo IP; não dá para separar TV de celular. Pedido de IP **público** (4G) faz o `▶ Assistir` preferir ≤ 4 GB e 720p antes de 4K (`_apply_clean_layout(..., remote=True)`).
    - **Kids "hora de dormir"** pronta e **desligada** (usuário não quis agora): `KIDS_BEDTIME=21:00-07:00` no `.env` liga; vídeo em `comet/assets/status_videos/KIDS_BEDTIME.mp4` (cópia em `comet-patches/assets/`; o `git diff` do patch não carrega binário).
    - **Atualização segura do Comet original:** `.\scripts\update_comet.ps1 -Check` / `.\scripts\update_comet.ps1` (guarda estado, `ff-only` + reaplica as modificações, deps se `pyproject` mudou, reinicia, smoke + regress; falhou → rollback). Em 02/11 já estávamos no último `origin/main`.
    - **`a71.ps1`** usa arquivo temporário único por execução (dois processos não se atropelam mais).
    - **Lição:** às 17:42 o Comet caiu com código em andamento e o smoke restaurou a versão das 17:12, levando junto edições não commitadas. Durante trabalho longo, criar `data/smoke.disable` e apagar no fim.
29. **Acesso fora de casa / 4G (02/11/2026, noite):** antes o `a71comet.duckdns.org` apontava para o IP da LAN (192.168.3.44), então só funcionava em casa. A casa tem **IP público** (WAN do Huawei WiFi BE3 = IP visto na internet; os saltos 10.x/172.x do traceroute são da rede interna da operadora, não é CGNAT). A porta 443 externa já é de **outro PC** da casa, então o Comet usa a **7443**: regra no roteador TCP/UDP 7443 → 192.168.3.44:7443; `config/Caddyfile` ganhou o site `a71comet.duckdns.org:7443` (mesmo certificado por DNS-01); `PUBLIC_BASE_URL=https://a71comet.duckdns.org:7443` no `.env` (capas e links de play usam isso). O DuckDNS aponta para o IP público e o `watchdog.sh` atualiza a cada 10 min (`update_duckdns`, `ip=` vazio). O roteador faz NAT loopback, então o mesmo link funciona em casa; a reescrita no AdGuard (`a71comet.duckdns.org` → `192.168.3.44`) é opcional (só encurta o caminho em casa). Link pessoal novo: `https://a71comet.duckdns.org:7443/<PERSONAL_LINK_TOKEN>/manifest.json` (reinstalar nos aparelhos). Testado de fora (check-host.net, 5 países): 200. A 8443 (StremThru) não foi aberta no roteador.
30. **Salto geracional (02/11/2026, noite; Claude + 4 subagentes, sem agy):** ideias e prioridades em `MELHORIAS.md` (★★).
    - **Medições que guiaram:** TorBox 0,5 s / 130–146 Mbit/s até a casa; RD 4K BLUDV bloqueado (451) na hora do play; respostas sem compressão (tela inicial 1,47 MB); Interestelar com 1.489 fontes (878 KB); sem `uvloop`.
    - **Base:** `encode zstd gzip` no Caddy (manifest 15,7 KB → 1,7 KB); `uvloop` + `httptools` no venv (e em `setup_comet.sh`); teto de 120 fontes por lista (`STREAM_LIST_CAP`, até 80 🇧🇷, `▶`/avisos sempre); **TorBox principal** (`DEBRID_PRIMARY`, padrão `torbox`) e, para IP público (4G), só TorBox ⚡ (RD ⚡ só se o TorBox não tiver; regra de 1 IP do RD); bloqueio `infringing_file` descoberto na sondagem de candidatos agora é gravado.
    - **Qualidade real** (`comet/services/media_probe.py` + `media_info.py`, tabela `media_info`): lê o cabeçalho MKV/MP4 (codec, bit depth, HDR10/HDR10+/DV com perfil e compat, bitrate real, faixas de áudio com a padrão, legendas). A lista mostra `🎞️ 4K · HEVC 10-bit · DV 8.1 · HDR10+ · 17 Mbps`, `🔊 PT padrão · EN` e avisos (`Começa em EN: troque o áudio`, DV perfil 5, TrueHD). O `▶ Assistir` evita DV perfil 5 e prefere PT como faixa padrão. Um download de 4 MB por arquivo (mesmo momento da sondagem de áudio).
    - **Atalhos com curadoria** (`_curated_shortcuts` em `stream.py`): abaixo do `▶`, `📱 Leve` (🇧🇷 720p/1080p ≤ 3 GB), `💎 Máxima qualidade` (4K, HDR, maior bitrate, sem DV P5), `🎧 Original` (sem PT, ≤ 15 GB). São cópias: o teste de duplicados as ignora.
    - **Capas vivas** (`comet/services/live_art.py` = motor Pillow; `live_art_svc.py` = rotas `/art/hero|tv|ep|live|week`, cache em `data/live_art`, só imagens de TMDB/metahub/Pluto/próprio Comet): pôster editorial no fundo da página do título (logo, IMDb/Rotten/Oscar em PT, 4K/HDR confirmado, dublado, "termina às HH:MM", elenco com fotos; assets do TMDB guardados 6 h, imagem refeita a cada 5 min; o aquecimento das fileiras já desenha); guia de TV na capa dos canais (agora/barra/depois, a cada 15 min, `posterShape` landscape); selos nos episódios (`DUB` via `dub_watch`, `FILLER`, `FINAL`; sem imagem do episódio usa o fundo da série); barra de progresso + "faltam X min" nas capas do que está pela metade no histórico do Stremio (`_progress_map`, 5 min); faixas `HOJE`/`AMANHÃ`/`EM N DIAS`/`NOVO` em 📅 Estreias e `DUBLADO CHEGOU` em 🔔 (o selo antigo `?b=` sai da capa de origem).
    - **📅 Sua semana** (`week_cards.py`, `comet_myweek`, antes de `comet_week`): um cartão desenhado por dia; clicar abre os episódios do dia (`cometsaga:w-AAAAMMDD`).
    - **Maratonas e anime sem filler** (`marathon.py`, `watch_orders.py` com 8 coleções/81 filmes conferidos no Cinemeta, `anime_canon.py`): `🍿 Maratonas na ordem da história` (`cometsaga:o-<chave>`) e `🎌 Anime só a história` (`cometsaga:c-<imdb>`, One Piece 1.085 eps sem 94 fillers). Reaproveitam o prefixo `cometsaga:` (sem reinstalar). Dúvidas de ordem em `downloads/work/orders/watch_orders_check.txt` (não versionado): posição de Deadpool & Wolverine, Homem-Aranha 2026.
    - **Lista de desejos + radar** (`wishlist.py`, comandos `/quero`, `/desejos`, `/remover`, `/radar on|off`, frases "me avisa quando sair X dublado"): checa a cada 3 h; o bot do Telegram prefere título exato na lista de desejos (aceita o que ainda não estreou, ex.: Duna: Parte Três) e título já lançado no pedido normal (`_tmdb_find(..., prefer_released)`).
    - **Ainda não feito (MELHORIAS ★★) na época:** 6 e 12. Os dois foram feitos no item 31.
    - **Fundo animado (testado e descartado):** WebP/GIF animado como `background`/`poster` (`/art/anim/...`) ficou parado no app da TV do usuário. Fileira de teste desligada (`PREVIEW_TEST_ROW=False`; a rota continua). Prévia em vídeo ao focar não é possível pelo protocolo; o que existe é `trailerStreams` (dublado + legendado) na página do título.
    - **Pegadinha nova:** o `grep` do Android (fora do chroot) não entende `\|`; use `grep -E "a|b"`. Emoji no padrão do grep enviado pelo `a71.ps1` também falha: procure por texto ASCII.
31. **PT padrão, gosto, TV reformulada e rádios (03/11/2026; Claude + 2 subagentes):**
    - **PT como faixa padrão sem reencodar (MELHORIAS ★★ 6).**
      - Peças: `comet/services/media_probe.py` registra os filhos de cada TrackEntry e o CRC-32 das Tracks; `flag_plan.py` (`make_plan(summary, head, extra)`) calcula a troca; `flag_proxy.py` faz o repasse.
      - Como funciona: toda faixa de áudio antes do PT ganha `FlagDefault=0` (o elemento é escrito por cima ou é reaproveitado um filho do mesmo tamanho: FlagForced, FlagLacing, Void...). O PT fica com 1 e o CRC é recalculado (zlib, little-endian).
      - Onde fica o plano: é gravado em `media_info.summary.pt_fix` na leitura do arquivo.
      - Na lista: a fonte ganha `&fix=1` e `PT padrão (ajustado pelo Comet)`, só em casa e até 30 Mbps. O `▶ Assistir` passa a tratar essas fontes como PT padrão.
      - No play: com `fix=1`, o `playback.py` (`_pt_fix_response`) repassa o arquivo pelo A71, com Range, trocando só os bytes do plano; sem plano, faz o redirecionamento normal.
      - Testado em 3 GoT reais (BLUDV com CRC; WEB-DL PiA com EN default+forced): o ffprobe mostra `eng=0 / por=1`. O avanço para 30 min abriu em 3 s.
      - Testes locais em `downloads/work/flagfix/` (15 + 14, não versionados).
      - O áudio DTS/TrueHD para a TV ficou de fora: pesado demais para o A71.
    - **O Comet que aprende (★★ 12).**
      - `comet/services/taste.py`: `play_log` + avaliação a cada 6 h com o histórico do Stremio.
      - O `▶ Assistir` usa a nota de gosto como desempate.
      - `/gosto` no Telegram mostra o que ele aprendeu.
    - **Anime só a história:** `marathon._clean` tira os campos `null` (o app descartava a página inteira). Detetive Conan foi removido da lista.
    - **TV ao vivo reformulada** (`live_tv.py`, `api/endpoints/live_routes.py`).
      - **Causa do "não abre":** a lista de canais vivos do Pluto nunca era gravada (só validava depois de 24 h ligado), então canais mortos e duplicados apareciam. Exemplo: "Nickelodeon Clássico" em Infantil não existe mais, e o que funciona é o de Nickelodeon.
      - **Validação:** agora roda 2 min depois de subir (se a lista tiver mais de 20 h) e a cada 12 h, com 2 tentativas por fonte. Grava `data/pluto_alive.json` e o idioma do áudio de cada canal (`data/pluto_info.json`, lido do `EXT-X-MEDIA`). Proteção: queda geral do Pluto não apaga a lista.
      - **Catálogo:**
        - sem duplicatas (por nome normalizado; cópias do Pluto no iptv-org saem);
        - português primeiro, gêneros novos `🇧🇷 Em português` e `🌎 Outros idiomas`;
        - o Início só mostra canais em PT.
      - **Idioma:** o Pluto marca muito canal nacional como `en`. Por isso há a lista `_FORCE_PT_WORDS` e as categorias `_FORCE_PT_CATS` (infantil, Nickelodeon, novelas, TV brasileira).
      - **Causa real do "fica só carregando":** uma sessão v4 do Pluto compartilhada entre canais e aparelhos (era uma só, em cache) faz o Pluto devolver playlists de variante **vazias** quando duas aberturas se cruzam. O ExoPlayer fica esperando para sempre.
      - **Opção 1 por clique:** `📺 Ao vivo` aponta para `PUBLIC_BASE_URL/live/pluto/<id>.m3u8`. O A71 (`resolve_pluto_url`) cria uma **sessão v4 nova e exclusiva** (`_fresh_pluto_session`, clientID aleatório), confere master + 1 variante com segmentos sem baixar vídeo, tenta de novo uma vez e, se falhar, cai no jmp2. A opção 2 é o jmp2 direto.
      - **Medição real** com ffmpeg no PC (o vídeo tem que andar 15 s): a sessão compartilhada falhava em 11–20% das aberturas da opção 1; com a sessão por clique, **178/179** com 6 canais abrindo ao mesmo tempo (a falha foi o Naruto lento). Scripts em `downloads/work/tvplay.py` (não versionado).
      - **iptv-org:** revalidado em 03/11 (227 canais). O rótulo de áudio do HLS erra muito, então nome com BR/Brazil/termo nacional = PT (`_iptv_lang`). Códigos de 3 letras (`por`) são convertidos (`_lang2`).
    - **Reinício preso (03/11, 04:08):** depois de um `pkill`, o uvicorn ficou esperando um stream aberto fechar (TV tocando) e parou de atender sem sair. Correções:
      - `timeout_graceful_shutdown=8` no `comet/main.py`;
      - o `watchdog.sh` mata com `-9` o Comet que está vivo mas não responde há 3 checagens (15 min).
    - **DNS (03/11, 05h):**
      - O que aconteceu: o `1.1.1.1` (primeiro do `/data/debian/etc/resolv.conf`) passou a responder em 1–3 s ou nem responder nesta rede. Os catálogos do TMDB davam timeout e o regress falhava.
      - Correção: a ordem agora é `9.9.9.9`, `8.8.8.8`, `1.1.1.1` com `options timeout:2 attempts:2` (o `install_rootfs.sh` já grava assim).
      - Se os catálogos voltarem a dar timeout, meça cada servidor com uma consulta UDP crua antes de mexer em código.
    - **iptv-org em português:** além de `countries/br.m3u`, entra `languages/por.m3u` (Portugal, Angola...).
      - O `index.m3u` mundial (>10 mil canais) foi descartado: pesado demais para validar no A71 e quase nada em PT.
      - URLs repetidas são validadas uma vez só; o semáforo baixou de 15 para 8.
    - **Servidor a 190% de CPU (03/11, achado com `py-spy dump`, instalado no venv via `uv pip`):** `_get_ready_tt_list` (fileira ⚡ Prontos) refazia `RTN.parse` de todos os títulos da `debrid_availability` a cada cálculo. A tabela cresceu com o TorBox principal, e vários cálculos rodavam em paralelo (o timeout do catálogo não cancela a thread) e seguravam o GIL. Resultado: os catálogos do TMDB davam timeout e o regress falhava em 6 testes. Correções:
      - memória por (título, tracker) em `_READY_PT_MEMO`;
      - um cálculo por vez por tipo (`_READY_LOCKS`); quem chega no meio do cálculo recebe a lista antiga.
    - **Não rode validação do iptv-org e o regress ao mesmo tempo:** a validação faz centenas de consultas DNS e o resto dá timeout.
    - **📻 Rádios ao vivo** (`comet/services/radio.py`, catálogo `comet_radio`). A página da rádio mostra `🎵 Tocando agora` (ICY `StreamTitle`, 3 s no máximo, cache de 2 min, conserta UTF-8 duplo).
      - Fonte: Radio Browser, 380 candidatas (todas de PE + as 10 maiores de cada estado + populares). 371 passam na validação de bytes reais (MP3/AAC/Ogg/HLS). A lista é revalidada a cada 24 h em `data/radio_alive.json` e nunca é gravada com menos de 20.
      - Gêneros: `📍 Recife e Pernambuco` (39 rádios) primeiro, depois por região e por tipo (Notícias, Esporte, Forró...).
      - IDs `cometlive:radio:<uuid>` (prefixo já existente: meta e stream sem reinstalar; o catálogo novo aparece depois de reinstalar o link).
      - Repasse `/radio/<id>` (http → https para o 4G; HLS reescrito em `.m3u8`). Capa desenhada `/art/radio.png?n=` quando a rádio não tem logo.
      - **Pegadinha:** o `uvloop` não aceita `happy_eyeballs_delay` em `open_connection` (a primeira validação deu 0 rádios); há fallback.
    - **Regress:** `t_livetv` agora reprova canal duplicado e meta com `null`, e testa a opção 1 pelo A71 local.
32. **Nuvio no Fire TV (05/11/2026):** o usuário testou o app Nuvio (`com.nuvio.tv`, Fire TV `192.168.3.29:5555`, 1.0.0) e pediu para deixá-lo redondo.
    - **Link próprio:** `NUVIO_LINK_TOKEN` no `.env` (`https://a71comet.duckdns.org:7443/<token>/manifest.json`), mesma config do link pessoal (`is_personal_request`). Instalado na TV; o Stremio segue com o link pessoal, sem mudança. O Nuvio não troca addon de mesmo id: remova o antigo antes de instalar.
    - **Diferenças em relação ao pessoal (`is_nuvio_request`):** `meta.py` não usa `/art/hero` (o Nuvio escreve logo, notas e elenco por cima e o texto duplicava); `stream.py` não põe `&fix=1` nem o aviso "Começa em EN" e mostra `PT · EN` (`_pt_auto`), porque o Nuvio com a TV em pt-BR escolheu Português sozinho em Reacher, cujo arquivo traz EN primeiro. Teste `t_nuvio` no `regress.py`.
    - **Conferido na TV:** tela inicial, Sua semana, Chegou dublado, Top 10, Maratonas (toca o filme certo), busca, lista de fontes, legendas, TV (relato do usuário), `Pular Abertura` (introdb.app, em Hunter x Hunter). O cartão "Próximo episódio" mantém a fonte `▶ Assistir`. No fim do episódio o Nuvio pergunta "Continuar assistindo?" e não avança sozinho (ao menos em 20 s).
    - **Rádio:** o som sai, mas fica em "Iniciando vídeo…", porque a tela de carregamento do Nuvio espera um quadro de vídeo. Vídeo falso exigiria ffmpeg, que o A71 não tem.
    - **Correções (06/11/2026):** título curto quase igual é outra obra (`_short_title_mismatch` em `filtering.py`: Reacher × Preacher, até 10 letras e 1 de diferença no tamanho); os links diretos são validados com dublados e maiores resoluções primeiro (o FenixFlix manda ~26 links e o lote só tem 7 s); direto 480p/SD não vira `▶ Assistir` se houver ⚡ em 720p ou mais (em Hunter x Hunter ele é outra versão, sem ano no nome, e travou o player após muitos saltos); `movie/comet_saga` sem gênero abre a 1ª saga.
    - **Ainda aberto:** o FenixFlix às vezes responde 403 ou demora; sem nenhum direto válido, o `▶ Assistir` pode cair em torrent SD dublado. O elenco no Nuvio vem sem foto (o app tem enriquecimento TMDB próprio; não testado).
    - **Dicas de ADB na TV:** `input keyevent 66` (Enter) abre os botões do player e `23` só pausa; em Fire TV, `input text` embaralha letras no teclado (envie letra por letra); `uiautomator dump` lê os textos do Compose.
20. **Episódio não lançado (31/10/2026):** VisionQuest E07/E08 (estreia 04/11 e 11/11) recebiam packs da temporada e um link FrostStream "MegaEmbed" falso (só áudio). Agora, em série com data do episódio maior que hoje, o Comet devolve só o aviso `[⏳] Comet` "Episódio ainda não lançado. Estreia em DD/MM/AAAA." (sem links diretos). O `DIGITAL_RELEASE_FILTER` segue desligado (bloquearia filmes de cinema).
21. **Legenda só sem áudio PT (31/10/2026):** o pedido de legendas devolve vazio quando o arquivo é PT-BR: links diretos PT (ganham `behaviorHints.filename` `<Addon>.direct.PTBR`), nome do arquivo com PT detectado (`apply_ptbr_detection`) ou arquivo que o Comet já marcou 🇧🇷 na lista de streams (memória `remember_pt_filename`, 50 mil nomes; cobre DUAL de fonte BR). Ressalva: essa memória zera quando o Comet reinicia.
14. **BRSites** (`comet/scrapers/brsites.py`, `SCRAPE_BRSITES=live`): busca pelo título (inglês e PT), filtra os posts pelo slug (em série, os posts da temporada ou do episódio vêm primeiro; máx. 4 por site), extrai todos os magnets e limpa os prefixos de site do `dn`. Em `filtering.py`, `dual` com tracker `BRSites` conta como PT-BR (igual ao BeTor). Levantamento de 12 sites em `.orquestra/levantamento-br.md`: só esses 2 trazem ganho real; os outros estão mortos ou não acrescentam nada. Ganho medido: GoT `7:2` 10→14 PT-BR, `6:5` 16→21; Transformers One (`tt8864596`) +1 dublado; Rick and Morty sem ganho. Tempo igual (~18 s por série, ~6 s por filme).

**O patch Python inteiro** (tudo menos `comet/templates/index.html`) está em `comet-patches/ptbr-first.patch` (LF). Para reaplicar depois de atualizar o Comet: `.\scripts\deploy_ui.ps1` e `.\scripts\deploy_patches.ps1`. Para regenerar a partir do A71: no chroot, `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /tmp/x.patch`, copie para `/data/local/tmp` e faça `adb pull`.

---

## 5. Estado do git (IMPORTANTE)

- **Remoto:** `https://github.com/onederson/CometToStremio` (o branch local `master` é enviado para `main`: `git push origin master:main`).
- **Commits mais recentes** (antes deste, que atualiza a documentação):
```
fa484ff Comet acessível fora de casa (4G) pela porta 7443
724f30d Leva supremo: tela instantânea, notas e Oscar, bot do Telegram e modo fora de casa
18958ad Tira do repositório o arquivo de anotações do usuário
0f52575 Fileiras de mood, animes dublados, estreias da semana e pré-download no RD
777476b Desliga a fileira de teste do fundo animado (não anima no app da TV)
42dd149 Pluto TV com sessão nova, sagas como série e teste de fundo animado
bc98273 Busca abrangente, sagas completas, TV na tela inicial e selos maiores
0dae6d9 Grande update: testes de regressão, legenda traduzida, TV ao vivo e áudio PT confirmado
40ea4d1 TorBox como 2º debrid, próximo episódio instantâneo, /status e teste automático
```
- O A71 está com tudo aplicado e rodando. O repositório é o espelho: `scripts/watchdog.sh` = `/data/comet/watchdog.sh`, `config/Caddyfile` = `/etc/caddy/Caddyfile` (chroot), `comet-patches/ptbr-first.patch` = diff de `/opt/comet` (o vídeo `KIDS_BEDTIME.mp4` vai à parte em `comet-patches/assets/`, porque o diff não carrega binário).
- `config/.env` e `config/duckdns.token` (no `.gitignore`) = `/opt/comet/.env` e `/etc/caddy/duckdns.token`. Ao mudar um, mude o outro. Para gravar uma chave no `.env` do A71 sem imprimir o valor, use `scripts/env_set.sh` (envie o valor em `/data/local/tmp/cc_val.txt` e rode `sh env_set.sh CHAVE` como root; ele confere a contagem de linhas e apaga o valor).
- Antes de cada commit, conferir que nenhum valor do `.env` aparece no diff (`PUBLIC_BASE_URL`, `ADDON_NAME` e `FASTAPI_HOST` aparecem e são inofensivos).
- Mensagem por arquivo (`git commit -F`) com a linha de coautoria da sessão. O usuário pediu commit + push ao fim de cada leva.

---

## 6. Como testar (sem RD, modo torrent)

```powershell
$cfg='{"debridServices":[],"enableTorrent":true,"cachedOnly":false,"removeTrash":true,"maxResultsPerResolution":0}'
$b=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($cfg))
$r=Invoke-RestMethod "http://192.168.3.44:8000/$b/stream/movie/tt12042730.json" -TimeoutSec 120
$s=$r.streams; "total=$($s.Count) ptbr=$(($s | ? { ($_.name + $_.description) -match '🇧🇷' }).Count)"
# série: .../stream/series/tt0903747:1:1.json
```

O cache fica na tabela `torrents` do SQLite (`/opt/comet/data/comet.db`), coluna `media_id` = IMDb puro (ex.: `tt0903747`). Para medir sem cache, apague as linhas do IMDb testado.

Atalho usado nas medições: um script Python no chroot que, para cada pedido, roda `DELETE FROM torrents WHERE media_id=?`, chama `http://127.0.0.1:8000/<b64>/stream/<tipo>/<id>.json` e conta os `🇧🇷` em `name`+`description`. Rode com `/opt/comet/.venv/bin/python` e apague o script depois.

**Resultados verificados (30/10/2026, estado atual):**

| Pedido | Total | PT-BR (antes → depois) | Falsos positivos | Tempo sem cache |
|---|---|---|---|---|
| `movie/tt12042730` (Devoradores de Estrelas) | 824 | 13 → 17 | 0 | 6.38s |
| `series/tt0903747:1:1` (Breaking Bad) | 530 | 9 → 9 | 0 | 17.54s |
| `series/tt0944947:1:1` (Game of Thrones) | 872 | 11 → 18 | 0 | 18.11s |
| `series/tt2861424:1:1` (Rick and Morty) | 319 | 5 → 6 | 0 | 17.86s |
| `series/tt0388629:1:1` (One Piece) | 382 | 0 → 0 | 0 | 18.04s |
| `series/tt0388629:21:1` (One Piece ep ~1071) | 55 | 0 → 0 | 0 | 30.87s |
| `series/tt9335498:1:1` (Demon Slayer) | 212 | — → 3 | 0 | 18s |
| `series/tt9335498:5:1` (Demon Slayer, arco Hashira) | 56 | — → 3 | 0 | 18s |
| `series/tt0903747:3:5` (Breaking Bad, 2º episódio da série) | 370 | 6 | 0 | 19s |
| `movie/tt22084616` (Spider-Man: Brand New Day; **não** é Transformers, que é `tt8864596`) | 674 | 17 → 21 | 0 | 6.46s |

Em todos os casos os PT-BR vêm primeiro, ordenados por resolução. Também medidos: Demon Slayer `3:1` = 34 (só arco Yuukaku), One Piece `21:181` (ep. 1071) = 124 / 4 PT-BR. Os números variam ±2 entre medições (fontes ao vivo). Memória disponível no A71: ~3,4 GB.

---

## 7. Lacunas conhecidas (situação atualizada)

1. **RD 451:** Mitigado. Hashes bloqueados agora recebem fallback transparente para P2P com rótulo `⚠️ P2P (bloqueado no RD)` (`P2P_FALLBACK_FOR_BLOCKED=True`), detecção prévia em background (`DEBRID_PRECHECK=True`) e auto-switch no playback (até 3 candidatos antes de exibir vídeo de erro).
2. **Anime:** Numeração absoluta mapeada via Kitsu/Cinemeta, aceitando batches/packs sem temporada (`seasons=[]`) e episódios com numeração corrida (One Piece 47 → 382 streams). Filtro de arcos: `get_imdb_arc_titles` + `release_cites_other_arc` (em `comet/services/anime.py`) rejeitam release cujo título mais específico cita OUTRO arco do mesmo IMDb, com ou sem número de temporada (grupos numeram arcos de jeitos diferentes: "Entertainment District Arc S01", "Swordsmith S03" do TVDB). Só vale para anime com ≥ 2 temporadas mapeadas (One Piece fica fora). No IMDb, Demon Slayer é T1 principal, T2 Mugen Train, T3 Entertainment District, T4 Swordsmith, T5 Hashira.
3. **Cache por episódio:** antes, qualquer linha em cache da temporada (packs salvos na busca de outro episódio) fazia o Comet pular a busca ao vivo, e o 2º episódio aberto de uma série vinha pobre (ex.: One Piece T1E1 com 47 em vez de 382). Agora `primary_cached` (em `orchestration.py::get_cached_torrents`) só é verdadeiro se houver linha daquele episódio; cada episódio novo faz 1 busca ao vivo (~18 s) e depois vem do cache. A 2ª abertura do mesmo episódio traz um pouco menos que a 1ª (ex.: BB T3E5 370 ao vivo → 213 do cache), comportamento original do Comet.
4. **Fontes:** MediaFusion recuperado (instância aberta Midnight + parsing corrigido); Peerflix e Comet adicionados com sucesso; TorrentsDB desativado por estar fora do ar (HTTP 502 na origem). AnimeTosho falha no DNS e NekoBT passa de 8 s.
5. **Indexadores:** FlareSolverr instalado e ligado ao Prowlarr (tag `flaresolverr`; resolve o Cloudflare do 1337x em ~17 s, pico real de ~750 MB PSS). Mas o catálogo do Prowlarr só tem 2 definições públicas pt-BR: BeTor (já ativo) e um site pornô (removido). Os sites BR de dublado não existem mais lá. Testados 8 indexadores gerais (1337x, TPB, EZTV, YTS, uIndex, LimeTorrents, TorrentDownloads, KAT): **nenhum ganho** de total ou PT-BR (Torrentio/Knaben já cobrem) e a busca de série subiu de ~18 s para ~32 s; todos removidos (`PROWLARR_INDEXERS=["1","2","3"]`). Próximo ganho possível: definições Cardigann próprias (`/var/lib/prowlarr/Definitions/Custom`) para sites BR, usando o FlareSolverr já pronto.

---

6. **Outros limites:** a 1ª busca de cada episódio leva ~18 s (filme ~6 s), por causa do Prowlarr. Em anime, quase todo PT-BR é legendado, não dublado.

---

## 8. Onde paramos e próximo passo

**Estado (05/11/2026, noite):** item 32 (Nuvio) rodando no A71. Pendências no fim do item 32. `data/smoke.disable` removido.

**Estado (03/11/2026, manhã):**
- O item 31 (PT padrão, gosto, TV reformulada, rádios, DNS) está rodando no A71 e no GitHub.
- **O usuário precisa reinstalar o link pessoal** para ver a fileira `📻 Rádios ao vivo` e os filtros de idioma da TV. O link é o mesmo; meta e stream das rádios já funcionam sem reinstalar.
- Próximas ideias: `MELHORIAS.md` ★★★ (10 melhorias + 10 novidades).

**Estado anterior (02/11/2026, noite):** tudo da Seção 4 (itens 1–29) está rodando no A71, testado (`SMOKE OK`, `REGRESS OK` com 41 testes; o WARN de `comet_mylist` vazio é normal) e no GitHub (`onederson/CometToStremio`, branch `main`). A restauração automática do smoke está **ligada** (sem `data/smoke.disable`).

**Último passo feito:** acesso fora de casa (item 29). O link agora é `https://a71comet.duckdns.org:7443/<PERSONAL_LINK_TOKEN>/manifest.json` e foi testado de fora (5 países, HTTP 200). **O usuário reinstalou com o link :7443 e confirmou que funciona no 4G (02/11/2026).**

**Pendente do lado do usuário:**
2. (Opcional) AdGuard: reescrita `a71comet.duckdns.org` → `192.168.3.44` (o roteador já faz NAT loopback, então não é obrigatória).
6. `NTFY_TOPIC` não é mais necessário: os avisos vão pelo Telegram.

**Se o usuário relatar problema:**
- Fora de casa não abre: `nslookup a71comet.duckdns.org 1.1.1.1` tem que dar o IP público da casa (o watchdog atualiza a cada 10 min; falha aparece como `DuckDNS: falha` no `watchdog.log`); a regra 7443 do roteador tem que existir; teste externo em check-host.net (`check-http` em `https://a71comet.duckdns.org:7443/manifest.json`).
- Dublado com `Failed to connect to <host>/0.0.0.0`: procure `🚫 DNS da casa bloqueia` no log e libere o host no AdGuard.
- Lista lenta: página de status (fontes pausadas, aquecimento); log `⏸️ <fonte> pausada`.
- 451 do RD: `🚫 RD bloqueou`, `🔁 451 no RD → TorBox`.
- Canal do Pluto mostrando "não está mais disponível": é o vídeo de aviso (`takedownslate`); o `check_channel_chain` já reprova; rodar a revalidação do `live_tv.py`.

**TorBox:** assinado pelo usuário em 02/11/2026. **SubDL:** o usuário decidiu não trocar a chave.

**Próximas melhorias:** ver `MELHORIAS.md` (medido em 02/11: respostas sem compressão, tela inicial com 65 fileiras = 1,47 MB, lista de Interestelar com 1.489 fontes = 878 KB, capa nova 1–1,5 s). **Vigia externo ligado (02/11/2026):** `HEALTHCHECK_URL` no `.env` (healthchecks.io, check `Comet A71`, período 5 min, tolerância 10 min, integração Telegram do próprio healthchecks). O `watchdog.sh` (`ping_healthcheck`) manda o sinal a cada 5 min só se o `manifest` local responder; Comet travado manda `/fail` na hora; A71 sem energia/internet → o healthchecks avisa no Telegram.

**Ideias que ficaram para depois (combinadas com o usuário):** perfis da família (um link por pessoa com histórico próprio; o usuário não quis agora), Letterboxd/MyAnimeList (só se ele usar), filtro por aparelho que trava com arquivo pesado (o app não se identifica; hoje só existe "fora de casa"), selo de áudio de cinema (Atmos/DTS-HD).

**Não é possível (não insistir):** prévia em vídeo ao focar a capa (testado: o app da TV não anima WebP/GIF; o protocolo não tem campo de vídeo), pular abertura, mudar o player.

**Manutenção:** se o BRSites parar de trazer resultados, provavelmente um dos sites trocou de domínio. Corrija o dict `SITES` em `comet/scrapers/brsites.py`. O `/configure` do usuário já está com "só em cache" desligado.

**Cuidado ao medir "novos" contra o banco:** a tabela `torrents` só tem os episódios já buscados. Compare sempre com o resultado ao vivo do Comet para o mesmo episódio, senão episódios de outras temporadas aparecem como "novos".

**Já descartado, não repita:** os indexadores gerais do Prowlarr (1337x, TPB, EZTV, YTS, uIndex, LimeTorrents, TorrentDownloads, KAT). Testados em 30/10/2026: zero ganho e +14 s por busca de série. Sites BR mortos ou sem ganho: VacaTorrent, LAPUMiA, Wolverdon, ThePirataFilmes, StarTorrent, OndeBaixo, LimonTorrent, TudoTorrents, BaixaFilmes, BaixeTorrents. Cardigann não serve para esses sites (um magnet por resultado, e os posts têm vários).
