# Tarefa I: página de status + memória de "arquivo dublado" que sobrevive ao reinício

## Contexto
- Comet no A71, chroot, `/opt/comet`. Arquivos: novo `comet/api/endpoints/status.py` (registrar em `comet/api/app.py` como os outros), `comet/services/direct_addons.py`, `comet/services/subtitles.py` (`remember_pt_filename`), `comet/core/logger.py` (se precisar de contadores), `comet/core/models.py`.
- `smoke_last.json` em `/opt/comet/data/` (criado pela Tarefa G): `{"ts","ok","checks":[{"name","ok","why","secs"}]}`.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF.
- **PROIBIDO:** imprimir chaves/tokens; a página **nunca** mostra chaves, tokens, URLs com config ou e-mails; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 120 s.

## 1. `/status` (só com o token pessoal: `GET /{PERSONAL_LINK_TOKEN}/status`; qualquer outro prefixo → 404)
HTML simples em PT-BR, tema escuro, legível no celular, `<meta http-equiv="refresh" content="60">`. Seções:
- **Geral:** versão do manifest, há quanto tempo o Comet está no ar, memória do A71 (`/proc/meminfo`: MemAvailable, SwapFree) e RSS do processo.
- **Teste automático:** resultado do `smoke_last.json` (hora, OK/FALHA, cada checagem com tempo); se o arquivo não existir, "ainda não rodou".
- **Fontes (últimas 6 h):** por scraper/fonte (Torrentio, MediaFusion, Comet, Zilean, Prowlarr, BRSites, Addons, diretos FenixFlix/FrostStream, legendas OpenSubtitles/SubSource/SubDL, TMDB): nº de sucessos, nº de erros e o último erro (texto curto, **sem URL**). Implemente com contadores em memória alimentados nos pontos onde já se loga sucesso/erro (ex.: `log_scraper_error`, `_fetch_addon`, `_fetch_subsource`).
- **Links diretos:** último `🌐 diretos: v/t` e a lista de hosts que o DNS da casa bloqueia (de `_HOUSE_DNS_CACHE` com `is_blocked`), com a dica "libere no AdGuard: `@@||<host>^$important`".
- **Debrid:** quantos hashes marcados 451 no RD (tabela `debrid_blocked_hashes`), se o TorBox está configurado (sim/não, sem chave).
- **Playback (últimas 6 h):** nº de plays, nº que estourou o `PLAYBACK_BUDGET`, nº de trocas do 451.

## 2. Memória de arquivo dublado persistente
`remember_pt_filename` hoje é só memória (zera ao reiniciar). Guarde também numa tabela SQLite `pt_filenames(filename TEXT PRIMARY KEY, seen_at INTEGER)` (crie se não existir, do jeito que o Comet já cria tabelas — veja `schema_specs.py`/`schema_migrations.py`), carregue na subida, apague entradas com mais de 90 dias, máx. 50 mil.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (polling `curl` no `manifest`); `.\scripts\smoke.ps1` → `SMOKE OK`; patch (`git add -N` dos novos; `git diff -- . ':!comet/templates/index.html'`; `adb pull` para `comet-patches/ptbr-first.patch`; apague temporários; zero `\r`).

## Verificação
1. `/{token}/status` → 200 com as seções (mostre só os títulos das seções e 3 linhas de exemplo, **sem** o token); `/qualquer/status` e `/status` → 404.
2. `grep` no HTML: nenhuma ocorrência do token, de `apiKey`, de `TORBOX`, de `@` de e-mail, nem de `http` com `/stream/`.
3. Memória persistente: peça a lista de um título com 🇧🇷, reinicie o Comet, e mostre que a tabela tem os nomes e que o pedido de legendas para um desses arquivos volta vazio depois do reinício.
4. `smoke.ps1` → `SMOKE OK`.

Responda em no máximo 5 linhas: arquivos alterados e resultado da verificação.
