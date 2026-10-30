# Tarefa: proteger memória + FlareSolverr + indexadores BR

São 3 etapas independentes. **Faça só a etapa pedida no comando.** Ao terminar a etapa, pare e responda.

## Contexto
- **Comandos no A71:**
  - `.\scripts\a71.ps1 '<cmd>'` roda no Android (root).
  - `.\scripts\a71.ps1 -Chroot '<cmd>'` roda no Debian em `/data/debian`.
- **Arquivos enviados ao aparelho:**
  - Use PowerShell com `adb push` para `/data/local/tmp`, depois mova.
  - Os arquivos devem ficar em LF, nunca CRLF.
- **Watchdog:**
  - A cópia do repositório é `scripts/watchdog.sh`; a do aparelho é `/data/comet/watchdog.sh`. As duas precisam ficar idênticas (confira o MD5).
  - Ele roda em `/system/bin/sh` (toybox, sem bash).
- **Memória medida hoje:**
  - Total 5,5 GB; disponível ~3,4 GB; swap de 2,7 GB.
  - Comet ~210 MB + forkserver ~145 MB; Prowlarr ~356 MB; StremThru 88 MB; AdGuardHome 84 MB; Caddy 20 MB.
- **Hoje todos os serviços estão com `oom_score_adj=-1000`, mas só por herança do Magisk.** Nenhum script define isso. Se o watchdog for reiniciado pelo `adb shell`, perde a proteção.
- **PROIBIDO:**
  - Alterar qualquer arquivo em `/data/adguard/` ou a configuração do AdGuard. Pode apenas escrever em `/proc/<pid>/oom_score_adj` do processo dele.
  - Imprimir a chave do Prowlarr, a chave do RD ou o token do DuckDNS.
  - Fazer commit.

---

## Etapa 1: proteção de memória (só `scripts/watchdog.sh` + script novo)

### 1.1 Proteção explícita contra o killer de memória
No watchdog, crie a função `protect()`, chamada a cada volta do loop. Ela escreve `-1000` em `/proc/<pid>/oom_score_adj` de:
- Comet: `pgrep -f 'python -m comet.main'` e os filhos dele, incluindo o `multiprocessing.forkserver` de `/opt/comet/.venv`;
- StremThru, Prowlarr e Caddy (os mesmos padrões de `pgrep` já usados no loop);
- AdGuard: `pgrep -f '/data/adguard/AdGuardHome/AdGuardHome'`, e também o processo `/data/adguard/watchdog.sh`;
- o próprio watchdog (`$$`).

Regras:
- Escreva só se o valor atual for diferente, para não gerar trabalho à toa.
- Ignore erros: o processo pode ter morrido entre o `pgrep` e a escrita.

### 1.2 Liberar memória matando coisas do Android
- **Função `free_mem()`, a cada volta do loop:**
  - Leia `MemAvailable` de `/proc/meminfo`.
  - Se ficar abaixo de **600 MB**, rode `am kill-all`. Esse comando mata só processos de apps em segundo plano, nunca os nossos.
  - Registre em log `memoria baixa (X MB), am kill-all`.
  - Rode no máximo 1 vez a cada 5 min (guarde o horário em variável).
- **Script novo `scripts/android-apps.sh`, com dois modos:**
  - `disable`: roda `pm disable-user --user 0` em cada pacote abaixo. Ignore os que não existirem.
  - `enable`: roda `pm enable` nos mesmos pacotes (reverte tudo).
  - Pacotes: `io.chaldeaprjkt.gamespace`, `org.omnirom.omnijaws`, `com.android.settings.intelligence`, `com.android.emergency`.
  - **NÃO incluir** `com.android.cellbroadcastreceiver*` (alertas da Defesa Civil), launcher, systemui, teclado, phone nem networkstack.
- Copie o script para `/data/comet/android-apps.sh` e rode `disable` uma vez.

### 1.3 Aplicar
1. Envie o watchdog e mate o watchdog antigo (o pid está em `/data/comet/watchdog.pid`). Os serviços continuam rodando.
2. Suba o novo com `nohup /system/bin/sh /data/comet/watchdog.sh >/dev/null 2>&1 &` pelo `adb shell`, de propósito, para provar que a proteção não depende do Magisk.

### Verificação da etapa 1
- `cat /proc/<pid>/oom_score_adj` dá `-1000` para: Comet, forkserver, StremThru, Prowlarr, Caddy, AdGuardHome e os dois watchdogs. Mostre a lista (pid, valor, nome).
- `pm list packages -d` mostra os 4 pacotes desativados.
- Teste do `free_mem`:
  1. Rode a função uma vez com o limite trocado temporariamente para 99999 MB.
  2. Confirme a linha no `watchdog.log`.
  3. Volte o limite para 600 MB.
- Os MD5 de `scripts/watchdog.sh` e `/data/comet/watchdog.sh` batem.
- `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/manifest.json` dá `200`.

---

## Etapa 2: FlareSolverr no chroot

