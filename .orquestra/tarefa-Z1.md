# Tarefa Z1: tudo da tela inicial abre na hora (aquecimento ao navegar + madrugada maior)

## Problema
A 1ª busca de streams de um título leva 5–45 s (Prowlarr + fontes ao vivo); depois vem do cache (tabela `torrents`, e o pré-resolve do `▶ Assistir`). O usuário navega pelas fileiras da tela inicial e abre títulos que ainda não foram buscados.

## Contexto
- Comet no A71, chroot, `/opt/comet`. Catálogos: `comet/api/endpoints/catalog.py` + `comet/services/catalogs.py`. Madrugada: `comet/services/nightly.py` (`_build_work_list`, `NIGHTLY_MAX_ITEMS`, para se `MemAvailable` < 600 MB). Pré-busca: `comet/services/prefetch.py` (GET interno em `http://127.0.0.1:8000/<config>/stream/...`; pedidos internos não têm `X-Forwarded-For` e **não** disparam a pré-busca de próximo episódio em `stream.py`).
- Memória do A71 é limitada (5,5 GB, ~3 GB livres) e a CPU é de celular: o aquecimento tem que ser **lento e educado**.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF. O `grep` do Android não aceita `\|`: use `grep -E`.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token; commit; instalar pacotes; mexer no AdGuard ou no `.env`; mexer em `comet/services/prefetch.py` e no início da função `stream` de `stream.py` (outra pessoa está editando). Nada em segundo plano (seus comandos): rode em primeiro plano e espere. Comandos com timeout ≤ 300 s.

## Comportamento
1. Novo `comet/services/row_warm.py`: fila única de aquecimento, **1 por vez**, pausa de 2 s entre itens, pula se `MemAvailable` < 700 MB, não aquece o que já está em cache (consulta barata: existe linha na `torrents` para o `media_id` atualizado há < 3 dias → pula), dedupe por 6 h (memória).
   - Filmes: `stream/movie/<tt>`. Séries: o episódio que faz sentido abrir: se a série está no histórico do Stremio, o próximo não assistido (reuse a lógica da madrugada); senão `S1E1`; para `🆕 Novos episódios`/`📅 Estreias da semana`/`🔔 Chegou dublado`, o episódio citado no item. Sagas (`cometsaga:`): o 1º filme. TV ao vivo: nada.
   - GET interno em `http://127.0.0.1:8000/<mesmo prefixo do pedido do catálogo>/stream/...` (sem `X-Forwarded-For`), timeout 90 s.
2. **Ao navegar:** quando um catálogo é pedido **de fora** (tem `X-Forwarded-For`) com link pessoal ou Kids, enfileire os **6 primeiros** itens dele (respeitando `skip`: se o app pediu a página 2, os 6 primeiros dela). Prioridade: fileiras pedidas mais recentemente primeiro (fila LIFO por fileira, máx. 60 itens na fila; o resto é descartado).
3. **Madrugada:** `NIGHTLY_MAX_ITEMS` → 120 e a lista de trabalho ganha, depois do que já existe, os 8 primeiros itens de cada fileira principal do link pessoal (Top 10, Em alta, Lançamentos, Sorteio, mood, Animes dublados, Estreias da semana), sem repetidos.
4. `models.py`: `ROW_WARM: bool = True`, `ROW_WARM_PER_ROW: int = 6`.
5. `/status`: seção **Aquecimento**: itens na fila, aquecidos hoje, pulados (já em cache / memória baixa), tempo médio.

## Fora de escopo
Tudo o resto.

## Aplicar
`py_compile`; reinicie (`.\scripts\a71.ps1 'pkill -f "python -m comet.main"'`, polling `curl` no `manifest`); `git -C /opt/comet add -N comet/services/row_warm.py`; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (sem imprimir URL/token)
1. Peça pelo endereço **público** (`https://a71comet.duckdns.org/<token>/catalog/movie/comet_mood_twist.json`, que passa pelo Caddy) e mostre no log os aquecimentos (`🔥 aquecido <tt>: <n> streams em <t>s` ou similar) dos 6 primeiros.
2. Depois, a lista de streams de 3 desses itens vem em ≤ 2 s.
3. Pedido **interno** (127.0.0.1) do mesmo catálogo não enfileira nada.
4. `MemAvailable` e RSS do Comet durante o aquecimento (antes/pico/depois).
5. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK` (em primeiro plano, espere).

Responda em no máximo 8 linhas.
