# Tarefa: (1) esconder torrents bloqueados pelo RD (451) e (2) Prowlarr local com indexadores BR

Contexto: PowerShell em `C:\Users\Vendel\Desktop\Projetos\a71\STREMIO`. Comandos no A71: `.\scripts\a71.ps1 '<cmd>'` (root Android) / `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian). Comet em `/opt/comet` (git; já tem patch local — veja `git -C /opt/comet diff --stat`). StremThru local em `127.0.0.1:8080`. Leia README Seção 0 e "Pegadinhas". Reinício do Comet: `pkill -f "python -m comet.main"` (watchdog religa em ≤30 s).

---
## PARTE 1 — Esconder torrents com 451 (infringing_file)

Diagnóstico: ao dar play num torrent não cacheado, `comet/debrid/stremthru.py` (`generate_download_link` → `_post_store_json` em `/magnets`) recebe do StremThru HTTP 451, `code: "UNAVAILABLE_FOR_LEGAL_REASONS"`, `upstream_cause` `{"error":"infringing_file","error_code":35}`. O RD bloqueou aquele hash. Esses itens continuam aparecendo na lista e o usuário perde cliques.

Implemente (mudança mínima):
1. Tabela SQLite nova `debrid_blocked_hashes(debrid_service TEXT, info_hash TEXT, reason TEXT, blocked_at INTEGER, PRIMARY KEY(debrid_service, info_hash))`, criada no mesmo mecanismo que o Comet usa para criar/migrar as outras tabelas (descubra qual; não crie à mão fora dele).
2. Quando `/magnets` retornar 451/`UNAVAILABLE_FOR_LEGAL_REASONS`, gravar `(service, hash, "infringing_file", now)` (upsert). Logar `🚫 RD bloqueou (451) <hash> <nome>`. Manter o vídeo de status atual para esse clique.
3. Na montagem da lista de streams (`comet/api/endpoints/stream.py`), NÃO emitir streams debrid daquele serviço para hashes bloqueados (consulta única por request, em lote). Modo torrent/P2P não é afetado.
4. Nova setting `HIDE_DEBRID_BLOCKED: bool = True` (models.py) controlando o item 3.
5. Não toque em nada de cached/availability além do necessário.

Validação da Parte 1 (sem usar a chave RD do usuário):
- Inserir manualmente na tabela um hash conhecido de `tt12042730` (ex.: o 1º PT-BR da lista atual) para `realdebrid`, e provar que o filtro funciona: chame `/stream` com uma config b64 que tenha `debridServices:[{"service":"realdebrid","apiKey":"teste"}]` e `cachedOnly:false` e verifique que aquele hash some (o Comet pode mostrar erro de chave inválida — isso é aceitável; se impedir o teste, teste a função de filtro isoladamente em Python). Depois REMOVA o registro de teste.
- `py_compile` de todos os arquivos alterados.

---
## PARTE 2 — Prowlarr local com indexadores brasileiros

Objetivo: mais fontes de releases DUBLADOS/DUAL PT-BR. O Comet já tem scraper nativo `prowlarr` (`SCRAPE_PROWLARR`, `PROWLARR_URL`, e a variável de API key — confira os nomes exatos em `comet/core/models.py` e `comet/scrapers/prowlarr.py`/`services/indexer_manager.py`).

1. Instale o **Prowlarr** (versão estável, `linux-core-arm64`) no chroot em `/opt/prowlarr`, dados em `/var/lib/prowlarr`. Instale dependências que ele exigir (ex.: `libicu`, `sqlite3`). Bind **somente** `127.0.0.1:9696` (config.xml: `BindAddress`=127.0.0.1, `AuthenticationMethod`/`AuthenticationRequired` adequados para uso local). Log em `/data/comet/prowlarr.log`.
2. Pela API do Prowlarr (`/api/v1/indexer/schema`), liste TODOS os indexadores públicos com idioma `pt`/`pt-BR` ou sites brasileiros conhecidos (ex.: Comando, BluDV, Torrent dos Filmes, VacaTorrent, ApacheTorrent, RedeTorrent, LAPUMiA, Filmes Torrent, StarckFilmes, BaixaFilmes, Wolverdon, ThePirataFilmes, BeTor — use o que existir). Adicione cada um e rode o teste (`/api/v1/indexer/test`). Mantenha **só os que passam**. NÃO instale FlareSolverr (pesado demais); indexadores que exigem Cloudflare bypass ficam de fora — liste-os no relatório.
3. Adicione também 2–3 indexadores públicos gerais confiáveis que passem no teste (ex.: 1337x se passar, TheRARBG, Knaben, EZTV, YTS) — só se não forem redundantes com o Torrentio; justifique.
4. Ligue no Comet: `SCRAPE_PROWLARR=live`, URL `http://127.0.0.1:9696`, API key e IDs de indexadores conforme o Comet exige. Atualize `config\.env` (LF, preserve o resto) e o `.env` no A71 (método do README, chmod 600). **A API key do Prowlarr não pode aparecer em README, `.orquestra/` nem na resposta final.**
5. Verifique que o Comet busca títulos em português para o Prowlarr (log `Indexer titles`, `INDEXER_LANGUAGES=["pt","en"]` já existe). Ex.: `tt12042730` deve buscar "Devoradores de Estrelas".