### 2.1 Instalação
- **Pacotes do Debian:** `apt-get install -y chromium chromium-driver xvfb`.
- **Código:**
  - Clone o FlareSolverr na última tag estável do GitHub (`FlareSolverr/FlareSolverr`) em `/opt/flaresolverr`.
  - Crie a venv `.venv` com Python 3.13 e rode `pip install -r requirements.txt`.
- **arm64:** o FlareSolverr precisa usar o Chromium e o chromedriver do sistema (`/usr/bin/chromium`, `/usr/bin/chromedriver`).
  - Se ele tentar baixar driver x86, resolva com a variável de ambiente ou o caminho que o próprio código aceita.
  - Se não houver jeito por configuração, faça a menor mudança possível em `src/utils.py` e salve como `comet-patches/flaresolverr-arm64.patch`.
- **Ambiente:** `HOST=127.0.0.1`, `PORT=8191`, `LOG_LEVEL=info`, `HEADLESS=true`, `TZ=America/Sao_Paulo`.

### 2.2 Watchdog
- Adicione `start_flaresolverr` no mesmo estilo dos outros: via `chroot.sh`, log em `/data/comet/flaresolverr.log` com `cap_log`.
- O FlareSolverr é **descartável**:
  - Em `protect()`, defina `oom_score_adj=200` para ele e todos os processos `chromium` filhos. Nunca `-1000`: se a memória acabar, ele morre antes dos nossos serviços.
  - Limite de memória: some o RSS (`VmRSS`) do FlareSolverr e dos filhos `chromium`. Se passar de **900 MB**, mate o grupo inteiro e registre em log. O loop religa.
- Envie e reinicie o watchdog como na etapa 1.

### Verificação da etapa 2
- `curl -s -X POST http://127.0.0.1:8191/v1 -H 'Content-Type: application/json' -d '{"cmd":"request.get","url":"https://nowsecure.nl","maxTimeout":60000}'` responde `"status": "ok"`. Mostre só `status`, `message` e o tempo.
- RSS total do FlareSolverr + chromium parado e logo após o teste.
- `oom_score_adj` dele = 200 e dos serviços continua -1000.
- Os MD5 do watchdog batem.

---

## Etapa 3: indexadores BR no Prowlarr

A API do Prowlarr fica em `http://127.0.0.1:9696/api/v1`. Leia a chave de `/var/lib/prowlarr/config.xml` para uma variável, sem imprimir.

1. **Proxy:** crie um proxy `FlareSolverr` (`POST /indexerProxy`) com host `http://127.0.0.1:8191/`, timeout de 60 s e tag `flaresolverr` (crie a tag se não existir).
2. **Candidatos:**
   - Em `GET /indexer/schema`, filtre os indexadores **públicos** com idioma `pt-BR` (ou descrição que indique Brasil).
   - Liste nome e `definitionName`.
3. **Para cada candidato:**
   - Adicione com a tag `flaresolverr` e as categorias padrão.
   - Rode `POST /indexer/test`.
   - Mantenha só os que passarem; apague os que falharem.
   - Registre o motivo de cada falha.
4. **Busca de prova:**
   - Para cada indexador mantido, faça `GET /search?query=Breaking%20Bad&indexerIds=<id>&type=search`.
   - Registre o número de resultados e o tempo.
   - Remova o indexador se demorar mais de 25 s (o Comet usa `INDEXER_MANAGER_TIMEOUT=30`) ou trouxer 0 resultados.
5. **Comet:**
   - Atualize `PROWLARR_INDEXERS` em `/opt/comet/.env` e em `config/.env`, com os IDs antigos (`1`, `2`, `3`) mais os novos.
   - Reinicie o Comet (`pkill -f "python -m comet.main"`).

### Verificação da etapa 3
- Use a configuração de teste em modo torrent, sem RD: base64 de `{"debridServices":[],"enableTorrent":true,"cachedOnly":false,"removeTrash":true,"maxResultsPerResolution":0}`.
- Antes de cada pedido, apague do `data/comet.db` as linhas `torrents` daquele `media_id`.
- Compare total e PT-BR (contando '🇧🇷' em name+description) com a referência:

  | Pedido | Referência total / PT-BR |
  |---|---|
  | `movie/tt12042730` | 823 / 17 |
  | `series/tt0903747:1:1` | 531 / 9 |
  | `series/tt0944947:1:1` | 872 / 18 |
  | `movie/tt22084616` | 672 / 20 |

- PT-BR não pode cair. Tempo de série sem cache: até ~30 s.
- Confira a olho 10 títulos novos marcados PT-BR (sem falsos positivos).

### Documentação (só na etapa 3)
- **`HANDOFF.md`:**
  - Na tabela de componentes, corrija "~1 GB de RAM livre" para "~3,4 GB disponíveis".
  - Acrescente FlareSolverr (127.0.0.1:8191) e os novos indexadores.
  - Atualize a tabela de resultados.
- **`README.md`:** 1 linha na Seção 0.

## Resposta final (máx. 8 linhas)
Etapa feita, arquivos alterados, resultado de cada verificação.
