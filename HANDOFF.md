# HANDOFF: Comet Stremio no Galaxy A71 (para outra IA continuar)

*Última atualização: 30/10/2026 (horário de Brasília)*

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
20. **Episódio não lançado (31/10/2026):** VisionQuest E07/E08 (estreia 04/11 e 11/11) recebiam packs da temporada e um link FrostStream "MegaEmbed" falso (só áudio). Agora, em série com data do episódio maior que hoje, o Comet devolve só o aviso `[⏳] Comet` "Episódio ainda não lançado. Estreia em DD/MM/AAAA." (sem links diretos). O `DIGITAL_RELEASE_FILTER` segue desligado (bloquearia filmes de cinema).
21. **Legenda só sem áudio PT (31/10/2026):** o pedido de legendas devolve vazio quando o arquivo é PT-BR: links diretos PT (ganham `behaviorHints.filename` `<Addon>.direct.PTBR`), nome do arquivo com PT detectado (`apply_ptbr_detection`) ou arquivo que o Comet já marcou 🇧🇷 na lista de streams (memória `remember_pt_filename`, 50 mil nomes; cobre DUAL de fonte BR). Ressalva: essa memória zera quando o Comet reinicia.
14. **BRSites** (`comet/scrapers/brsites.py`, `SCRAPE_BRSITES=live`): busca pelo título (inglês e PT), filtra os posts pelo slug (em série, os posts da temporada ou do episódio vêm primeiro; máx. 4 por site), extrai todos os magnets e limpa os prefixos de site do `dn`. Em `filtering.py`, `dual` com tracker `BRSites` conta como PT-BR (igual ao BeTor). Levantamento de 12 sites em `.orquestra/levantamento-br.md`: só esses 2 trazem ganho real; os outros estão mortos ou não acrescentam nada. Ganho medido: GoT `7:2` 10→14 PT-BR, `6:5` 16→21; Transformers One (`tt8864596`) +1 dublado; Rick and Morty sem ganho. Tempo igual (~18 s por série, ~6 s por filme).

**O patch Python inteiro** (tudo menos `comet/templates/index.html`) está em `comet-patches/ptbr-first.patch` (LF). Para reaplicar depois de atualizar o Comet: `.\scripts\deploy_ui.ps1` e `.\scripts\deploy_patches.ps1`. Para regenerar a partir do A71: no chroot, `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /tmp/x.patch`, copie para `/data/local/tmp` e faça `adb pull`.

---

## 5. Estado do git (IMPORTANTE)

- **Commits:** `cbe21b8` → `17cec22` → `372e0e8` → `6615563` → `7642b2a` → "Proteção de memória, FlareSolverr e limpeza de apps do Android" (HEAD). Veja com `git log --oneline`.
- **Árvore limpa** depois do último commit. Nada pendente.
- O A71 está com tudo aplicado e rodando. O repositório é o espelho: `scripts/watchdog.sh` = `/data/comet/watchdog.sh` (confira o MD5), `comet-patches/*.patch` = diffs de `/opt/comet` e `/opt/flaresolverr`.
- `config/.env` (no `.gitignore`) = `/opt/comet/.env`. Ao mudar um, mude o outro.
- Commit só quando o usuário pedir. E-mail local `wandersonks02@gmail.com`; mensagem por arquivo (`git commit -F`) com a linha de coautoria definida pela sessão.

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

**Estado:** rodando no A71. Os itens 12–14 da Seção 4 estão aplicados e conferidos no aparelho (commit só quando o usuário pedir).

**Testado pelo usuário em 30/10/2026:** lançamento dublado funcionou, mas pela troca do 451 caiu num CAMRip com marca d'água (resolvido no item 12); Demon Slayer T1 e T5 ok; One Piece sem PT-BR (limite das fontes: quase tudo é legendado); Ben 10 Omniverse: todos os dublados estão bloqueados (451) no RD e só o P2P sobra, que tem poucos seeders.

**Pendente do lado do usuário:** instalar o addon Store (`https://a71comet.duckdns.org:8443/stremio/store/configure`, Real-Debrid + chave do RD) (FenixFlix e FrostStream **não** precisam mais ser instalados: já vêm dentro do Comet, item 16 da Seção 4).

**O Store é opcional:** ele só mostra como catálogo os torrents que já estão na conta do RD (135 em 30/10/2026, quase todos adicionados pelo próprio Comet ao dar play). O usuário achava que não tinha nada lá.

**Próximos passos que o usuário quer:**
1. **Mais fontes de link direto como FenixFlix/FrostStream:** procurar outros addons Stremio que servem vídeo HTTP direto com dublado e acrescentar a URL em `DIRECT_ADDONS_URL` (nada de código). Critério para entrar: o `GET /stream/...json` traz `url`, o link responde `200/206 video/*` com `Range`, e há dublado em títulos que o RD bloqueia (teste com Ben 10 Omniverse `tt2293002:1:2`).
2. **Legendas:** feito (item 17 da Seção 4). Pendente do usuário: reinstalar o Comet no Stremio para aparecer o recurso de legendas, tirar o addon OpenSubtitles PRO e trocar a chave do SubDL (vazou num teste em 31/10/2026).

Se ele relatar problema, comece pelos logs (`/data/comet/comet.log`: procure `🚫 RD bloqueou`, `🔁 451 em`).

**Manutenção:** se o BRSites parar de trazer resultados, provavelmente um dos sites trocou de domínio. Corrija o dict `SITES` em `comet/scrapers/brsites.py`. O `/configure` do usuário já está com "só em cache" desligado.

**Cuidado ao medir "novos" contra o banco:** a tabela `torrents` só tem os episódios já buscados. Compare sempre com o resultado ao vivo do Comet para o mesmo episódio, senão episódios de outras temporadas aparecem como "novos".

**Já descartado, não repita:** os indexadores gerais do Prowlarr (1337x, TPB, EZTV, YTS, uIndex, LimeTorrents, TorrentDownloads, KAT). Testados em 30/10/2026: zero ganho e +14 s por busca de série. Sites BR mortos ou sem ganho: VacaTorrent, LAPUMiA, Wolverdon, ThePirataFilmes, StarTorrent, OndeBaixo, LimonTorrent, TudoTorrents, BaixaFilmes, BaixeTorrents. Cardigann não serve para esses sites (um magnet por resultado, e os posts têm vários).