Validação da Parte 2 (modo torrent, sem RD): config b64 `{"debridServices":[],"enableTorrent":true,"cachedOnly":false,"removeTrash":true,"maxResultsPerResolution":0}`:
- `tt12042730` e `tt22084616`: conte streams `🇧🇷 PT-BR` ANTES (anote da lista atual) e DEPOIS do Prowlarr; quantos vieram com fonte Prowlarr (campo 🔎 na description); liste até 8 títulos PT-BR novos.
- Um título PT-BR mais antigo, ex. `tt0110357` (O Rei Leão 1994): quantos PT-BR.
- Tempo total da busca (primeira busca, sem cache) — não pode passar de ~30 s; se passar, ajuste timeouts/indexadores e explique.
- RSS do Prowlarr e do Comet; RAM livre do A71 (`free -m`).

---
## Watchdog
NÃO edite `scripts/watchdog.sh`. No relatório, dê o comando de start do Prowlarr em UMA linha no padrão de `start_stremthru` (via `"$BASE/chroot.sh" -c '... exec ...'`, log `>> "$BASE/prowlarr.log"`) e um padrão `pgrep -f` único (teste no Toybox do Android). Deixe o Prowlarr rodando ao final.

## Patch e README
- Regenere `comet-patches\ptbr-first.patch` com TODO o diff Python atual (`git -C /opt/comet diff -- comet/ ':!comet/templates/index.html'`, via `/data/local/tmp` + `adb pull`, LF, apague temporários).
- README Seção 0 + "Mapa de arquivos": filtro 451 (`HIDE_DEBRID_BLOCKED`), Prowlarr (versão, porta local, indexadores ativos, os que ficaram de fora e por quê). Mudanças mínimas.

## Regras
- Não altere `scripts/`, `comet-ui/`, Caddy, StremThru, AdGuard.
- Não exponha Prowlarr na LAN nem no Caddy. Não imprima chaves.
- NÃO tente contornar o bloqueio 451 do Real-Debrid (nada de alterar hashes/magnets para enganar o RD). A Parte 2 é só ampliar fontes legítimas de busca.

## Resposta final (máx. 14 linhas)
P1: arquivos alterados, onde grava/filtra, resultado do teste. P2: versão do Prowlarr, indexadores ativos (nomes), excluídos (e motivo), PT-BR antes→depois em tt12042730/tt22084616/tt0110357, tempo de busca, RSS e RAM livre, comando de start + pgrep, pendências.
