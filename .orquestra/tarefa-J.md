# Tarefa J: suíte de testes de regressão (integrados e automáticos)

## Objetivo
Garantir que nada do que já funciona quebre nas próximas mudanças. Uma suíte que roda no A71 contra o Comet real e diz PASS/FAIL/WARN por teste.

## Contexto
- Comet no A71, chroot Debian, `/opt/comet`, escuta em `http://127.0.0.1:8000`. Python: `/opt/comet/.venv/bin/python` (tem `httpx`). **Não instale pacotes.**
- Já existe `scripts/smoke.py` (instalado em `/opt/comet-tools/smoke.py`) e `scripts/smoke.ps1`. Copie deles o jeito de ler o `.env` (`load_env`), trocar o domínio público por `127.0.0.1:8000` (`rewrite_url`) e o wrapper PowerShell (push + bind-mount do log). **Não altere o comportamento do smoke.**
- Links: pessoal `/<PERSONAL_LINK_TOKEN>/...`, kids `/<KIDS_LINK_TOKEN>/...` (os dois no `.env`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (root Android) / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb -s 192.168.3.44:5555 push` pelo **PowerShell** para `/data/local/tmp/` + `mv` para `/data/debian/var/tmp/`. Tudo em LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token (no terminal, nos arquivos de resultado e nas mensagens de falha: troque o token por `<token>`); commit; instalar pacotes; mexer no AdGuard ou no `.env`; alterar código do Comet (`/opt/comet/comet/...`), exceto o item 4. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## 1. `scripts/regress.py` (novo; instalado em `/opt/comet-tools/regress.py`)
Cada teste é uma função `t_<nome>()` que devolve `("PASS"|"FAIL"|"WARN", motivo curto)`. Exceção dentro do teste = FAIL com o tipo + mensagem curta. Timeout por requisição 25 s. Rode os testes HTTP com no máx. 4 em paralelo (threads). Meta: a suíte inteira em ≤ 4 min.

### A. Testes de unidade (sem rede, importando o Comet)
Rode com `sys.path.insert(0, "/opt/comet")` e o cwd `/opt/comet`. Escolha **pelo menos 12** funções puras que já existem (leia o código; não invente assinaturas) e grave o comportamento atual como asserts (testes de caracterização). Obrigatórios:
- `filtering.is_cam_release` (CAM/TS → True; WEB-DL 1080p → False);
- conversões `_ass_to_srt` e `_vtt_to_srt` de `subtitles.py` (entrada pequena → SRT com `-->` e numeração);
- detecção de PT-BR/dublado usada no ranking/rótulo 🇧🇷 (ache a função; "Dublado", "Dual Áudio", "PT-BR" → PT; um nome só em inglês → não);
- `select_debrid_refresh_hashes` de `media_search.py` (com `services`);
- a lógica de "próximo episódio" de `prefetch.py` (último episódio da temporada → S+1:1);
- a escolha da prioridade RD ⚡ → TB ⚡ → RD ⬇️ → TB ⬇️ em `stream.py`, se estiver numa função isolável; se não estiver, pule e diga por quê no relatório.

### B. Testes integrados (HTTP no Comet real, link pessoal)
1. `manifest`: 200; `resources` contém catalog, meta, stream, subtitles; ≥ 30 catálogos; `version` começa com `2.1.`.
2. `catalogos`: **todos** os catálogos do manifest pessoal sem extra obrigatório: 200 e JSON com `metas`. Os não pessoais (id sem `mylist`/`newep`/`foryou`) com ≥ 5 itens (menos = FAIL; os pessoais vazios = WARN). Todo `poster`/`background` presente começa com `https://` (relativo = FAIL, diga quantos e em que catálogo).
3. `capa`: baixe 1 pôster do Top 10 (troque o domínio por `127.0.0.1:8000`): 200, `content-type` `image/*`, > 5 KB.
4. `busca`: `comet_search` filme `batman` ≥ 3; `comet_person` filme `Tom Hanks` ≥ 3.
5. `meta_filme`: `tt0111161` → `name` em PT (`Um Sonho de Liberdade`), `description` não vazia. `meta_serie`: `tt0903747` → `videos` ≥ 60.
6. `stream_filme` `tt12042730`, `stream_serie` `tt2293002:1:2`, `stream_anime` `tt0388629:1:1`: ≥ 5 streams (anime ≥ 20); se houver algum ⚡, o 1º se chama `▶ Assistir`; **nenhum infoHash repetido** (fora o `▶ Assistir`, que é cópia de outro); na série, ≥ 1 com `🇧🇷`; nos 5 primeiros não há CAM se existir algum não-CAM (use o mesmo critério de `is_cam_release` no `behaviorHints.filename`/descrição).
7. `kids`: manifest do Kids 200 com id terminando em `.kids`; 3 catálogos dele com ≥ 5 itens; stream de `tt2293002:1:2` pelo Kids 200.
8. `legendas`: pedido de legendas com `filename` claramente PT (`Ben.10.Omniverse.S01E02.1080p.WEB-DL.DUAL.PT-BR.mkv`) → lista vazia. Pedido de um filme com filename inglês → 200 JSON (vazio por cota = WARN).
9. `status`: `/<token>/status` 200 e o HTML **não contém** o token, `apiKey`, `TORBOX`; `/x/status` e `/status` → 404.
10. `configure`: `/configure` 200.
11. `play`: o `▶ Assistir` do filme do item 6, seguindo redirecionamentos com `User-Agent: ExoPlayerLib/2.19.1` e `Range: bytes=0-1023` → 200/206 e `content-type` de vídeo ou `application/octet-stream`, em ≤ 20 s. Sem `▶ Assistir` = WARN.
12. `log`: no trecho do `comet.log` escrito durante a suíte (offset como no smoke), nenhum `Traceback`, `NameError`, `AttributeError`, `TypeError`.

### C. Linha de base (pega queda de qualidade)
- `--save-baseline` grava `/opt/comet/data/regress_baseline.json` com: nº de streams, nº de ⚡ e nº de 🇧🇷 de cada título do item 6 e nº de itens de cada catálogo.
- Numa execução normal, se a linha de base existir: queda > 60 % em qualquer número → WARN (não FAIL: fontes oscilam); se cair a 0 algo que era ≥ 5 → FAIL.

### Saída
- Terminal: uma linha por teste `PASS|FAIL|WARN  <nome>  <segundos>s  <motivo>` e no fim `REGRESS OK (<p> pass, <w> warn)` ou `REGRESS FALHOU (<f> fail: <nomes>)`. Código de saída 0 só sem FAIL.
- Grava `/opt/comet/data/regress_last.json` `{"ts","ok","tests":[{"name","status","why","secs"}]}` (sem token).
- Argumentos: `--only <nome1,nome2>`, `--skip-unit`, `--save-baseline`, `--log-file`, `--log-offset`.

## 2. `scripts/regress.ps1` (novo)
Igual ao `smoke.ps1`: instala `regress.py` em `/opt/comet-tools/`, faz o bind-mount do log, roda e devolve o código de saída. Repassa `-Only`, `-SaveBaseline`, `-SkipUnit`.

## 3. Ligar no deploy
`scripts/deploy_patches.ps1` e `scripts/deploy_ui.ps1`: depois do `smoke.ps1`, rodar `regress.ps1`. Se falhar, imprimir em vermelho `REGRESSÃO: <nomes>` e sair com código 1 (sem restaurar sozinho; isso continua sendo do smoke).

## 4. `/status`
Em `comet/api/endpoints/status.py`, nova seção **Testes de regressão** lendo `regress_last.json` (hora, OK/FALHA, contagem e os nomes dos que falharam/avisaram). Sem o arquivo: "ainda não rodou". Depois: `py_compile`, reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`) e regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Fora de escopo
Qualquer mudança de comportamento do Comet além do item 4. Se um teste falhar porque o Comet tem um bug, **não corrija o Comet**: deixe o FAIL e descreva o bug na resposta.

## Verificação
1. `.\scripts\regress.ps1 -SaveBaseline` e depois `.\scripts\regress.ps1`: mostre a saída inteira (sem token).
2. Prove que a suíte pega quebra: rode só `--only stream_serie` com uma variável de ambiente `REGRESS_SELFTEST=1` que faz o teste usar um id inexistente (`tt0000000:1:1`) e mostre o FAIL e o código de saída 1.
3. `grep` em `regress_last.json` e na saída: nenhum token.
4. `.\scripts\smoke.ps1` → `SMOKE OK`.

Responda em no máximo 8 linhas: arquivos alterados, resultado da suíte (pass/warn/fail) e qualquer bug do Comet encontrado.
