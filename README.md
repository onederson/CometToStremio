# Fase 2: Backend de Addon Stremio no Galaxy A71 (Comet + Real-Debrid)

*Início da Fase: 29/10/2026*  
*Última atualização: 30/10/2026 (horário de Brasília)*

> **🤖 Para outra IA continuar daqui:** comece por **`HANDOFF.md`** (resumo completo, regras, estado do git e próximo passo). Depois leia a **Seção 0** inteira antes de rodar qualquer comando. Ela descreve o estado real verificado no aparelho, o que já está pronto e o comando exato do próximo passo.  
> O contexto completo da Fase 1 (rede `192.168.3.0/24`, IP fixo `192.168.3.44`, DNS `a71.lan`, AdGuard Home, ADB Wi-Fi permanente e regras de `su -c`) está em `README adguard contexto.md`.

---

## 0. 📍 Status Atual / Diário de Bordo

### Estado verificado no Galaxy A71 em 29/10/2026 às 10:22
* **ADB Wi-Fi (`192.168.3.44:5555`):** Conectado e estável.
* **AdGuard Home (Fase 1):** Rodando normalmente (`watchdog.sh` + `AdGuardHome`), intacto.
* **Disco e Memória:** `105 GB` livres em `/data` (uso total de `/data`: 4,6 GB / 5%); ~700 MB de RAM livre + 2,3 GB de swap livre.
* **Ambiente Debian 13.7 (`trixie` `aarch64`):** Extraído e funcional em `/data/debian` (~1,6 GB com toolchain).
  * `resolv.conf` configurado (`192.168.3.44` + `9.9.9.9`).
  * `/etc/gai.conf` configurado com `precedence ::ffff:0:0/96  100` (prioriza IPv4, já que o IPv6 está desativado na rede local).
  * `/etc/apt/apt.conf.d/01-android-sandbox` configurado com `APT::Sandbox::User "root";` (necessário por causa do `CONFIG_ANDROID_PARANOID_NETWORK`).
* **Comet instalado, configurado e rodando com sucesso:**
  * Arquivo `.env` gerado em `config/.env` e instalado em `/data/debian/opt/comet/.env` (`chmod 600`, LF apenas) contendo `PUBLIC_BASE_URL=https://a71comet.duckdns.org`.
  * Processo ativo em background sob supervisão (`python -m comet.main`, PID 3656).
  * **RAM medida Comet:** RSS de ~109 MB (`111.760 KB`).
* **Caddy com módulo DuckDNS configurado e rodando com HTTPS oficial:**
  * Binário customizado Caddy `v2.11.7` com módulo `dns.providers.duckdns` instalado em `/usr/local/bin/caddy` (`chmod 755`, no chroot).
  * Caddyfile configurado em `/etc/caddy/Caddyfile` (`/data/debian/etc/caddy/Caddyfile`, `chmod 644`, cópia local em `config/Caddyfile`), apontando reverse proxy para `127.0.0.1:8000`.
  * Token DuckDNS mantido isolado em `/data/debian/etc/caddy/duckdns.token` (`chmod 600`, sem versionamento).
  * Log de execução em `/data/comet/caddy.log`.
  * Certificado TLS Let's Encrypt (`CN=YE1, O=Let's Encrypt, C=US`) obtido com sucesso via desafio DNS-01 sem abrir portas de roteador.
  * Processo ativo em background sob supervisão (PID 3664).
  * **RAM medida Caddy:** RSS de ~40,5 MB (`41.428 KB`).
* **Endpoints HTTPS validados com sucesso a partir do PC (sem bypass de certificado):**
  * `https://a71comet.duckdns.org/manifest.json` → ID `stremio.comet.a71`, Nome `Comet A71`, versão `2.0.0`.
  * `https://a71comet.duckdns.org/configure` → HTTP 200 OK via HTTPS.
* **Persistência ativada e validada pós-reboot (Passo 4 concluído):**
  * O `watchdog.sh` atualizado está em `/data/comet/watchdog.sh` (`chmod 755`) supervisionando Comet e Caddy a cada 30 s (com cap de 5 MB para `comet.log` e `caddy.log`). Auto-recuperação testada e confirmada matando o Caddy.
  * O script de boot `comet.sh` foi instalado em `/data/adb/service.d/comet.sh` (`chmod 755`).
  * **Reboot validado:** A71 reiniciado com sucesso via ADB. Boot completado em 68 s; HTTPS online em 95 s após comando de reboot (27 s após `sys.boot_completed`).
  * **Processos ativos e supervisionados:** AdGuard Home intacto (DNS respondendo), 1 watchdog Comet (PID 3648), 1 Comet (`python -m comet.main`, PID 3656), 1 Caddy (`caddy run`, PID 3664).
