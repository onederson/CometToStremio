# Tarefa N: "áudio PT confirmado" (lê as faixas de áudio do arquivo antes de prometer dublado)

## Contexto
- Comet no A71, chroot, `/opt/comet`. Hoje o `🇧🇷` vem só do **nome** do torrent/arquivo. Às vezes o nome diz "DUAL" e o arquivo não tem português, ou o `▶ Assistir` escolhe um "dublado" que abre em inglês.
- O `▶ Assistir` já tem o link do RD/TorBox pré-resolvido em background (`_preresolve_assistir_task` em `comet/api/endpoints/stream.py`; `get_preresolved_link` em `playback.py`). Com esse link dá para ler só o começo do arquivo com `Range`.
- Arquivos: novo `comet/services/audio_probe.py`, `comet/api/endpoints/stream.py`, `comet/core/models.py`, migração SQLite nova (como `pt_filenames`), `comet/api/endpoints/status.py`.
- **Não instale ffmpeg/ffprobe nem nada.** Python puro.
- **Comandos:** `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`. Scripts com aspas: arquivo local + `adb push` pelo **PowerShell** + `mv`. LF.
- **PROIBIDO:** imprimir chaves/tokens/URLs com token ou links do RD/TorBox; commit; instalar pacotes; mexer no AdGuard ou no `.env`. Nada em segundo plano. Comandos com timeout ≤ 300 s.

## 1. `audio_probe.py`
`async def probe_audio(url: str) -> list[dict] | None`: lê `Range: bytes=0-1048575` (se as Tracks não estiverem nesse trecho, mais 1 vez até 4 MB) com `User-Agent: ExoPlayerLib/2.19.1`, timeout 8 s.
- **MKV/WebM** (começa com `1A 45 DF A3`): parse EBML (IDs e tamanhos de tamanho variável; tamanho "desconhecido" no Segment/Cluster). Dentro de `Segment (18 53 80 67)` → `Tracks (16 54 AE 6B)` → cada `TrackEntry (AE)`: `TrackType (83)` = 2 é áudio; `Language (22 B5 9C)` (padrão `eng` se ausente), `LanguageBCP47 (22 B5 9D)`, `Name (53 6E)`, `CodecID (86)`. Pare ao achar um `Cluster (1F 43 B6 75)`. Use o `SeekHead` só se as Tracks não vierem antes do 1º Cluster (aí faça um Range na posição indicada, ≤ 64 KB).
- **MP4** (`ftyp` no byte 4): procure `moov` nos bytes lidos; se achar, percorra `trak` → `mdia` → `hdlr` = `soun` e `mdhd` (idioma ISO-639-2/T empacotado em 15 bits). Se o `moov` não estiver no começo, devolva `None`.
- Outro formato/erro → `None`.
- Retorno: `[{"lang": "por", "name": "Português", "codec": "A_AAC"}, ...]`. É português se `lang` em `por`/`pt`/`pob`/`pt-BR` (BCP47 começando com `pt`) **ou** `Name` contém `portugu`, `dublad`, `pt-br`, `brasil`.

## 2. Tabela `audio_probe(info_hash TEXT, file_key TEXT, langs TEXT, has_pt INT, probed_at INT, PRIMARY KEY(info_hash, file_key))`
`file_key` = índice/nome do arquivo (o mesmo que identifica o arquivo no playback). Guarde 60 dias.

## 3. Quando sondar (`stream.py`)
- Dentro do `_preresolve_assistir_task`, depois de obter o link do `▶ Assistir`: sonde (se não estiver na tabela) e grave.
- Em background, também os **2 seguintes** candidatos ⚡ com `🇧🇷` (mesma ordem de escolha do `▶ Assistir`), um por vez, só se `MemAvailable` ≥ 600 MB. Use o mesmo caminho de resolução de link que o pré-resolve usa (não duplique lógica).
- `models.py`: `AUDIO_PROBE: bool = True`.

## 4. Efeito na lista (layout `clean`)
- Se a tabela diz `has_pt=1` para o hash/arquivo: o nome ganha `🇧🇷✔` no lugar de `🇧🇷` e a descrição ganha a linha `🔊 <idiomas>` (ex.: `🔊 PT · EN`, siglas de 2 letras maiúsculas, no máx. 4).
- Se diz `has_pt=0` mas o nome dizia PT-BR: tira o `🇧🇷`, a linha vira `🔊 <idiomas> (sem português)`, e esse stream perde a prioridade de dublado (cai para o grupo dos não PT, mantendo resolução/tamanho).
- Escolha do `▶ Assistir`: entre os candidatos de hoje, prefira `has_pt=1`; **nunca** escolha um `has_pt=0` como dublado. Se o candidato escolhido pelo pré-resolve tiver `has_pt=0`, na próxima lista o `▶ Assistir` passa para o seguinte (sem isso travar a resposta atual).
- Sem dado na tabela: comportamento de hoje.
- Log: `🔊 áudio <hash curto>: <idiomas> (pt=<0|1>) em <t>s`.

## 5. `/status`
Seção **Áudio confirmado**: nº sondados, nº com PT, nº "dizia PT e não tinha", nº falhas de sonda (formato não suportado).

## Fora de escopo
Tudo o resto (rótulos fora do layout `clean`, fontes, legendas).

## Aplicar
`py_compile`; reinicie (polling `curl` no `manifest`); `git -C /opt/comet add -N` dos novos; regenere o patch (`git -C /opt/comet diff -- . ':!comet/templates/index.html' > /var/tmp/x.patch`; copie para `/data/local/tmp`, `chmod 644`, `adb pull` para `comet-patches/ptbr-first.patch`; zero `\r`; apague temporários).

## Verificação (link pessoal, sem imprimir URLs)
1. Unidade: monte em Python um MKV mínimo em bytes (EBML header + Segment com Tracks de 1 vídeo + 2 áudios `por` e `eng` + 1 Cluster) e um MP4 mínimo com `moov` (2 `trak` de som `por`/`eng`): `probe_audio` sobre um servidor HTTP local de teste (porta alta, só durante o script) devolve as duas faixas certas.
2. Real: peça a lista de Ben 10 Omniverse `tt2293002:1:2` e de um filme dublado (`tt12042730`); espere ≤ 60 s; mostre as linhas `🔊 áudio` do log e a tabela; peça a lista de novo e mostre os nomes/descrições dos 5 primeiros (com `🇧🇷✔`/`🔊`).
3. Caso "dizia PT e não tinha": se aparecer algum naturalmente, mostre; senão, insira uma linha `has_pt=0` de teste para um hash da lista, mostre que ele perdeu o `🇧🇷` e o `▶ Assistir` não é ele; apague a linha de teste.
4. `.\scripts\smoke.ps1` → `SMOKE OK`; `.\scripts\regress.ps1` → `REGRESS OK`.

Responda em no máximo 6 linhas: arquivos alterados e resultado da verificação.
