# Comet A71: o addon de Stremio da casa (Comet + Real-Debrid + TorBox, PT-BR primeiro)

*Início: 29/10/2026 · Última atualização: 02/11/2026, noite (horário de Brasília)*

> **🤖 Para outra IA continuar daqui:** leia **`HANDOFF.md`** inteiro antes de rodar qualquer comando (regras, segurança, histórico item a item na Seção 4, onde paramos na Seção 8). O modo de trabalho está em **`CLAUDE.md`** (desde 02/11/2026 o Claude implementa direto, sem delegar ao `agy`). O contexto da Fase 1 (rede, AdGuard, ADB) está resumido nas Seções 1 e 3 do `HANDOFF.md`.

---

## 1. O que é

Um servidor **Comet** (addon de Stremio) rodando 24 h num **Samsung Galaxy A71** com root, dentro de um Debian em chroot. Ele junta torrents de várias fontes, entrega pelo **Real-Debrid** e pelo **TorBox**, e coloca **dublado PT-BR em primeiro lugar**. Também monta uma tela inicial estilo Netflix, com TV ao vivo, legendas, avisos no Telegram e testes automáticos.

**Links (o token fica no `.env`; não versionar):**

| Uso | Endereço |
| :--- | :--- |
| Link pessoal (em casa **e no 4G**) | `https://a71comet.duckdns.org:7443/<PERSONAL_LINK_TOKEN>/manifest.json` |
| Link Kids | `https://a71comet.duckdns.org:7443/<KIDS_LINK_TOKEN>/manifest.json` |
| Página de status | `https://a71comet.duckdns.org:7443/<PERSONAL_LINK_TOKEN>/status` |
| Configurar (genérico) | `https://a71comet.duckdns.org:7443/configure` |
| Bot do Telegram | `@comet_a71_casa_bot` (só responde ao dono) |

> Desde 02/11/2026 o link usa a porta **7443** (a 443 externa do roteador é de outro PC). O link antigo sem porta ainda funciona **só em casa**.

---

## 2. O que ele faz (resumo)

**Fontes e reprodução**
- Torrentio, MediaFusion, 2 instâncias do Comet, Zilean, StremThru, Peerflix, SeaDex, Prowlarr (Catálogo BeTor + Knaben), BRSites (sites BR) e links diretos FenixFlix/FrostStream.
- Real-Debrid + **TorBox** (2º debrid): uma linha por torrent, RD ⚡ → TorBox ⚡ → baixar. O bloqueio 451 do RD cai automaticamente no TorBox.
- **`▶ Assistir`** no topo: a melhor opção (dublado pronto, 1080p, ≤ 30 GB) já pré-resolvida. **Fora de casa** (IP público/4G) prefere versão leve (≤ 4 GB, 720p antes de 4K).
- **Áudio PT confirmado:** lê as faixas de áudio de dentro do MKV/MP4 (`🇧🇷✔ 🔊 PT · EN`); quem diz "dublado" e não tem português perde o 🇧🇷.
- **Próximo episódio instantâneo:** ao abrir um episódio, o seguinte já é buscado. Se o dublado dele não estiver em cache, o debrid já começa a baixar (até 10 por dia).
- Fonte que falha 3 vezes seguidas é pausada sozinha (breaker); CAM vai para o fim; episódio não lançado mostra aviso.

**Tela inicial (65+ fileiras):** Top 10 com número, 🎲 Sorteio do dia, 📌 Minha lista, 🆕 Novos episódios, 🔔 Chegou dublado, 📅 Estreias da semana, 💡 Recomendados, 🔥 Em alta, 🆕 Lançamentos, 📺 Ao vivo agora, fileiras de mood (😭 chorar, 🤯 plot twist, ⚡ séries curtas, 😌 comédia leve, 👨‍👩‍👧 família, 🌙 suspense), 🏆 Vencedores do Oscar, ⭐ Mais bem avaliados, 📼 Clássicos dublados, originais por streaming, ⚡ Pronto dublado, 🎬 Sagas (abrem com todos os filmes), 🎌 Animes dublados, animes da temporada e TV ao vivo completa.
- **Capas montadas:** logo do título, selos grandes (NOVO EPISÓDIO, DUBLADO, TOP 10), logo do streaming (Netflix, Max, Prime…) e selo dourado **OSCAR**.
- **Tela inicial instantânea:** ao navegar, os 6 primeiros de cada fileira são aquecidos. Às 4h a "madrugada" aquece até 120 títulos.

