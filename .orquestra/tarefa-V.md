# Tarefa V: canais do Pluto TV que tocam no aparelho (3 links por canal) + limpar canais abertos quebrados

## Problema
O usuário diz que **vários canais do Pluto não tocam** no Stremio (sobretudo na TV). Do A71, a cadeia master → variante → segmento funciona nos 25 testados, e o DNS da casa resolve todos os hosts do Pluto. O link hoje é o formato antigo `…/stitch/hls/channel/<id>/master.m3u8?<query v1>` (`generate_pluto_stream_url` em `comet/services/live_tv.py`). Os apps atuais do Pluto usam sessão do `boot.pluto.tv/v4/start` com JWT.
Canais abertos com problema: "+MaisUm" (404) e "Amazon Sat" (URL com bytes de controle: parse do M3U quebrado).

## Contexto
- Comet no A71, chroot, `/opt/comet`. Arquivo principal: `comet/services/live_tv.py` (`get_live_tv_stream`, `generate_pluto_stream_url`, validação do iptv-org, `iptv_alive.json`). Teste: `scripts/regress.py` (teste `livetv`).
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token, nem o JWT do Pluto; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## Comportamento
1. **Sessão Pluto v4:** `GET https://boot.pluto.tv/v4/start?appName=web&appVersion=9.0.0&deviceVersion=122.0.0&deviceModel=web&deviceMake=chrome&deviceType=web&clientID=<deviceId fixo de data/pluto_device_id>&clientModelNumber=1.0.0&serverSideAds=false` → `sessionToken`, `stitcherParams`, `servers.stitcher`, `refreshInSec`. Cache em memória até `refreshInSec − 300` s; erro → usa o cache antigo se houver.
2. **Três streams por canal Pluto**, nesta ordem:
   - `📺 Ao vivo` → `<servers.stitcher>/v2/stitch/hls/channel/<id>/master.m3u8?<stitcherParams>&jwt=<sessionToken>&masterJWTPassthrough=true`, `notWebReady: false`;
   - `📺 Ao vivo · opção 2` → `https://jmp2.uk/plu-<id>.m3u8`, `notWebReady: false`;
   - `📺 Ao vivo · opção 3` → o link v1 de hoje, `notWebReady: true`.
   `description` de cada um: `<canal> · Pluto TV` + `\nSe não abrir, tente a próxima opção`. Se a sessão v4 falhar, o 1º some e os outros continuam.
3. **Canais abertos:** no parse do M3U, descarte URL com caractere de controle ou que não seja `http(s)://` válida; na validação diária, além de `#EXTM3U` no master, baixe a 1ª variante e confirme que há segmento (mesma cadeia do item 4); 404/sem segmento = fora da lista.
4. Função `check_channel_chain(url) -> (ok, motivo)` (master → 1ª variante → 3º segmento, `User-Agent: ExoPlayerLib/2.19.1`, 4 KB do segmento), usada pela validação e pelo teste.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URL/token/JWT)
1. Para 25 canais Pluto do catálogo: cada uma das 3 opções passa por `check_channel_chain`? Mostre uma tabela `canal | v4 | jmp2 | v1`.
2. Canais abertos depois da revalidação: quantos ficaram; "+MaisUm" e "Amazon Sat" fora (ou consertados).
3. `scripts/regress.py`, teste `livetv`: 5 canais Pluto aleatórios com a opção 1 passando na cadeia completa (FAIL se < 4). `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK` (em primeiro plano, espere terminar).

Responda em no máximo 8 linhas: arquivos alterados e a tabela resumida (quantos ok por opção).