* **Página `/configure` traduzida para PT-BR:** Template com explicações detalhadas em `comet-ui/index.html` aplicado em `/data/debian/opt/comet/comet/templates/index.html` (backup único em `index.html.orig`).
* **Patch "PT-BR primeiro" aplicado no Comet (`PTBR_FIRST=True`):** Detecção ampliada de PT-BR (trackers BR, marcadores de título e grupos `PTBR_RELEASE_GROUPS`), ordenação de streams PT-BR no topo agrupados por resolução (preservando PT-BR no corte de `maxResultsPerResolution`) e rótulo visual `🇧🇷 PT-BR`. Salvo em `comet-patches/ptbr-first.patch`.
* **Correção `magnet_error` no Real-Debrid (mesmo patch + `DOWNLOAD_GENERIC_TRACKERS=True`):** hashes vindos do Torrentio/StremThru chegam sem trackers; sem eles o RD não achava peers e recusava o magnet ("provider is currently unavailable" no Stremio). Agora `comet/debrid/stremthru.py` usa os 20 trackers públicos de `ngosang/trackerslist` quando o torrent não tem trackers próprios. **Nota:** após `git pull` do Comet, reaplicar `.\scripts\deploy_ui.ps1` e `.\scripts\deploy_patches.ps1`.
* **StremThru self-hosted local (`v0.105.4`):** A instância pública (`stremthru.13377001.xyz`) dava `TimeoutError` / `magnet_error` ao adicionar torrents não cacheados no Real-Debrid (`POST /v0/store/magnets`). Compilado do código-fonte oficial (`MunifTanjim/stremthru` tag `0.105.4` com Go `1.26.10` `linux/arm64`, já que as releases não publicam binários pré-compilados) em `/usr/local/bin/stremthru` (`chmod 755`, no chroot), escutando apenas em `127.0.0.1:8080`, dados em `/var/lib/stremthru` (chroot), log em `/data/comet/stremthru.log` e RSS de ~60,6 MB (`62.084 KB`). No `.env` do Comet foi adicionado `STREMTHRU_URL=http://127.0.0.1:8080` (mantendo `STREMTHRU_SCRAPE_URL` público apenas para scraping).
* **Filtro de hashes bloqueados pelo Real-Debrid (`451` / `HIDE_DEBRID_BLOCKED=True`):** Quando `POST /magnets` retorna HTTP 451 (`UNAVAILABLE_FOR_LEGAL_REASONS` / `infringing_file`), `comet/debrid/stremthru.py` grava upsert na tabela SQLite `debrid_blocked_hashes` (migração nativa `2026102901_debrid_blocked_hashes`), loga `🚫 RD bloqueou (451) <hash> <nome>` mantendo o vídeo de status atual no clique, e `comet/api/endpoints/stream.py` esconde os streams daquele serviço debrid nos próximos requests (consulta única em lote; modo P2P intacto).
* **Prowlarr local (`v2.7.0.5723` `linux-core-arm64`):** Instalado em `/opt/prowlarr` (dados em `/var/lib/prowlarr`, pacotes `libicu76` + `sqlite3`), bind exclusivo em `127.0.0.1:9696`, log em `/data/comet/prowlarr.log` e RSS de ~223,3 MB (`228.676 KB`; Comet em ~121,3 MB e `1.569 MB` de RAM livre no A71). Integrado ao Comet com `SCRAPE_PROWLARR=live` e `PROWLARR_URL=http://127.0.0.1:9696` (ainda fora do `watchdog.sh`).
  * **Indexadores ativos (3):** `Catálogo BeTor` (`catalogo-betor.yml` custom oficial `pt-BR` agregando BluDV, Comando, Torrent dos Filmes, StarckFilmes, RedeTorrent e SemTorrent via busca direta por IMDb ID), `Knaben` (meta-busca geral não usada pelo Torrentio) e `TorrentsCSV` (índice curado DHT/trackers).
  * **Excluídos e motivo:** Blogs BR avulsos (Comando, BluDV, Torrent dos Filmes, VacaTorrent, ApacheTorrent, RedeTorrent, LAPUMiA, Filmes Torrent, StarckFilmes, BaixaFilmes, Wolverdon, ThePirataFilmes) não existem no schema nativo do Prowlarr (Cloudflare/DNS morto/posts multi-magnet, cobertos pelo `Catálogo BeTor`); nativos `pt-BR`/`pt-PT` do schema são privados (ASC, BJ-Share, BrasilTracker, CapybaraBR, Locadora, MDAN, SAMARITANO, ShaKaw, UniOtaku, BTNext, Portugas, SAPIbr, SceneRush) ou adulto (`PornoTorrent`); `1337x`, `EZTV`, `Uindex`, `ExtraTorrent.st`, `Magnet Cat` e `KickassTorrents` exigem bypass Cloudflare (sem FlareSolverr); `TheRARBG` ausente no v2.7; `YTS` e `The Pirate Bay` redundantes com Torrentio; `LimeTorrents`, `TorrentDownload` e `TorrentProject2` omitem `infoHash` na listagem; `FileMood` retorna HTTP 429; `BTdirectory`, `DaMagNet`, `TorrentByte`, `Torrent[CORE]` e `52BT` falham no teste (HTTP 400).