**Página do título:** nome e sinopse em PT-BR, `⭐ IMDb · 🍅 Rotten · Ⓜ️ Metacritic · 🏆 Oscars` (OMDb), trailer dublado e legendado, fillers de anime marcados, "📺 Na temporada anterior" no episódio 1.

**Busca que entende português:** "anime do pirata que estica", "série de médicos", "filme do cara que acorda sempre no mesmo dia", "comédia anos 90 dublada", "filme com Tom Hanks dos anos 90" (bateria de 25 frases no teste automático, ~22 certas).

**Legendas:** OpenSubtitles + SubSource + SubDL, escolhidas pela release e sincronizadas; tradução automática para PT-BR quando só existe em inglês; legenda 🎓 PT+EN; nenhuma legenda quando o áudio já é PT.

**TV ao vivo grátis:**
- Pluto TV e canais abertos do iptv-org (Brasil + canais em português de outros países), revalidados a cada 12 h.
- Só aparecem os canais que funcionam, sem duplicatas.
- Português primeiro, com filtro `🇧🇷 Em português` / `🌎 Outros idiomas`.
- O "Ao vivo" é testado na hora do clique.

**📻 Rádios ao vivo:** cerca de 370 rádios brasileiras validadas (Radio Browser), com Recife e Pernambuco primeiro. Separadas por região e por tipo, com repasse pelo A71 para funcionar no 4G.

**Dublado de primeira:** quando o arquivo começa em inglês, o Comet ajusta o cabeçalho no caminho e o PT vira a faixa padrão, sem reencodar. **O Comet aprende** o que você assiste até o fim (`/gosto` no Telegram).

**Kids:** link próprio só com conteúdo infantil (inclui família, clássicos e canais infantis). A "hora de dormir" está pronta e **desligada** (`KIDS_BEDTIME=21:00-07:00` no `.env` liga).

**Bot do Telegram:** "Duna 2 dublado" → diz se está pronto ou manda baixar e avisa quando ficar ⚡. Também avisa se o teste automático falhar ou restaurar, se o RD/TorBox estiver vencendo e quando chega episódio dublado.

---

## 3. Arquitetura

