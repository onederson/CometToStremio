# Tarefa: Comet "PT-BR primeiro" — detecção melhor, ordenação e rótulo 🇧🇷

Contexto: PowerShell em `C:\Users\Vendel\Desktop\Projetos\a71\STREMIO`. Comandos no A71: `.\scripts\a71.ps1 '<cmd>'` (root Android) / `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian). O Comet está em `/opt/comet` (chroot), é um repositório git limpo (exceto `comet/templates/index.html`, traduzido). Use o `.venv/bin/python` do Comet. O watchdog religa o Comet em até 30 s após `pkill -f "python -m comet.main"`.

## Objetivo do usuário
Na lista de streams do Stremio (addon Comet A71), vir PRIMEIRO todo o conteúdo PT-BR agrupado por resolução: **4K PT-BR → 1080p PT-BR → 720p PT-BR → (demais resoluções PT-BR)**, e DEPOIS todo o resto na ordem normal do Comet. E identificar visualmente os PT-BR.

## Diagnóstico já feito pelo orquestrador (não refaça, use)
- O ranking vem de `comet/services/ranking.py` (`rank_worker` → RTN `sort_torrents`, que agrupa por resolução e ordena por rank). Preferred=pt dá só +10000 e REMUX em inglês passa disso → dublado fica em ~#42.
- A detecção de idioma: RTN `parse()` + "smart language detection" em `comet/services/filtering.py` (`filter_worker`, ~linha 307–360, adiciona idioma via alias de título). Ex.: `Devoradores de Estrelas 2026 WEB-DL 1080p ... DUAL 5.1` (tracker `Torrentio|Comando`/`Torrentio|BluDV`) é detectado como pt; `Project.Hail.Mary.2026.1080p.iT.WEB-DL...DUAL-BiOMA` NÃO é.
- Depois do ranking, o Comet separa cached/uncached ao montar a resposta (veja `comet/services/media_search.py`, `sortCachedUncachedTogether`). A ordenação final PT-BR precisa ser aplicada no ponto em que a lista FINAL de streams é montada, para não ser desfeita depois.

## Passo A — Detecção PT-BR (em `filter_worker`, após a smart detection, antes do ranking)
Marque `'pt'` em `parsed.languages` (se ainda não tiver) quando:
1. O tracker/fonte do torrent contiver (case-insensitive) `Comando`, `BluDV`, `MicoLeaoDublado`; OU
2. O título contiver `dublado`, `dub[ .-]?pt`, `nacional`, `pt-?br`, `portugu[eê]s`, `\bpor\b` (só junto de `dual`/`audio`); OU
3. O título tiver `dual` E terminar/contiver um release group BR da lista configurável `PTBR_RELEASE_GROUPS` (env, CSV; default: `BiOMA,C76,WOLVERDONFILMES,COMANDO,BLUDV,VACATORRENT,LAPUMiA,TBS,SF`).
NÃO marque pt se o título indicar latino/espanhol (`\blat\b`, `latino`, `castellano`, `\besp\b`, `spanish`) sem um marcador PT explícito do item 2.
Descubra no código como o tracker chega no `filter_worker` (campo do dict do torrent) — não suponha.

## Passo B — Ordenação PT-BR primeiro
Nova setting `PTBR_FIRST: bool = True` (em `comet/core/models.py`, junto das outras settings; defina também no `.env`).
No ponto onde a lista final de streams é montada: particionar de forma ESTÁVEL em grupo PT (idiomas contêm `pt`) e resto. Grupo PT ordenado por resolução (2160p, 1440p, 1080p, 720p, 576p, 480p, 360p, 240p, unknown); dentro de cada resolução, cached antes de uncached, mantendo a ordem de rank original. O resto fica exatamente como o Comet já ordenaria. Respeitar `maxResultsPerResolution` como hoje (não deve cortar PT-BR por causa dos outros — se o corte acontece antes, garanta que PT-BR não seja descartado em favor de não-PT; explique no relatório o que fez).

## Passo C — Rótulo visual
Para streams PT, prefixe o campo `name` do stream (coluna esquerda no Stremio) com `🇧🇷 PT-BR` + quebra de linha, mantendo o resto do name original. Não altere `description` nem `url`/`behaviorHints`.

## Passo D — .env, patch e reaplicação
- Adicione `PTBR_FIRST=True` em `config\.env` (LF) e no `/data/debian/opt/comet/.env` (mesmo método do README, chmod 600). Não adicione `PTBR_RELEASE_GROUPS` (usar o default).
- `python -m py_compile` em todos os .py alterados. Reinicie o Comet.
- Salve o patch das mudanças Python (exclua `comet/templates/index.html`) em `comet-patches\ptbr-first.patch` no PC (via `git -C /opt/comet diff -- comet/ ':!comet/templates/index.html'`, copiando por `/data/local/tmp` + `adb pull`, apagando o tmp). LF.
- Crie `scripts\deploy_patches.ps1` (curto, comentado em PT): envia o patch, faz `git -C /opt/comet apply --check` e `apply` (pulando se já aplicado: `git apply --reverse --check`), e reinicia o Comet.

## Passo E — Validar (sem Real-Debrid; config de teste em modo torrent)
Gere a config base64 de `{"debridServices":[],"enableTorrent":true,"cachedOnly":false,"removeTrash":true,"maxResultsPerResolution":0,"languages":{"preferred":["pt"],"allowed":["pt","en","ja"]}}` e chame `http://192.168.3.44:8000/<b64>/stream/movie/tt12042730.json` (Devoradores de Estrelas) e `tt22084616`:
- Os primeiros itens devem ser todos 🇧🇷 PT-BR, em blocos 2160p → 1080p → 720p; o primeiro não-PT só depois do último PT.
- Liste no relatório os 8 primeiros `name`+arquivo e a posição do primeiro não-PT.
- Confirme que nenhum título com `Lat`/`latino` virou PT.
- Repita com `maxResultsPerResolution: 5` e confirme que PT-BR continua presente.
- Teste também um episódio: `series/tt0121955:1:1`.
- `https://a71comet.duckdns.org/manifest.json` OK.

## Passo F — README
Seção 0 + "Mapa de arquivos": patch PT-BR primeiro, `comet-patches/ptbr-first.patch`, `scripts/deploy_patches.ps1`, `PTBR_FIRST`. Nota: após `git pull` do Comet, reaplicar `deploy_ui.ps1` e `deploy_patches.ps1`. Mudanças mínimas.

## Regras
- Não altere `scripts/` existentes, `comet-ui/`, Caddy, watchdog, AdGuard.
- Mudanças no Comet mínimas e localizadas; nada de refatorar.
- Se o comportamento pedido for impossível em algum ponto, faça o mais próximo e EXPLIQUE no relatório.

## Resposta final (máx. 12 linhas)
Arquivos do Comet alterados (e onde aplicou a ordenação), como o tracker chega ao filtro, os 8 primeiros resultados de tt12042730, posição do primeiro não-PT, resultado com maxResults=5, falsos positivos encontrados, pendências.
