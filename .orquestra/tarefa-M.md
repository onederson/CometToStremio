# Tarefa M: fonte que está caindo é pausada sozinha (lista mais rápida)

## Contexto
- Comet no A71, chroot, `/opt/comet`. Hoje, quando uma fonte (Torrentio, MediaFusion, Comet, Zilean, Prowlarr, BRSites, Addons, Peerflix, SeaDex, links diretos FenixFlix/FrostStream...) está fora do ar, cada busca espera o timeout dela, e a 1ª lista de um título demora mais.
- Erros já passam por `log_scraper_error` → `record_source_error` (`comet/core/logger.py`); sucessos por `record_source_success`. Ache o ponto único onde os scrapers são chamados (provavelmente `comet/scrapers/manager.py` ou `comet/services/orchestration.py`) e onde os links diretos são buscados (`comet/services/direct_addons.py`, `_fetch_addon`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
1. `models.py`: `SOURCE_BREAKER: bool = True`, `SOURCE_BREAKER_FAILS: int = 3`, `SOURCE_BREAKER_PAUSE: int = 600`.
2. Novo `comet/core/breaker.py`: por nome de fonte (a instância, ex.: `Torrentio`, `MediaFusion Midnight`, `FenixFlix`), em memória:
   - `SOURCE_BREAKER_FAILS` erros **seguidos** (erro ou timeout; resposta vazia **não** conta) → fonte pausada por `SOURCE_BREAKER_PAUSE` s. Log uma vez: `⏸️ <fonte> pausada <min> min (<n> falhas seguidas)`.
   - Passada a pausa: deixa **1** pedido passar; sucesso → volta ao normal (`▶️ <fonte> voltou`); erro → pausa de novo pelo dobro (máx. 1 h).
   - Sucesso zera a contagem.
   - `is_open(name) -> bool`, `record(name, ok: bool)`, `snapshot() -> list[dict]`.
3. Ligue nos scrapers de torrent e nos links diretos: fonte pausada é pulada na hora (sem requisição), com log `debug`. Não pule nada nas buscas internas do smoke/regress? **Pule igual** (é o comportamento real).
4. `/status`: na seção **Fontes**, coluna "Estado" (`ok` / `pausada até HH:MM` / `testando`).
5. Nunca pause o Real-Debrid, o TorBox, o StremThru nem o TMDB/Cinemeta (fora do escopo do breaker).

## Fora de escopo
Tudo o resto. Não mude timeouts nem a ordem das fontes.

## Aplicar
`py_compile`; reinicie (polling `curl` no `manifest`); `git -C /opt/comet add -N comet/core/breaker.py`; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação
1. Unidade (script Python no chroot importando `comet.core.breaker`, com o tempo simulado): 3 falhas → aberto; antes da pausa → pulado; depois → 1 passa; sucesso → fechado; falha no teste → pausa dobrada.
2. Integrado: com uma variável de ambiente só de teste **ou** apontando temporariamente uma fonte para `http://127.0.0.1:9` (porta fechada) **sem mexer no `.env`** (ex.: override por variável de ambiente no processo de teste não serve, porque o Comet roda no watchdog; então faça o teste chamando a função de busca de um scraper direto num script, com a URL trocada em memória): 3 buscas → log `⏸️`; a 4ª não faz requisição.
3. Tempo da 1ª lista de um título ainda não buscado antes/depois com uma fonte pausada (se nenhuma estiver fora do ar, diga que o ganho só aparece quando alguma cai).
4. `/status` mostra a coluna Estado.
5. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
