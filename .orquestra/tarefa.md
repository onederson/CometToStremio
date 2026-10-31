# Tarefa: links diretos de outros addons dentro da resposta do Comet (`DIRECT_ADDONS_URL`)

Objetivo: o usuário quer **um addon só**. Hoje ele precisa instalar FenixFlix e FrostStream à parte, porque eles servem vídeo HTTP direto (sem torrent/RD, então o bloqueio 451 do RD não se aplica). O Comet passa a buscar os streams desses addons **ao vivo, em paralelo com a busca normal**, e a mesclá-los na própria lista.

Addons (padrão Stremio, `GET <base>/stream/<movie|series>/<id>.json` → `{"streams":[...]}`):
- `https://fenixflix.fenixhub.online`
- `https://froststream.cloutteam.com`

Os streams úteis têm `url` (HTTP) e podem ter `behaviorHints` com `proxyHeaders`, `notWebReady`, `filename`, `videoSize`. Os links podem expirar: **não** guardar no banco.

## Contexto
- Código do Comet: A71, chroot, `/opt/comet` (Android: `/data/debian/opt/comet`). Edite lá.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` (Android root) e `.\scripts\a71.ps1 -Chroot '<cmd>'` (Debian; `git` só existe aqui).
- Enviar arquivo: `adb -s 192.168.3.44:5555 push <arq> /data/local/tmp/<nome>` (um por vez, nome completo), depois mova. Tudo em **LF**.
- **PROIBIDO:** imprimir chaves (a do RD aparece nas URLs do `comet.log`; não mostre essas linhas), commit, mexer no AdGuard. **NÃO rode tarefas em segundo plano.** Divida o trabalho em passos curtos.

## O que fazer

### 1. Configuração (`comet/core/models.py`)
- `DIRECT_ADDONS_URL: str | list[str] = []` e `DIRECT_ADDONS_TIMEOUT: float = 8.0`, perto de `ADDONS_URL`.
- Aceitar string única ou lista JSON, do mesmo jeito que `ADDONS_URL` (veja a linha ~670 onde `"ADDONS_URL"` aparece numa lista de campos normalizados; acrescente `"DIRECT_ADDONS_URL"` lá).
- `config/.env` (PC) **e** `/data/debian/opt/comet/.env` (A71), em LF, iguais (MD5), `chmod 600` no A71:
  ```
  DIRECT_ADDONS_URL=["https://fenixflix.fenixhub.online","https://froststream.cloutteam.com"]
  ```

### 2. Novo módulo `comet/services/direct_addons.py`
`async def fetch_direct_streams(media_type: str, media_id: str) -> list[dict]`
- Para cada URL de `settings.DIRECT_ADDONS_URL` (sem `/` final), em paralelo (`asyncio.gather`), `GET {base}/stream/{media_type}/{media_id}.json` com `curl_cffi.requests.AsyncSession(impersonate="chrome")`, timeout `settings.DIRECT_ADDONS_TIMEOUT`. Erro ou timeout de um addon → lista vazia para ele + `logger.warning` curto (sem stack trace). Nunca levanta exceção.
- Cache em memória (dict de módulo) por `(media_type, media_id)` por **10 min**; não cachear resultado vazio. Limite simples de 500 entradas (apaga as mais antigas).
- Manter só streams com `url` começando com `http`. Ignorar os que têm só `infoHash`, `externalUrl` ou `ytId`.
- Nome curto do addon: `FenixFlix` para host com `fenixflix`, `FrostStream` para `froststream`, senão o 1º rótulo do host com a inicial maiúscula.
- Converter cada stream:
  - `texto` = `name` + `\n` + (`title` ou `description`) do stream original.
  - `is_pt` = `texto` (minúsculo) contém algum de: `dublado`, `dual`, `pt-br`, `ptbr`, `português`, `portugues`, `nacional`, `🇧🇷`.
  - `res` = 1ª ocorrência em `texto` de `2160p`/`4k` (→ `4K`), `1080p`, `720p`, `480p`; senão vazio.
  - `name` novo = (`"🇧🇷 PT-BR\n"` se `is_pt`) + `f"🌐 {curto}"` + (`f"\n{res}"` se `res`).
  - `description` novo = o `title`/`description` original (máx. 6 linhas) + `f"\n🌐 Link direto ({curto}): não usa o Real-Debrid"`.
  - `url`: o original.
  - `behaviorHints`: copie o original (se houver) e defina `bingeGroup = f"comet|direct|{curto}|{res}"`.
  - Remova qualquer outra chave. Guarde `is_pt` e `res` num atributo à parte (ex.: devolva tuplas `(stream, is_pt, res_rank)` com `res_rank` 0=4K, 1=1080p, 2=720p, 3=480p, 4=vazio) — escolha o formato que facilitar o passo 3.
- Ordem de saída: PT antes de não-PT, depois por `res_rank`, mantendo a ordem original no empate.

### 3. Mesclar em `comet/api/endpoints/stream.py`, função `stream()`
- Se `settings.DIRECT_ADDONS_URL` não estiver vazio: crie a tarefa **antes** de `search_media(...)`: `direct_task = asyncio.create_task(fetch_direct_streams(media_type, media_id))`. Assim corre em paralelo com o scraping.
- Função auxiliar para aguardar: `await asyncio.wait_for(direct_task, settings.DIRECT_ADDONS_TIMEOUT + 2)`, qualquer erro → `[]`. Se a função retornar cedo por `INVALID`, cancele a tarefa.
- **Retornos antecipados** `UNRELEASED`, `METADATA_UNAVAILABLE` e `BUSY`: se houver streams diretos, devolva o aviso **mais** os diretos (`is_empty=False` nesse caso).
- **Retorno final** (onde se monta `final_streams`): insira os diretos assim, nos 3 ramos que hoje montam `final_streams` com `notice_streams` (DEMOTE_CAM+PTBR_FIRST, DEMOTE_CAM sem PTBR_FIRST, PTBR_FIRST sem DEMOTE_CAM; e também o `else` final):
  - Separe as entradas PT boas (`pt_good` / `pt_entries`) em **com RD** (`"url" in entry[0]`) e **P2P** (sem `url`, são as bloqueadas no RD com `infoHash`).
  - Ordem: `notice_streams` → PT boas com RD → **diretos PT** → PT boas P2P → outras boas → **diretos não-PT** → CAM (PT, depois outras).
  - Nos ramos sem PTBR_FIRST: `notice_streams` → diretos PT → resto como hoje → diretos não-PT antes dos CAM (se houver separação de CAM) ou no fim.
- Não mude mais nada da ordenação, do precheck, do 451, dos scrapers.

### 4. Aplicar
1. `py_compile` dos arquivos alterados.
2. Reinicie o Comet: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`; espere o `manifest.json` voltar (loop de polling, sem `Start-Sleep`).
3. Regenere o patch: no chroot `git -C /opt/comet add -N comet/services/direct_addons.py` e `git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp/x.patch`, `adb pull` para `comet-patches/ptbr-first.patch`, apague temporários com `unlink`. Zero `\r`.

