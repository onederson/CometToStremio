# Tarefa K: legenda PT-BR traduzida automaticamente quando só existe em inglês

## Contexto
- Comet no A71, chroot, `/opt/comet`. Arquivos: `comet/services/subtitles.py` (`search_subtitles`, `fetch_subtitle`, conversões), `comet/api/endpoints/subtitles.py` (rotas `/subs/...`), novo `comet/services/sub_translate.py`, `comet/core/models.py`.
- Hoje `search_subtitles` devolve só PT-BR (`lang: "pob"`) e variantes `sync-...`. Quando o título não tem nenhuma legenda PT-BR, o usuário fica sem nada. Quase sempre existe a inglesa (OpenSubtitles/SubSource/SubDL; o código já busca a inglesa como referência de sincronia: `cache_key_en`, `ref_candidates`).
- Arquivo PT-BR (dublado) continua devolvendo lista vazia: **não mude isso**.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv` para `/data/debian/var/tmp/`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com config ou token; imprimir respostas cruas do SubDL (a chave vem dentro do campo `url`); commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
1. `models.py`: `AUTO_TRANSLATE_SUBS: bool = True`, `AUTO_TRANSLATE_MAX_CHARS: int = 150000`.
2. Em `search_subtitles`: se o resultado final **não tem nenhuma PT-BR** (nem sync) e existe ao menos uma legenda inglesa para o mesmo `media_id` (busque a inglesa também quando não veio `filename`; reaproveite `_fetch_*` com o idioma inglês, como já é feito para a referência), acrescente **uma** entrada:
   `{"id": "auto-<provider>-<id>", "url": f"{base_url}/subs/auto/<provider>/<id>/<S>/<E>.srt", "lang": "pob"}`
   Escolha a inglesa com o mesmo score de release que já existe (a mais parecida com o `filename`). Log: `🤖 Legenda traduzida oferecida <media_id> (<provider>)`.
   E dispare em background (task guardada num set, como em `prefetch.py`) a tradução, para ela já estar pronta quando o usuário escolher.
3. Rota nova `GET /subs/auto/{provider}/{sub_id}/{season}/{episode}.srt` (mesmo arquivo de rotas e mesmo `content-type`/headers das outras `/subs/`): baixa a inglesa com `fetch_subtitle`, traduz e devolve SRT UTF-8. Cache em disco no mesmo `SUBS_CACHE_DIR` (`auto-<sha1>.srt`, sem expirar por 30 dias). Se dois pedidos chegarem juntos para a mesma legenda, traduza uma vez só (lock por chave).
4. `comet/services/sub_translate.py` (`async def translate_srt(srt_text: str) -> str | None`):
   - Parse do SRT em cues (índice, tempo, texto). Tempos e índices **intactos**.
   - Tradutor: `GET https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=pt&dt=t&q=<texto>` (sem chave; resposta `[[["trad","orig",...],...],...]`: junte os `[0]` de cada segmento). Use `curl_cffi` `AsyncSession` como o resto do arquivo.
   - Lotes: um cue por linha (quebras internas do cue viram espaço; tags `<i>`, `{\an8}` etc. removidas antes), até ~4500 caracteres por pedido, no máx. 3 pedidos ao mesmo tempo. Se a resposta voltar com número de linhas diferente do enviado, traduza aquele lote cue a cue (4 ao mesmo tempo).
   - Depois, quebre linhas com > 42 caracteres em 2 linhas no espaço mais perto do meio.
   - 429/erro/timeout (10 s por pedido): tente de novo 1 vez após 2 s; se falhar, devolva `None` (a rota responde 404) e `logger.warning` curto. Acima de `AUTO_TRANSLATE_MAX_CHARS`, não traduz.
   - Log: `🤖 Legenda traduzida: <n> falas em <t>s`.
   - Alimente os contadores do `/status` (`record_source_success("Tradutor")` / `record_source_error("Tradutor", ...)`, de `comet/core/logger.py`).

## Fora de escopo
Tudo o resto (fontes de legenda, sincronia, regra do arquivo PT, `index.html`).

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); `git -C /opt/comet add -N comet/services/sub_translate.py`; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token)
1. Unidade: `translate_srt` num SRT de 5 falas (2 com 2 linhas e uma com `<i>`) → 5 falas, tempos idênticos, texto em português (mostre o resultado).
2. Ache um título com inglesa e **sem** PT-BR (ex.: um episódio lançado nesta semana de série pouco popular, ou anime recente; mostre qual). O pedido de legendas dele traz a entrada `auto-...`; baixe-a: 200, nº de falas igual ao da inglesa, tempo da 1ª vez e da 2ª (cache, < 0,5 s).
3. Título com PT-BR (ex.: `tt0111161`): **não** aparece `auto-`. Arquivo PT (`...DUAL.PT-BR.mkv`): lista vazia.
4. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK` (a suíte existe; se algum WARN, diga qual).

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
