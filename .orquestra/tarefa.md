# Tarefa (rodada 3, FINAL): rejeitar release de anime que cita OUTRO arco

A rodada anterior estourou o tempo só explorando. **Tudo o que você precisa saber já está aqui. NÃO explore; implemente direto.** Tempo-alvo: 15 min.

## Contexto
- Comandos no A71: `.\scripts\a71.ps1 -Chroot '<cmd>'`. O Comet fica em `/opt/comet`; use `.venv/bin/python`.
- Reinício: `pkill -f "python -m comet.main"`. O watchdog religa em até 30 s.
- O estado atual já foi aprovado (patch idêntico a `comet-patches\ptbr-first.patch`). Mude APENAS o descrito abaixo.

## Dados (já verificados pelo orquestrador; não reverifique)
- `anime_mapper.get_kitsu_ids_from_imdb("tt9335498")` → `['41370','45249','44081','45866','47635','44063','45828']`.
- `anime_mapper.get_kitsu_episode_mapping(k)` → `{'imdb_id': 'tt9335498', 'from_season': N, 'from_episode': M}`. Para Demon Slayer:

  | kitsu | from_season | from_episode | arco |
  |---|---|---|---|
  | 41370 | 1 | 1 | principal |
  | 45249 | 2 | 1 | Mugen Ressha (TV) |
  | 44081 | 3 | 1 | Yuukaku |
  | 45866 | 4 | 1 | Katanakaji no Sato |
  | 47635 | 5 | 1 | Hashira Geiko |
  | 44063, 45828 | 0 | — | especiais |

- Títulos de cada entrada Kitsu:
  - `SELECT entry_id FROM anime_ids WHERE provider='kitsu' AND provider_id=:k` → `SELECT data_json FROM anime_entries WHERE id=:entry_id`.
  - `data_json` é JSON no formato anime-offline-database: use as chaves `title` (str) e `synonyms` (lista de str).
- One Piece `tt0388629`: só a kitsu `12` tem `from_season=1`; as demais são `from_season=0` (filmes/especiais).

## Implementação
### 1. Em `comet/services/anime.py` (classe `AnimeMapper`), adicionar:
```python
async def get_imdb_arc_titles(self, imdb_id: str) -> list[tuple[int, set[str]]]:
    """[(from_season, {títulos normalizados}), ...] para cada kitsu do IMDb; cache em dict na instância."""
```
- Normalização (`_norm_arc_title`, função de módulo):
  - NFKD, sem acentos, minúsculas;
  - `re.sub(r"[^a-z0-9]+", " ", s).strip()`;
  - devolve `f" {s} "` (com espaço nas pontas, para casar por palavra inteira);
  - descarte títulos normalizados com menos de 4 letras úteis.
- Erros ou dados faltando → retorne `[]`.

### 2. Função de módulo em `anime.py`:
```python
def release_cites_other_arc(release_title: str, arcs: list[tuple[int, set[str]]], requested_season: int) -> bool:
```
- Normalize `release_title` do mesmo jeito.
- Para cada `(season, titles)` em `arcs`, para cada título `t`: se `t in release_norm`, registre `(len(t), season)`.
- Pegue o maior `len`. Se não houver nenhum casamento → `False`.
- Entre os casamentos com esse comprimento máximo, se algum tem `season == requested_season` → `False`.
- Senão → `True` (o título mais específico pertence a outro arco ou a um especial).

### 3. Em `comet/services/media_search.py`
Onde hoje já se calcula `is_anime` / `absolute_episode` para pedido IMDb de episódio: se `is_anime`, calcule `arcs = await anime_mapper.get_imdb_arc_titles(media_only_id)` e passe ao `TorrentManager` (novo kwarg `anime_arcs=arcs`, padrão `None`).

### 4. Em `comet/services/orchestration.py` (`TorrentManager`)
- Guarde `self.anime_arcs`.
- No começo de `_matches_requested_scope`:
  - se `self.is_anime and self.anime_arcs and self.search_season is not None and not parsed.seasons and release_cites_other_arc(parsed.raw_title or "", self.anime_arcs, self.search_season)` → `return False`.
- Isso já cobre `scrape_torrents` e `_append_cache_file_infos`, que chamam `_matches_requested_scope`. Confirme os dois e não duplique.

Lógica esperada:
- **T1E1:** `Kimetsu no Yaiba - Hashira Geiko Hen - 01` casa com o título mais longo do arco T5 → rejeita.
- **T5E1:** `[SubsPlease] Kimetsu no Yaiba - 01` casa só com `kimetsu no yaiba` do arco T1 → rejeita, o que é correto (é o T1E01).
- **One Piece:** `One Piece - 1071` casa com `one piece` (kitsu 12, T1)… mas o pedido `21:181` tem `search_season=21`, então REJEITARIA.
  - Para evitar isso: **só aplique a regra se `arcs` tiver ≥ 2 entradas com `season ≥ 1` distintas.** O One Piece tem só 1 e fica fora.
  - Coloque essa checagem em `get_imdb_arc_titles`: retorne `[]` se houver menos de 2 temporadas ≥ 1 distintas.

## Validação (sem cache: antes de cada pedido, apague as linhas `torrents` do IMDb)
| Pedido | Exigência |
|---|---|
| `series/tt9335498:1:1` | NENHUM título com Hashira, Katanakaji, Yuukaku ou Mugen |
| `series/tt9335498:5:1` | traz `Hashira Geiko Hen - 01` |
| `series/tt9335498:3:1` | traz `Yuukaku Hen` e nenhum Hashira/Katanakaji |
| `series/tt0388629:21:181` | mantém `One Piece - 1071` (≈119 total) |
| `series/tt0388629:1:1` | total ≈ 336 |
| `series/tt0903747:1:1` | 9 PT-BR |
| `movie/tt12042730` | ≥ 13 PT-BR |

## Final
- Rode `py_compile` e reinicie o Comet.
- Regenere `comet-patches\ptbr-first.patch` com TODO o diff Python, excluindo `comet/templates/index.html`. Faça via `/data/local/tmp` + `adb pull`, em LF, e apague os temporários.
- Acrescente 1 linha no README (Seção 0) e no `HANDOFF.md` (Seção 7, item Anime).
- Não faça commit. Não altere mais nada.

## Resposta final (máx. 8 linhas)
Arquivos alterados, tabela da validação (total, PT-BR e se passou).
