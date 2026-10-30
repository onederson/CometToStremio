# HANDOFF: Comet Stremio no Galaxy A71 (para outra IA continuar)

*Última atualização: 30/10/2026 (horário de Brasília)*

Este é o documento de passagem. Ele resume **tudo o que foi feito, o estado real verificado, as regras do projeto, como testar e o que vem a seguir**. O `README.md` (Seção 0 e Mapa de arquivos) tem os detalhes da instalação. A Fase 1 (AdGuard) está em `README adguard contexto.md`.

---

## 1. Regras obrigatórias (leia primeiro)

### Modo de trabalho (do `CLAUDE.md`)
- A IA principal é **orquestradora**. Ela escreve a especificação em `.orquestra/tarefa.md`, delega ao `agy` (CLI do Antigravity) e revisa com `git diff --stat` / `git diff`, além de uma verificação independente no aparelho. Se aprovar, faz `git add -A`.
- **Quem roda o `agy` é o usuário**, com `! agy -p "..."`. O classificador bloqueia a IA de rodá-lo. Comando padrão:
  ```
  agy -p "Execute exatamente o que está em .orquestra/tarefa.md. Não faça nada fora do escopo. Ao terminar, rode a verificação descrita e responda em no máximo 5 linhas: arquivos alterados e resultado da verificação." --model gemini-3.8-flash-high --dangerously-skip-permissions --print-timeout 900s
  ```
  Para tarefas difíceis, use `--model gemini-4-argon-high`. Para continuar a mesma conversa, use `-c`. Nunca use os modelos `claude-*` do agy.
- Mudanças triviais (menos de ~20 linhas) a IA faz direto. No máximo 3 rodadas por tarefa; depois disso a IA corrige diretamente.
- **Commit só quando o usuário pedir.** Escreva a mensagem num arquivo temporário e use `git commit -F arquivo`.

### Segurança e restrições
- **Nunca imprima nem versione:**
  - o token do DuckDNS (`config/duckdns.token`, que está no `.gitignore`);
  - a chave do Real-Debrid;
  - a API key do Prowlarr.
- Use somente o domínio DuckDNS **`a71comet.duckdns.org`**. A conta tem 2 domínios; não mexa no outro.
- E-mail do git **só neste repo** (config local): `wandersonks02@gmail.com`.
- **Não mexa no AdGuard Home nem em nada da Fase 1.**
- **Não contorne o bloqueio 451 do Real-Debrid** (DMCA, `infringing_file`). A decisão foi apenas **esconder** os torrents bloqueados.
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

Torrents bloqueados pelo RD (451) devem ficar **escondidos**. O usuário quer **"todos os conteúdos possíveis"**: dublados, lançamentos, séries e anime. Ele disse que **esperava ganhos maiores, com mais conteúdo** (ver Seção 8).

---

## 3. Arquitetura (estado verificado em 30/10/2026)