* **Correção de séries dubladas PT-BR (`comet-patches/ptbr-first.patch`):** `torrentio.py` agora separa corretamente o cabeçalho antes de `\n👤 ... 💾`, usa o nome do arquivo quando reconhecível e faz fallback para a linha 1 do torrent quando o arquivo não traz o título da série (ex.: `1 - Piloto.mp4`, preservando `fileIndex`); `filtering.py` reconhece marcadores BR de temporada (`\d+ª Temporada`, `Temporada \d+`, `\d+ Temporada`, `Temporada Completa`) combinados com PT/tracker BR/`dual` e remove o `es` falso do RTN (mantendo `es` real); `orchestration.py` preserva pacotes de temporada (`seasons=[N]`, `episodes=[]`) em buscas de episódio mesmo com `reject_unknown_episode_files=True`.
* **Melhorias Parte 1 (Fallback P2P para 451):** Flag `P2P_FALLBACK_FOR_BLOCKED=True` (padrão) permite que streams bloqueados pelo RD (451) sejam convertidos em streams P2P transparentemente com rótulo `⚠️ P2P (bloqueado no RD)`, preservando ordenação por resolução e detecção PT-BR sem reenviar ao RD.
* **Melhorias Parte 1B (Detecção prévia e troca automática):** Background precheck (`DEBRID_PRECHECK=True`, max 20/h) detecta antecipadamente bloqueios do RD gravando em cache SQLite; no playback, quando o RD retorna 451, o Comet troca automaticamente para o próximo melhor lançamento do mesmo episódio/filme (até 3 tentativas) antes de exibir erro.
* **Melhorias Parte 2 (Anime com numeração absoluta):** Resolução de episódio absoluto via metadados Kitsu/Cinemeta para requisições S:E de animes; suporte a packs/batches sem temporada (`seasons=[]`) e episódios com numeração corrida (ex: One Piece 1071); ativação do scraper SeaDex (`SCRAPE_SEADEX=live`).
* **Melhorias Parte 3 (Fontes perdidas e novos scrapers):** MediaFusion corrigido apontando para a instância pública aberta `https://mediafusionfortheweebs.midnightignite.me` com parsing robusto de títulos, tamanhos e seeders; TorrentsDB desativado (`SCRAPE_TORRENTSDB=False`) por indisponibilidade total da origem (HTTP 502); novos scrapers ativos: `SCRAPE_PEERFLIX=live` (com `impersonate="chrome"`) e `SCRAPE_COMET=live` (`https://comet.feels.legal`), elevando a contagem de fontes sem sobrecarregar a memória do A71 (> 2 GB livres).
* **Filtro de Arcos em Anime (`comet-patches/ptbr-first.patch`):** Rejeição automática de releases de anime que citam outro arco via mapeamento Kitsu/IMDb e detecção de títulos normalizados de arcos concorrentes (preservando séries com arco único como One Piece), inclusive em releases com número de temporada próprio do grupo.
* **Busca ao vivo por episódio:** `primary_cached` só considera o cache válido se houver linha daquele episódio (packs salvos na busca de outro episódio não bastam), então cada episódio novo de uma série faz sua própria busca nas fontes.
* **Proteção de memória e FlareSolverr:** Watchdog com proteção oom (-1000 para Comet, StremThru, Prowlarr, Caddy e AdGuard; 200 para o FlareSolverr), `am kill-all` abaixo de 600 MB disponíveis, limite de 1200 MB PSS no FlareSolverr, 4 apps do Android desativados (`scripts/android-apps.sh`). FlareSolverr v3.5.2 (127.0.0.1:8191) em arm64 com proxy no Prowlarr (tag `flaresolverr`). Indexadores gerais testados via FlareSolverr não trouxeram ganho e foram removidos (detalhes em `HANDOFF.md`, Seção 7).
* **CAM no fim da lista (`DEMOTE_CAM=True`):** gravações de cinema (CAM/TS/TC/SCR) vão para o fim com o rótulo `🎦 CAM`, e a troca automática do 451 só as usa em último caso.
* **Biblioteca do RD no Stremio:** addon Store do StremThru em `https://a71comet.duckdns.org:8443/stremio/store/configure` (Caddy `:8443` → `127.0.0.1:8080`).
* **Fonte BRSites (`SCRAPE_BRSITES=live`):** scraper próprio de `filmestorrent.tv` e `apachetorrents.com` que pega todos os magnets de cada post (ex.: GoT T7E2 10 → 14 PT-BR).