| Peça | Onde | Observação |
| :--- | :--- | :--- |
| Galaxy A71 (root, crDroid) | `192.168.3.44` (IP fixo) | ADB Wi-Fi `192.168.3.44:5555` |
| Debian 13 arm64 (chroot) | `/data/debian` | `scripts/chroot.sh` |
| Comet (FastAPI, Python 3.13) | `/data/debian/opt/comet`, porta 8000 | modificado por `comet-patches/ptbr-first.patch` |
| Caddy (HTTPS Let's Encrypt via DNS-01 do DuckDNS) | `/etc/caddy/Caddyfile` (chroot) | 443 (casa), **7443** (casa + internet), 8443 (StremThru) |
| StremThru local | `127.0.0.1:8080` | ponte para Real-Debrid/TorBox |
| Prowlarr + FlareSolverr | `127.0.0.1:9696` / `:8191` | indexadores BR |
| AdGuard Home (Fase 1) | portas 53 e 3000 | DNS da casa (não mexer sem combinar) |
| Watchdog | `/data/comet/watchdog.sh` | religa tudo, protege memória, smoke a cada hora, DuckDNS a cada 10 min, sinal para o healthchecks.io a cada 5 min |
| Roteador Huawei WiFi BE3 | `192.168.3.1` | IP público; regra TCP/UDP 7443 → 192.168.3.44:7443 |

---

## 4. Operar

```powershell
.\scripts\a71.ps1 '<cmd>'            # comando como root no Android
.\scripts\a71.ps1 -Chroot '<cmd>'    # comando dentro do Debian
.\scripts\smoke.ps1                  # teste rápido (manifest, fileiras, streams, play, log)
.\scripts\regress.ps1                # suíte completa (~40 testes); -SaveBaseline grava a linha de base
.\scripts\deploy_patches.ps1         # reaplica o patch do Comet + smoke + regress
.\scripts\update_comet.ps1 -Check    # há versão nova do Comet original?
.\scripts\update_comet.ps1           # atualiza, testa e desfaz sozinho se algo quebrar
```

- Reiniciar o Comet: `.\scripts\a71.ps1 'pkill -f "python -m comet.main"'` (o watchdog religa em até 30 s).
- Logs: `/data/comet/comet.log`, `watchdog.log`, `caddy.log`, `stremthru.log`, `prowlarr.log`.
- Durante trabalho longo no Comet, crie `/data/debian/opt/comet/data/smoke.disable` (senão a restauração automática pode desfazer edições) e apague ao terminar.
- Mudou código no A71? Regere o patch: `git -C /opt/comet diff -- . ':!comet/templates/index.html' ':!comet/templates/index.html.orig'` → `comet-patches/ptbr-first.patch` (LF, sem `\r`).

**Segredos (nunca versionar nem imprimir):** `config/.env` (RD/TorBox, tokens dos links, Stremio, OMDb, Telegram, SubDL…) e `config/duckdns.token`. Ambos estão no `.gitignore`.

---

## 5. Checklist

- [x] Debian chroot, Comet, Caddy HTTPS, watchdog e boot automático
- [x] PT-BR primeiro, StremThru local, Prowlarr, FlareSolverr, BRSites, links diretos
- [x] Filtro/troca do 451, P2P de emergência, anime com numeração absoluta, CAM no fim
- [x] Legendas PT-BR (sincronia, tradução automática, PT+EN)
- [x] Tela inicial estilo Netflix, fileiras pessoais, sagas, Kids, capas montadas com selos
- [x] TorBox como 2º debrid, próximo episódio instantâneo, `/status`
- [x] Teste automático por hora (com restauração) e suíte de regressão no deploy
- [x] Madrugada, Chegou dublado, Estreias da semana, mood, Animes dublados, prestígio (Oscar/Top/Clássicos)
- [x] Áudio PT confirmado, pausa de fontes, pré-download no debrid
- [x] TV ao vivo (Pluto v4 + abertos), busca que entende português
- [x] Notas IMDb/Rotten/Metacritic + selo Oscar (OMDb)
- [x] Bot do Telegram com pedidos e avisos
- [x] Funciona fora de casa (4G) pela porta 7443
- [x] Salto geracional: capas vivas (pôster editorial, guia de TV, progresso, faixas HOJE/DUBLADO), 📅 Sua semana, 🍿 maratonas na ordem da história, 🎌 anime sem filler, qualidade real do arquivo (HDR/DV/bitrate/faixa padrão), atalhos 📱💎🎧, TorBox principal, compressão + uvloop, lista de desejos no Telegram
- [x] Usuário reinstalou com o link **:7443** e testou no 4G (02/11/2026): funcionou
- [ ] **Usuário (opcional):** reescrita no AdGuard `a71comet.duckdns.org` → `192.168.3.44` (deixa a casa um pouco mais rápida; não é obrigatória porque o roteador faz NAT loopback)
- [x] Vigia externo (healthchecks.io): avisa no Telegram se o A71 cair ou o Comet travar
- [x] TorBox assinado pelo usuário (02/11/2026)
- [ ] Achar mais addons de link direto (como FenixFlix/FrostStream) e somar em `DIRECT_ADDONS_URL`

---

## 6. Documentos

| Arquivo | Para quê |
| :--- | :--- |
| `HANDOFF.md` | Regras, arquitetura detalhada, histórico item a item (Seção 4), lacunas e onde paramos |
| `CLAUDE.md` | Modo de trabalho da IA |
| `MELHORIAS.md` | Lista priorizada de melhorias possíveis (com medições) e passo a passo do que depende do usuário |
| `COMO-CRIAR-BOT-TELEGRAM.md` | Passo a passo do bot (para leigos) |
| `como.md` | Como preencher o `/configure` (link genérico, sem token) |
| `.orquestra/tarefa-*.md` | Especificação de cada tarefa feita (registro) |