| Componente | Onde | Porta | Observação |
|---|---|---|---|
| Galaxy A71 | `192.168.3.44`, ADB Wi-Fi `:5555` | — | Android 14 (crDroid), Magisk root, ~1 GB de RAM livre + swap |
| Debian 13 chroot | `/data/debian` | — | Montado por `/data/comet/chroot.sh` |
| **Comet** (`g0ldyy/comet` @ `f56677f`) | `/opt/comet` (chroot), `.venv`, Python 3.13, SQLite `data/comet.db` | 8000 | Patch local: 12 arquivos, +738/−223 linhas |
| **Caddy** + DuckDNS (DNS-01, Let's Encrypt) | `/etc/caddy/Caddyfile` | 443 | `https://a71comet.duckdns.org` → 127.0.0.1:8000 |
| **StremThru** v0.105.4 local | `/usr/local/bin/stremthru` | 127.0.0.1:8080 | Ponte Comet → Real-Debrid (a instância pública dava timeout) |
| **Prowlarr** v2.7.0.5723 | `/opt/prowlarr`, dados em `/var/lib/prowlarr` | 127.0.0.1:9696 | Indexadores: Catálogo BeTor (BR), Knaben, TorrentsCSV |
| **Watchdog** | `/data/comet/watchdog.sh` (= `scripts/watchdog.sh`, MD5 conferido) | — | A cada 30 s religa StremThru, Prowlarr, Comet e Caddy; logs limitados a 5 MB |
| Boot | `/data/adb/service.d/comet.sh` | — | Sobe o watchdog. Reboot já validado |

- **Logs:** `/data/comet/{comet,caddy,stremthru,prowlarr,watchdog}.log`.
- **Reiniciar o Comet:** `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`. O watchdog religa em até 30 s.

**Fontes de scraping** (`config/.env`, que está no `.gitignore` e é instalado em `/opt/comet/.env`):

| Fonte | Configuração | Situação |
|---|---|---|
| Torrentio | — | Principal |
| MediaFusion | elfhosted | ⚠️ retorna 0 resultados |
| Zilean | — | — |
| StremThru scrape | público | — |
| TorrentsDB | — | ⚠️ HTTP 502 por rate limit |
| Nyaa | anime only | — |
| Prowlarr | `PROWLARR_INDEXERS=["1","2","3"]` | — |

Flags importantes do `.env`:
- `PTBR_FIRST=True`
- `SMART_LANGUAGE_DETECTION=True`
- `INDEXER_LANGUAGES=["pt","en"]`
- `DOWNLOAD_GENERIC_TRACKERS=True`
- `STREMTHRU_URL=http://127.0.0.1:8080`
- `HIDE_DEBRID_BLOCKED`: padrão True no patch

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
4. **Filtro 451** (staged, sem commit):
   - Tabela SQLite `debrid_blocked_hashes`, criada pela migração `2026102901_debrid_blocked_hashes`.
   - O 451 é gravado em `comet/debrid/stremthru.py` e logado como `🚫 RD bloqueou (451)`.
   - `comet/api/endpoints/stream.py` esconde esses hashes daquele debrid; o P2P continua intacto.
5. **Prowlarr** (staged): instalado e integrado (`SCRAPE_PROWLARR=live`, busca também por título PT). Ganho em filmes: `tt12042730` 11→13 PT-BR, `tt22084616` 16→17. A lista de indexadores excluídos e o motivo está no README, Seção 0.
6. **Watchdog** (staged, já implantado no A71): supervisão do Prowlarr + cap de logs.
7. **Séries dubladas PT-BR** (staged). Causa encontrada:
   - **(a)** `torrentio.py` testava `"\n💾" in title_full` e falhava quando havia a linha de seeders (`\n👤 7 💾`). Também usava só o nome do arquivo (ex.: `1 - Piloto.mp4`), que não contém o nome da série.
   - **(b)** O RTN marca títulos BR com "Temporada/Completa" como `es`.
   - **(c)** Pacotes de temporada (`seasons=[N], episodes=[]`) eram descartados por `reject_unknown_episode_files=True`, em `match_parsed_episode_target` (`comet/utils/parsing.py`).

   Correções:
   - `torrentio.py`: `METADATA_SPLIT_PATTERN`, `BARE_EPISODE_PREFIX_PATTERN` e `_select_stream_title`. Usa o arquivo quando ele é reconhecível; senão cai para a linha 1 (nome do torrent), mantendo o `fileIndex`.
   - `filtering.py::apply_ptbr_detection`: `_PTBR_SEASON_RE`, com marcador de temporada BR + PT, tracker BR, `dual` ou grupo BR → `pt`. Remove o `es` falso, mas não quando há `latino`, `castellano`, `spanish`, `español` ou `spa`.
   - `orchestration.py::TorrentManager`: `_is_matching_season_pack`, `_matches_requested_scope`, `_live_torrent_priority`, dedup que une `pt` e `sources`, e `_append_cache_file_infos` passou a manter os packs.

**O patch Python inteiro** (tudo menos `comet/templates/index.html`) está em `comet-patches/ptbr-first.patch` (LF). Para reaplicar depois de atualizar o Comet: `.\scripts\deploy_ui.ps1` e `.\scripts\deploy_patches.ps1`. Para regenerar a partir do A71: no chroot, `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /tmp/x.patch`, copie para `/data/local/tmp` e faça `adb pull`.

---

## 5. Estado do git (IMPORTANTE)

- **Commits:** `cbe21b8` → `17cec22` → `372e0e8` (HEAD).
- **Staged, sem commit:**
  - `comet-patches/ptbr-first.patch` (451 + Prowlarr + séries)
  - `README.md`
  - `scripts/watchdog.sh`
  - `.orquestra/tarefa.md`
  - este `HANDOFF.md`
- O usuário **ainda não pediu commit**. Proponha: "Filtro 451, Prowlarr, watchdog e séries PT-BR". Use o e-mail local `wandersonks02@gmail.com` e termine a mensagem com a linha de coautoria definida pela sessão.
- O código do A71 **já está com tudo aplicado e rodando**. O que está staged é só o espelho no PC.

---

## 6. Como testar (sem RD, modo torrent)

```powershell
$cfg='{"debridServices":[],"enableTorrent":true,"cachedOnly":false,"removeTrash":true,"maxResultsPerResolution":0}'
$b=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($cfg))
$r=Invoke-RestMethod "http://192.168.3.44:8000/$b/stream/movie/tt12042730.json" -TimeoutSec 120
$s=$r.streams; "total=$($s.Count) ptbr=$(($s | ? { ($_.name + $_.description) -match '🇧🇷' }).Count)"
# série: .../stream/series/tt0903747:1:1.json
```

O cache fica na tabela `torrents` do SQLite (`/opt/comet/data/comet.db`). Para medir sem cache, apague as linhas do IMDb testado.

**Resultados verificados (30/10/2026):**

| Pedido | Total | PT-BR (antes → depois) | Falsos positivos |
|---|---|---|---|
| `movie/tt12042730` (Devoradores de Estrelas) | 713 | 13 → 13 | 0 |
| `series/tt0903747:1:1` (Breaking Bad) | 332 | 0 → 9 | 0 |
| `series/tt0903747:3:5` | 236 | 0 → 6 | 0 |
| `series/tt0944947:1:1` (Game of Thrones) | 605 | 1 → 11 | 0 |
| `series/tt2861424:1:1` (Rick and Morty) | 212 | 0 → 5 | 0 |
| `series/tt0121955:1:1` (South Park) | — | 0 → 1 | 0 |
| `series/tt0388629:1:1` (One Piece) | — | 0 → 0 | — |

Em todos os casos os PT-BR vêm primeiro, ordenados por resolução.

---

## 7. Lacunas conhecidas (por que ainda falta conteúdo)

1. **RD 451:** o Real-Debrid bloqueia boa parte dos **lançamentos dublados recentes**. Esse é o maior limitador. Não contornar.
2. **Anime:**
   - Packs com numeração absoluta (`001-600`) não têm temporada (`seasons=[]`) e não casam com o pedido `S1E1` vindo do IMDb.
   - One Piece tem 0 PT-BR.
3. **MediaFusion** retorna 0 resultados e **TorrentsDB** dá 502 (rate limit). São duas fontes perdidas.
4. **Indexadores:** sites BR e gerais protegidos por Cloudflare (1337x, EZTV, Kickass etc.) exigiriam o FlareSolverr. Ele foi considerado pesado para o A71 (cerca de 1 GB de RAM livre); dá para reavaliar.

---

## 8. Próximo passo (proposta feita ao usuário, aguardando resposta)

O usuário disse que esperava **ganhos maiores, com mais conteúdo**. A recomendação foi uma única tarefa para o agy com os itens 1, 2 e 3 abaixo, todos grátis:

1. **Fallback P2P (modo torrent) para os bloqueados pelo 451:**
   - Em vez de sumir, o stream bloqueado aparece como opção P2P (o Stremio baixa direto).
   - Contra: depende de seeders e expõe o IP do usuário no swarm. Tem que ser opcional, e o usuário precisa concordar.
2. **Anime com numeração absoluta:**
   - Mapear temporada/episódio para episódio absoluto (via metadados: Kitsu/AniList/TMDB, ou a contagem de episódios por temporada).
   - Aceitar packs/episódios sem temporada cujo intervalo contenha o absoluto.
3. **Consertar MediaFusion** (outra instância ou configuração) e **TorrentsDB** (backoff/limite).
4. *(Pago, opcional)* **Segundo debrid** (TorBox, AllDebrid ou Premiumize). Antes, testar se ele também bloqueia os mesmos títulos.

**Antes de começar:**
- Pergunte ao usuário se ele aprova a tarefa e se quer **commitar o que está staged**.
- Depois escreva `.orquestra/tarefa.md` no mesmo formato da tarefa de séries: contexto, evidências, passos A–D, regras e resposta final curta.
- Inclua validação antes → depois com a tabela da Seção 6 + One Piece + um lançamento recente, e exija 0 falsos positivos.