### Checklist de progresso
- [x] Conferir ADB (`192.168.3.44:5555`), root, internet do A71, espaço e RAM
- [x] Baixar rootfs Debian 13 (`trixie` `arm64`) e validar SHA256 (`b4b49e1d…07cd1c`)
- [x] Criar scripts locais em `scripts/` (`a71.ps1`, `install_rootfs.sh`, `chroot.sh`, `setup_comet.sh`, `watchdog.sh`, `comet.sh`) — todos em **LF** (zero `\r`)
- [x] Extrair rootfs em `/data/debian` e validar chroot + `/dev/shm` + DNS
- [x] Executar `setup_comet.sh` até o fim (apt + rustup + uv + clone do Comet + `uv sync` compilando `torrent-parse-rank`)
- [x] **Passo 1:** Criar `/data/debian/opt/comet/.env` (template conferido e validado) e subir Comet na porta `8000`
- [x] **Passo 2:** Testar `http://192.168.3.44:8000/manifest.json` e `http://a71.lan:8000/configure` a partir do PC
- [x] **Passo 3:** Configurar **HTTPS com DuckDNS + Caddy (Let's Encrypt via DNS-01)** e validar do PC
- [x] **Passo 4:** Ativar persistência: `watchdog.sh` supervisionando Comet + Caddy, `comet.sh` instalado em `/data/adb/service.d/` e reboot validado com AdGuard e HTTPS automáticos
- [x] **Passo 5 (com o usuário):** Gerar manifest no `/configure` com a API Key do **Real-Debrid** + filtros **PT-BR / Dual Áudio**, instalar no Stremio (PC e Smart TV) e validar reprodução
- [x] StremThru local, filtro 451, Prowlarr e correção de séries PT-BR (ver Seção 0 acima)
- [x] Fallback P2P para 451, precheck/troca automática, anime absoluto e expansão de fontes (MediaFusion, Comet, Peerflix)
- [x] Proteção de memória (oom + `am kill-all`), FlareSolverr e desativação de apps do Android
- [x] Teste do usuário no Stremio com RD (451/troca automática, anime, 2º episódio)
- [x] CAM no fim da lista, addon Store (biblioteca do RD) e fonte BRSites
- [ ] Usuário instalar o addon Store no Stremio

---

### Mapa de arquivos (PC ↔ Galaxy A71)

| Arquivo no PC (`STREMIO\`) | Caminho no A71 | Status no A71 | Função |
| :--- | :--- | :--- | :--- |
| `scripts/a71.ps1` | *(apenas no PC)* | ✅ Pronto | Helper PowerShell: `.\scripts\a71.ps1 'cmd'` (root no Android) ou `.\scripts\a71.ps1 -Chroot 'cmd'` (dentro do Debian). Elimina problemas de aspas do PowerShell + `adb` |
| `downloads/debian-trixie-arm64-rootfs.tar.xz` | `/data/local/tmp/rootfs.tar.xz` | ✅ Já extraído em `/data/debian` | Imagem base Debian 13 arm64 (não versionar no git) |
| `scripts/install_rootfs.sh` | `/data/local/tmp/install_rootfs.sh` | ✅ Já executado | Extraiu o rootfs, configurou DNS/hosts e copiou scripts |
| `scripts/chroot.sh` | `/data/comet/chroot.sh` | ✅ Instalado (`755`) | Monta `/proc`, `/sys`, `/dev`, `/dev/pts`, `/dev/shm` (tmpfs 128 MB) e executa comandos no chroot Debian |
| `scripts/setup_comet.sh` | `/data/debian/root/setup_comet.sh` | ✅ Executado c/ sucesso | Instalou Python 3.13, GCC, Rust, `uv`, clonou Comet em `/opt/comet` e rodou `uv sync` (log em `/data/comet/setup.log`) |
| `scripts/watchdog.sh` | `/data/comet/watchdog.sh` | ✅ Ativo (`755`) | A cada 30 s religa StremThru, Prowlarr, Comet, Caddy e FlareSolverr; protege os serviços (e o AdGuard) do killer de memória; `am kill-all` com pouca RAM; limita logs a 5 MB |
| `scripts/android-apps.sh` | `/data/comet/android-apps.sh` | ✅ `disable` aplicado | Desativa (`disable`) ou reativa (`enable`) 4 apps do Android que gastam RAM à toa |
| `comet-patches/flaresolverr-arm64.patch` | *(aplicado em `/data/debian/opt/flaresolverr`)* | ✅ Aplicado | FlareSolverr v3.5.2 usando `/usr/bin/chromium` e `/usr/bin/chromedriver` do Debian (arm64); log em `/data/comet/flaresolverr.log` |
| `scripts/comet.sh` | `/data/adb/service.d/comet.sh` | ✅ Instalado (`755`) | Script de boot Magisk (`sleep 45` + sobe `/data/comet/watchdog.sh`) |
| `config/.env` | `/data/debian/opt/comet/.env` | ✅ Instalado (`600`) | Configurações do Comet (SQLite, 1 worker, scrapers, `PTBR_FIRST=True`, `DOWNLOAD_GENERIC_TRACKERS=True`, `STREMTHRU_URL=http://127.0.0.1:8080`, `SCRAPE_PROWLARR=live` em `127.0.0.1:9696` e `PUBLIC_BASE_URL=https://a71comet.duckdns.org`) |
| *(compilado no chroot)* | `/data/debian/usr/local/bin/stremthru` | ✅ Ativo (`755`) | StremThru `v0.105.4` (`arm64`, compilado da tag `0.105.4`) em `127.0.0.1:8080` para operações de store Real-Debrid; dados em `/data/debian/var/lib/stremthru` e log em `/data/comet/stremthru.log` |
| *(instalado no chroot)* | `/data/debian/opt/prowlarr` | ✅ Ativo (`755`) | Prowlarr `v2.7.0.5723` (`linux-core-arm64`) em `127.0.0.1:9696` (`Catálogo BeTor`, `Knaben`, `TorrentsCSV`); dados em `/data/debian/var/lib/prowlarr` e log em `/data/comet/prowlarr.log` |
| `config/Caddyfile` | `/data/debian/etc/caddy/Caddyfile` | ✅ Instalado (`644`) | Configuração do reverse proxy Caddy HTTPS com Let's Encrypt DNS-01 (DuckDNS) |
| `comet-ui/index.html` | `/data/debian/opt/comet/comet/templates/index.html` | ✅ Instalado (`644`) | Página `/configure` traduzida para PT-BR com explicações detalhadas (backup original em `index.html.orig`) |
| `scripts/deploy_ui.ps1` | *(apenas no PC)* | ✅ Pronto | Reaplica `comet-ui/index.html` no A71 (mantendo `index.html.orig`) e reinicia o Comet |
| `comet-patches/ptbr-first.patch` | *(aplicado em `/data/debian/opt/comet`)* | ✅ Aplicado | Patch Python consolidado (20 arquivos): detecção/ordenação `PTBR_FIRST` (`🇧🇷 PT-BR`), trackers genéricos, filtro 451 + fallback P2P + precheck + troca automática, séries/packs PT-BR, anime absoluto com filtro de arcos, busca ao vivo por episódio, MediaFusion/Peerflix, melhorias no Prowlarr, CAM no fim (`DEMOTE_CAM`) e scraper `BRSites` |
| `scripts/deploy_patches.ps1` | *(apenas no PC)* | ✅ Pronto | Reaplica `comet-patches/ptbr-first.patch` no A71 (pula se já aplicado) e reinicia o Comet |

> ⚠️ **Pegadinhas importantes (leia antes de mexer):**
> 1. **Sempre use `.\scripts\a71.ps1`** para rodar comandos no A71 a partir do PowerShell. Ele grava um script temporário em UTF-8 LF e executa via `su -c`, evitando que o PowerShell engula aspas, `$` ou `|`.
> 2. **Bug do `adb push` com múltiplos arquivos no Windows:** passar vários arquivos com barra normal (`adb push scripts/a.sh scripts/b.sh /data/local/tmp/`) **trunca o último caractere do nome** (`chroot.s`). Sempre envie **um arquivo por vez especificando o nome final completo**:  
>    `adb -s 192.168.3.44:5555 push scripts\arquivo.sh /data/local/tmp/arquivo.sh`
> 3. **Sempre grave scripts e `.env` com quebra de linha LF** (sem `\r`).
> 4. **A chave do Real-Debrid NÃO vai no `.env`** (a menos que se ative proxy de stream). No Comet, o token do Real-Debrid e os idiomas preferidos são configurados na interface web `/configure`, que codifica tudo na URL do `manifest.json` instalada no Stremio.

---

## 1. 🎯 Objetivo da Fase 2

* **Serviço:** Servidor privado **Comet** (`g0ldyy/comet`) para indexação/raspagem de torrents com resolução de cache e streaming de alta velocidade via **Real-Debrid**.
* **Foco:** Conteúdos em português (áudio dublado / dual áudio PT-BR e legendas) para filmes, séries e animes.
* **Porta local do Comet:** `8000` (`0.0.0.0:8000` no A71 → `http://192.168.3.44:8000` / `http://a71.lan:8000`).
* **Dispositivos clientes:** Stremio no PC, Smart TV, celulares e tablets da rede doméstica.

---

## 2. 🏗️ Arquitetura no Galaxy A71

| Recurso | Detalhes |
| :--- | :--- |
| **Dispositivo** | Samsung Galaxy A71 (`SM-A715F`), Snapdragon 730, 6 GB RAM, 128 GB UFS 2.1 |
| **Sistema** | crDroid 10 (Android 14 Vanilla), Magisk 31.1 Root, carga limitada a 70% |
| **IP Fixo / DNS LAN** | `192.168.3.44` / `a71.lan` |
| **Fase 1 (Ativo)** | AdGuard Home nativo em `/data/adguard` (portas `53` UDP/TCP e `3000` TCP) |
| **Fase 2 (Em implantação)** | Comet em chroot Debian 13 (`/data/debian/opt/comet`), controlado por `/data/comet/` (porta `8000` TCP) |

**Por que chroot Debian 13 (`trixie`) em vez de binário solto ou Termux?**
1. O Comet exige **Python ≥ 3.13** (disponível nativamente no Debian 13) e compila o pacote Rust `torrent-parse-rank` via `maturin` direto do GitHub.
2. Com `glibc` padrão do Debian `aarch64`, todas as demais dependências pesadas (`pydantic-core`, `orjson`, `cryptography`, `curl-cffi`, `lxml`) baixam wheels `manylinux_aarch64` pré-compiladas em segundos.
3. Zero dependência de app Android (sem Termux), rodando 100% em `/data` sob controle direto do Magisk `service.d`, exatamente como o AdGuard Home.

---

## 3. ▶️ Roteiro Exato para Continuar (Passo a Passo)

### Passo 1: Criar `/opt/comet/.env` e testar subida manual

Por padrão no Comet, `DATABASE_TYPE` vem como `postgresql`, `USE_GUNICORN` vem `True` e **todos os `SCRAPE_*` vêm `False`**. Portanto, o `.env` abaixo é **obrigatório** para usar SQLite leve com Uvicorn e habilitar as fontes de torrents (incluindo Torrentio e MediaFusion, que trazem releases dublados/dual-áudio PT-BR).

Conteúdo recomendado para salvar localmente em `config/.env` (com **LF**) e copiar para `/data/debian/opt/comet/.env`:

```ini
ADDON_ID=stremio.comet.a71
ADDON_NAME=Comet A71

# Servidor leve para o A71 (1 worker Uvicorn puro, sem Gunicorn)
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_WORKERS=1
USE_GUNICORN=False
EXECUTOR_MAX_WORKERS=1

# Banco local SQLite (em /opt/comet/data/comet.db)
DATABASE_TYPE=sqlite
DATABASE_PATH=data/comet.db

# Desativa background scraper contínuo para poupar CPU/RAM/flash
BACKGROUND_SCRAPER_ENABLED=False

# Melhora detecção de idiomas em títulos PT-BR / Dual Áudio
SMART_LANGUAGE_DETECTION=True
INDEXER_LANGUAGES=["pt","en"]

# Fontes públicas de scraping em tempo real (sem exigir Jackett/Prowlarr local)
SCRAPE_TORRENTIO=live
TORRENTIO_URL=https://torrentio.strem.fun

SCRAPE_MEDIAFUSION=live
MEDIAFUSION_URL=https://mediafusion.elfhosted.com

SCRAPE_ZILEAN=live
ZILEAN_URL=https://zileanfortheweebs.midnightignite.me

SCRAPE_STREMTHRU=live
STREMTHRU_SCRAPE_URL=https://stremthru.13377001.xyz

SCRAPE_TORRENTSDB=live
SCRAPE_NYAA=live
NYAA_ANIME_ONLY=True
```

**Como enviar e testar manualmente:**
```powershell
cd c:\Users\Vendel\Desktop\Projetos\a71\STREMIO
adb connect 192.168.3.44:5555

# 1. Enviar o .env (depois de cria-lo em config\.env sem CR)
adb -s 192.168.3.44:5555 push config\.env /data/local/tmp/comet.env
.\scripts\a71.ps1 'cp /data/local/tmp/comet.env /data/debian/opt/comet/.env && chmod 600 /data/debian/opt/comet/.env && rm /data/local/tmp/comet.env'

# 2. Subir o Comet em background para teste e acompanhar os primeiros 15 s de log
.\scripts\a71.ps1 'nohup sh /data/comet/chroot.sh -c "cd /opt/comet && exec /opt/comet/.venv/bin/python -m comet.main" > /data/comet/comet.log 2>&1 < /dev/null & sleep 12; cat /data/comet/comet.log'
```

### Passo 2: Validar HTTP na LAN a partir do PC
```powershell
Invoke-RestMethod http://192.168.3.44:8000/manifest.json
Invoke-WebRequest http://a71.lan:8000/configure -UseBasicParsing | Select-Object StatusCode
```
E medir quanto de RAM o processo `python -m comet.main` ocupou no A71 (`.\scripts\a71.ps1 'ps -o pid,rss,args -ef | grep "[c]omet.main"'`).

---

## 4. 🔒 Questão Crítica: Stremio exige HTTPS fora de `localhost`

O aplicativo **Stremio bloqueia a adição de addons via `http://` em IPs de rede local** (`http://192.168.3.44:8000` ou `http://a71.lan:8000`) — ele só aceita `http://` puro em `127.0.0.1` / `localhost`. Além disso, **Smart TVs rejeitam certificados SSL autoassinados** (pois não é possível instalar uma CA própria na TV).

Portanto, para funcionar perfeitamente no **PC + Smart TV + Celulares**, precisamos expor a porta `8000` do Comet via **HTTPS com certificado TLS público válido (Let's Encrypt ou Cloudflare)**. Há duas opções excelentes (ambas gratuitas e sem abrir portas no roteador HUAWEI):

### Opção A (Recomendada para LAN 100% local, URL fixa e máxima velocidade): DuckDNS + Caddy (Let's Encrypt via DNS-01)
1. Criar um subdomínio gratuito em `https://www.duckdns.org` (ex.: `a71comet.duckdns.org`) apontando para o IP local **`192.168.3.44`** (e adicionar também um *DNS Rewrite* no AdGuard Home: `a71comet.duckdns.org` → `192.168.3.44`).
2. Rodar o **Caddy** (com módulo `caddy-dns/duckdns`) no próprio A71 escutando em `:443` (ou `:8443`), fazendo `reverse_proxy 127.0.0.1:8000`.
3. O Caddy renova sozinho um certificado **Let's Encrypt real** via desafio DNS-01 usando o token do DuckDNS — **sem abrir nenhuma porta no roteador** e mantendo 100% do tráfego dentro do Wi-Fi local.
4. No `.env` do Comet, definir `PUBLIC_BASE_URL=https://a71comet.duckdns.org` (ou `:8443`).

### Opção B (Mais rápida para testar em 1 minuto, sem criar conta): Cloudflare Tunnel (`cloudflared`)
1. Instalar `cloudflared` (`arm64`) dentro do chroot Debian e rodar `cloudflared tunnel --url http://127.0.0.1:8000`.
2. Gera na hora uma URL `https://xxxx.trycloudflare.com` com SSL válido aceito por qualquer Smart TV.
3. *Contras do modo rápido sem conta:* a URL muda se o `cloudflared` reiniciar. Se o usuário tiver um domínio no plano gratuito da Cloudflare, um **Named Tunnel** fixa a URL permanentemente (`https://comet.seudominio.com`) e ainda permite usar o addon fora de casa (4G/5G), mas cuidado com a regra de 1 IP por vez do Real-Debrid!

> 💡 **Atenção sobre o Real-Debrid:** o Real-Debrid só permite streaming simultâneo a partir de **1 endereço IP público por vez**. Na LAN de casa todos saem pelo mesmo IP da operadora, então TV + PC + celulares podem assistir ao mesmo tempo sem risco de banimento, **desde que** o Real-Debrid seja chamado diretamente pelos clientes na mesma casa (padrão do Comet com `PROXY_DEBRID_STREAM=False`).

---

## 5. 🔁 Persistência no Boot e Watchdog (Passo 4)

Somente **após** validar que o Comet sobe e responde na porta `8000`:

```powershell
# 1. Matar eventual processo de teste manual e deixar o watchdog assumir
.\scripts\a71.ps1 'pkill -f "python -m comet.main" || true; nohup /system/bin/sh /data/comet/watchdog.sh >/dev/null 2>&1 </dev/null & sleep 5; cat /data/comet/watchdog.log'

# 2. Instalar o script de boot no Magisk service.d
adb -s 192.168.3.44:5555 push scripts\comet.sh /data/local/tmp/comet.sh
.\scripts\a71.ps1 'cp /data/local/tmp/comet.sh /data/adb/service.d/comet.sh && chmod 755 /data/adb/service.d/comet.sh && rm /data/local/tmp/comet.sh && ls -la /data/adb/service.d/'

# 3. Teste de fogo: reiniciar o A71 e conferir (~60 s após o boot) AdGuard + Comet
adb -s 192.168.3.44:5555 reboot
```

*(Nota: com o Caddy implantado no Passo 3, o `/data/comet/watchdog.sh` precisará supervisionar tanto o Comet quanto o Caddy antes do teste final de reboot no Passo 4.)*

---

## 6. 🧹 Limpeza Opcional de Espaço (Pós-Instalação)

Atualmente há 105 GB livres em `/data`, então **não há urgência**. Caso queira enxugar ~1 GB depois que tudo estiver homologado:
* `/data/local/tmp/rootfs.tar.xz` (90 MB) e `/data/local/tmp/AdGuardHome.tar.gz` (11 MB) podem ser removidos.
* Dentro do chroot, `/root/.cache` (203 MB) e `apt-get clean` liberam cache de pacotes; mantenha `/root/.cargo` e `/root/.rustup` caso pretenda atualizar o Comet (`git pull && uv sync`) no futuro.

---

## 7. 🔑 O que pedir ao Usuário na Etapa Final (Passo 5)

1. **Chave de API do Real-Debrid:** obtida em `https://real-debrid.com/apitoken` (será colada pelo próprio usuário na tela `/configure` ou passada para gerarmos a URL).
2. **Decisão de HTTPS (Seção 4):** perguntar se prefere **DuckDNS + Caddy (100% local e fixo)** ou **Cloudflare Tunnel**.
3. **Configuração recomendada na página `/configure` do Comet:**
   * **Debrid Service:** `Real-Debrid` + API Token.
   * **Cached Only:** Ativado (mostra apenas torrents já em cache instantâneo `⚡` no Real-Debrid).
   * **Resolutions:** `4K (2160p)`, `1080p`, `720p`.
   * **Languages:** Em *Preferred Languages* colocar **Portuguese** (e Dubbed/Dual Audio no topo da ordenação) e em *Allowed/Required* manter **Portuguese** + **English** (para não esconder filmes legendados quando não houver dublado).