## Fora do escopo
Qualquer outra mudança (scrapers, Prowlarr, watchdog, UI, README/HANDOFF).

## Verificação
Crie `/var/tmp/vd.py` (apague no fim) que chama `http://127.0.0.1:8000/<cfg>/stream/<tipo>/<id>.json` com `cfg` = base64 de `{"debridServices": [], "enableTorrent": true, "cachedOnly": false, "removeTrash": true, "maxResultsPerResolution": 0}` e imprime: total, nº de streams com `🌐`, posição do 1º `🌐`, tempo, e as 5 primeiras linhas `name` (1 linha cada, `\n`→` | `). Rode com o Python do venv no chroot:
```
.\scripts\a71.ps1 -Chroot '/opt/comet/.venv/bin/python /var/tmp/vd.py series/tt2293002:1:2 series/tt9335498:1:1 movie/tt12042730 series/tt0388629:21:181'
```
Esperado:
- `tt2293002:1:2` (Ben 10 Omniverse) e `tt12042730` (Devoradores de Estrelas): streams `🌐` presentes, com `🇧🇷 PT-BR` nos dublados.
- Tempo não piora mais que ~2 s em relação a uma chamada com `DIRECT_ADDONS_URL` vazio.
- Pegue 1 `url` de stream `🌐` e faça `GET` com `Range: bytes=0-1023` (usando os `proxyHeaders.request` se houver): status 200/206.
- `grep -a "direct" /data/comet/comet.log | tail -5`: sem erro em loop.

Responda em no máximo 5 linhas: arquivos alterados e os números.
