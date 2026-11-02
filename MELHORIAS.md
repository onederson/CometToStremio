# Melhorias possíveis para o Comet A71

*Levantamento de 02/11/2026. Os números da Parte 1 foram medidos pelo endereço público (`:7443`), do jeito que o app do Stremio enxerga o addon.*

Legenda:
- **Impacto:** 🔥🔥🔥 muda o dia a dia · 🔥🔥 bom ganho · 🔥 detalhe.
- **Esforço:** quanto trabalho dá para mim. Nenhum item exige gastar dinheiro.
- ✋ marca o que depende de você.

O documento tem duas partes:
- **★ O salto para o perfeito:** as melhorias que mudam a experiência de verdade, cada uma baseada em algo que medi ou vi acontecer no seu A71.
- **Partes 0 a 8:** a base (rapidez, interface, bot, segurança), que também vale fazer.

---

## ★★ O salto geracional (12 ideias que nenhum addon tem)

A grande sacada: **no Stremio, a interface do addon são as imagens.** Capas, fundo da página do título, miniatura de episódio e logo de canal são desenhados pelo próprio Comet no A71. Ou seja, dá para pôr **informação viva** dentro deles: progresso, dublagem, notas, horário. As ideias marcadas com 🎨 mudam o visual.

| # | Ideia | Como fica para você |
|---|---|---|
| 1 🎨 | **Capas vivas** | A capa muda com o seu momento: **barra vermelha de progresso** ("faltam 23 min") no que você começou, "T2E5 sai HOJE", contagem "Estreia em 3 dias", "🇧🇷 Dublado chegou", nota IMDb. Tudo desenhado na hora a partir do seu histórico do Stremio |
| 2 🎨 | **Página do título cinematográfica** | O fundo da página vira um **pôster editorial** em tela cheia: logo grande, notas (IMDb/Rotten/Oscar), "🇧🇷 dublado pronto em 4K", tira com as fotos do elenco, duração e "termina às 22:41" |
| 3 🎨 | **Episódios que contam tudo** | Cada miniatura de episódio ganha selos: `🇧🇷 DUB`, `✓ visto`, `🟡 FILLER`, `★ 9,4` (nota do episódio), `FINAL DE TEMPORADA`. Você vê de longe qual episódio é imperdível |
| 4 🎨 | **Lista de fontes com curadoria** | No topo, 4 botões claros em vez de 100 linhas: `▶ Melhor dublado` · `📱 Leve (celular/4G)` · `💎 Máxima qualidade (4K HDR/Atmos)` · `🎧 Original legendado`. Abaixo, o resto, já sem as mentiras |
| 5 | **Qualidade de verdade (abrir o arquivo)** | O Comet lê o cabeçalho de cada arquivo: codec, HDR/Dolby Vision, bitrate real, faixas de áudio. Mostra `4K REAL · HDR10 · 22 Mbps` ou `⚠ 4K falso (upscale)`, avisa `DV perfil 5: cores erradas na sua TV` e `Som TrueHD: sua TV pode ficar muda` |
| 6 | **Dublado de primeira, sempre** | Prefere arquivo com o PT como faixa padrão. Experimental: o Comet **corrige o arquivo no caminho** (PT vira padrão; som DTS/TrueHD vira um formato que a TV toca) |
| 7 🎨 | **Ordens de maratona** | Itens novos que são uma "série" montada: **Universo Marvel em ordem cronológica**, **Star Wars na ordem da história**, **Velozes em ordem cronológica**, com capa desenhada e cada filme como episódio. Clicou, maratona na ordem certa, com progresso |
| 8 🎨 | **Anime sem filler** | Ao lado de "One Piece" aparece **"One Piece · só a história"**: a lista de episódios pulando os fillers, na ordem certa. Vale para Naruto, Bleach e o que tiver lista de filler |
| 9 🎨 | **TV ao vivo com guia na capa** | A capa de cada canal mostra **o que está passando agora** (título + barra de progresso do programa) e o que vem depois, atualizada a cada 15 min. A fileira vira um guia de TV |
| 10 🎨 | **Sua semana em cartões** | Fileira "📅 Sua semana" com um **cartão por dia** (desenho do Comet): "Quarta: The Boys T5E3 🇧🇷 · Pinguim T2E1". Clicou, abre o do dia |
| 11 | **Lista de desejos + radar** (Telegram) | "Me avisa quando sair Duna 3 dublado" → baixa e avisa sozinho. Filme saiu do cinema e chegou dublado (sem CAM) → aviso |
| 12 | **O Comet que aprende** | O que você assiste até o fim fortalece aquele tipo de release; o que abandona enfraquece. As fileiras se reordenam pelo seu uso. "Para hoje à noite" escolhe pelo dia e pela hora |

**Já em andamento (02/11/2026, noite):**
- **5 (qualidade de verdade):** leitor completo de MKV/MP4, feito por um subagente.
- **11 (lista de desejos + radar):** feito por outro subagente.
- **Base:** play garantido, TorBox principal, `uvloop` e compressão, comigo.

Depois: **4 → 1 → 3 → 7 → 8 → 9 → 2 → 10 → 6 → 12**.

---

## ★ O salto para o perfeito

### O que as medições mostraram (02/11/2026, à noite)
| Medição | Resultado |
|---|---|
| Velocidade do **TorBox** até a sua casa | começa a tocar em **0,5 s** e entrega **130–146 Mbit/s** (folga até para 4K HDR) |
| **"⚡ Real-Debrid"** de Interestelar 4K e Breaking Bad 4K | **não tocou**: o RD bloqueou na hora do play (451, direito autoral), o Comet tentou outra opção, e o primeiro byte chegou em **3 a 15 s** |
| Checagem de áudio dos candidatos | **já tinha descoberto** esse bloqueio antes (`infringing_file`), mas **não guardou** (bug) |
| Lista de Interestelar | 1.489 fontes, 878 KB, nada compactado |
| Motor de rede do Comet | Python puro, **sem `uvloop`** (o motor rápido) |

### 1. "⚡ pronto" tem que significar "toca na hora" 🔥🔥🔥
Hoje **⚡** quer dizer "o arquivo está no cache do debrid", mas não garante que o RD vá liberar. A BLUDV, que tem quase todo o 4K dublado, é muito bloqueada pelo RD.
- **Verificação ativa:** quando você abre um título, o Comet testa em segundo plano as 5 melhores opções de verdade (pede o link e lê o 1º pedaço do vídeo). Bloqueada vai para o TorBox ou some; lenta perde posição.
- **Corrigir o bug:** todo `infringing_file` descoberto, em qualquer caminho, entra na lista de bloqueados na hora.
- **Resultado:** o `▶ Assistir` e os ⚡ do topo **sempre começam em ~1 s**, sem "trocando de fonte…".

### 2. TorBox como serviço principal, RD como reserva 🔥🔥🔥
Com o TorBox assinado e medido (0,5 s; 130+ Mbit/s; muito menos bloqueios em dublado), inverter a prioridade: **TorBox ⚡ → RD ⚡ → baixar**.
- **Bônus de segurança:** o RD só permite **um IP por vez**. Assistir em casa e no 4G ao mesmo tempo pelo RD pode gerar alerta ou bloqueio da conta. Fora de casa, o Comet passa a usar **só o TorBox**.

### 3. Dublado "de primeira", sem trocar a faixa de áudio 🔥🔥🔥
Muitos arquivos DUAL trazem o **inglês como 1ª faixa**, e o player começa em inglês. A checagem de áudio já lê a ordem das faixas.
- O `▶ Assistir` passa a preferir arquivos em que o **português é a faixa padrão**. Empate → o de PT em 2º perde pouco, mas perde.
- A lista mostra `🔊 PT primeiro` ou `🔊 EN · PT` para você saber antes de dar play.
- ✋ **Ajuste no app (1 min, em cada aparelho):** Stremio → **Configurações → Player → Idioma de áudio preferido: Português**. Assim o player escolhe o PT sozinho mesmo quando não é a 1ª faixa.

### 4. Áudio confirmado em toda a lista, não só no topo 🔥🔥
Hoje só o `▶ Assistir` e 2 candidatos têm o áudio lido. Uma fila em segundo plano vai sondando, aos poucos, todas as opções 🇧🇷 dos títulos que você abre e dos aquecidos pela madrugada. Com o tempo, quase tudo vira `🇧🇷✔` ou perde o 🇧🇷 falso.
- **Dublagem por IA / redublagem:** releases marcadas com "IA", "AI dub" ou "redublagem" ganham o rótulo `🤖 Dublagem IA` e vão para o fim dos dublados.

### 5. Maratona perfeita: a temporada inteira do mesmo arquivo 🔥🔥🔥
Quando você dá play num episódio que veio de um **pacote da temporada**, os próximos episódios desse pacote já estão na conta do debrid: tocam na hora e com a **mesma dublagem, o mesmo volume e a mesma qualidade**.
- O `▶ Assistir` dos episódios seguintes prefere o pacote que você já começou.
- Os pacotes "já na sua conta" aparecem com `📦 Na sua conta`.

### 6. O Comet aprende o seu gosto 🔥🔥🔥
O Comet sabe o que você toca, e o Stremio sabe até onde você assistiu.
- **Ranking que aprende:** a release que você assistiu até o fim ganha pontos para o grupo dela (BLUDV, PiA…). A que você abandonou em menos de 2 min perde. Com o tempo, o `▶ Assistir` acerta de primeira com mais frequência.
- **Fileiras que se organizam:** as fileiras que você abre sobem e as que você ignora descem, sem precisar configurar nada.
- **"Para hoje à noite":** em dia de semana, sugestões mais curtas e séries que você está vendo; no fim de semana, filmes longos e sagas.

### 7. Página do título que leva a outros títulos 🔥🔥
O protocolo do Stremio permite "botões" (links) na página do título. Hoje quase não usamos isso.
- `🔎 Mais como este` abre uma fileira com títulos parecidos (TMDB, com os dublados primeiro).
- `🎬 Da mesma saga` · `🎥 Do mesmo diretor` · `👤 <ator principal>`
- Em séries: `🇧🇷 Dublado: T1–T3 · T4 legendado`, e o 🇧🇷 em cada episódio que já tem dublado pronto.

### 8. Pedir pelo Telegram e esquecer 🔥🔥🔥
- **Lista de desejos:** "me avisa quando sair Duna 3 dublado". A madrugada confere todo dia; quando aparecer dublado, baixa e avisa: "⚡ Duna 3 dublado pronto". Vale também para "quando sair o episódio dublado de X".
- **Radar de lançamentos:** filmes que saíram do cinema avisam quando chegam dublados em boa qualidade (sem CAM).
- **Botões na resposta:** "▶ Abrir no Stremio", "Outra versão", "Baixar a temporada inteira".

### 9. Motor mais rápido no A71 🔥🔥
- **`uvloop`:** o motor de rede rápido do Python; costuma dar de 2 a 4× mais vazão em servidores como o Comet, sem mudar nada no resto.
- **Busca progressiva:** responde com as fontes que já chegaram e completa o resto em segundo plano (a 1ª busca cai de 5–45 s para ~5–8 s).
- **Cache do debrid seletivo:** consulta primeiro os ~300 melhores torrents, e não os 1.000+.
- **Previsão de uso:** pelo seu histórico (séries que você vê toda noite, horário em que costuma assistir), o Comet aquece **antes** os próximos episódios prováveis.

### 10. Nunca ficar sem Comet 🔥🔥
- **Backup diário criptografado** (banco, `.env`, patch) mandado pelo bot só para você. Se o A71 morrer, outro celular volta ao ar a partir do backup.
- **Saúde do A71:** temperatura, bateria e espaço no `/status`, com aviso no Telegram. Se esquentar, um modo economia diminui o aquecimento até baixar.
- **Proteção da porta pública:** limite de pedidos por IP e bloqueio de robôs que varrem a internet.

### Ordem que eu proponho
1. **Itens 1, 2 e 9** (`uvloop` + compressão + limite de fontes): play que sempre começa e app mais leve. São o maior ganho imediato.
2. **Itens 3 e 5:** dublado de primeira e maratona perfeita.
3. **Itens 4 e 7:** áudio confirmado em tudo e página do título com links.
4. **Itens 6 e 8:** o Comet que aprende e a lista de desejos no Telegram.
5. **Item 10:** backup e saúde do A71.

---

## 0. A base: as 6 primeiras que eu faria (maior ganho por menor esforço)

| # | Melhoria | Por quê | Ganho esperado |
|---|---|---|---|
| 1 | **Compactar as respostas** (gzip/zstd no Caddy) | Hoje nada vai comprimido: a tela inicial baixa 1,47 MB, e a lista de fontes de um filme passa de 800 KB | **~80 a 90 % menos dados.** No 4G a tela inicial e as listas chegam bem mais rápido |
| 2 | **Enxugar a lista de fontes** | Interestelar devolve **1.489 fontes**; a TV precisa ler e desenhar tudo | Manter as ~120 melhores (todas as dubladas + as melhores de cada resolução) → lista **5 a 10× menor** e abrindo na hora |
| 3 | **Tela inicial mais leve** | O app pede **65 fileiras** ao abrir | Escolher as ~25 que você usa (o resto vai para o Descobrir) → abre mais rápido e fica menos poluída |
| 4 | **Capas prontas antes de você ver** | A capa montada leva 1 a 1,5 s na 1ª vez (o A71 desenha na hora) | A madrugada já desenha as capas das fileiras principais → **capas instantâneas** |
| 5 | **1ª busca de um título mais rápida** | Hoje 5 a 45 s; os vilões são o Prowlarr (~16 s) e a consulta de cache no debrid de **1.000+ torrents** (~20 s) | Responder com as fontes rápidas e completar o resto em segundo plano; consultar o cache só dos ~300 melhores → **~5 a 8 s** na 1ª vez |
| 6 | ~~Vigia externo~~ ✅ **feito em 02/11/2026** | O A71 não consegue avisar quando ele mesmo cai | Aviso no Telegram em até 10 min se o A71 sumir |

---

## 1. Rapidez e conexão

| Melhoria | Detalhe | Impacto | Esforço |
|---|---|---|---|
| **Compressão gzip/zstd** | `encode zstd gzip` no Caddy (portas 443 e 7443) | 🔥🔥🔥 | Baixo |
| **Limite de fontes por lista** | Teto de ~120 fontes, sempre com todas as 🇧🇷 e as melhores de cada resolução; descartar duplicatas do mesmo arquivo (mesmo nome + tamanho) | 🔥🔥🔥 | Baixo |
| **Resposta rápida + completa depois** | Na 1ª busca, responder em até ~6 s com as fontes que já chegaram; as lentas (Prowlarr, BRSites) completam o cache para a próxima abertura | 🔥🔥🔥 | Médio |
| **Cache do debrid só no que importa** | Hoje consulta RD e TorBox para todos os 1.000+ torrents; consultar primeiro os ~300 melhores (e os PT-BR) e o resto depois | 🔥🔥 | Médio |
| **Capas em WebP** | Mesma qualidade com ~30 % menos peso que JPEG (o app Android lê WebP) | 🔥🔥 | Baixo |
| **Capas pré-desenhadas na madrugada** | Desenhar as capas das ~25 fileiras principais às 4h | 🔥🔥 | Baixo |
| **Cache mais esperto das fileiras** | `stale-while-revalidate`: o app recebe na hora a versão guardada, e o Comet atualiza por trás | 🔥🔥 | Baixo |
| **Ficha do addon (manifest) com cache** | Hoje vai sem `Cache-Control`; dá para guardar por 1 h | 🔥 | Baixo |
| **HTTP/3 também no 4G** ✋ | Se a regra 7443 do roteador estiver só em TCP, mudar para **TCP/UDP** (o HTTP/3 vai por UDP e conecta mais rápido em rede móvel) | 🔥 | Seu: 1 min |
| **Respostas JSON mais rápidas** | Gerar o JSON com `orjson` (mais leve no processador do A71) | 🔥 | Baixo |
| **Banco SQLite em dia** | `VACUUM` e `ANALYZE` semanais na madrugada, para as consultas não ficarem lentas com o tempo | 🔥 | Baixo |

## 2. Interface (o que você vê no Stremio)

| Melhoria | Detalhe | Impacto | Esforço |
|---|---|---|---|
| **Página "Minhas fileiras"** | Uma página no próprio Comet (protegida pelo token) com uma lista para marcar quais fileiras aparecem e em que ordem; as fileiras que você nunca abre descem sozinhas | 🔥🔥🔥 | Médio |
| **Dublagem por episódio** | Na lista de episódios de uma série, marcar `🇧🇷` nos episódios com dublado pronto | 🔥🔥🔥 | Médio |
| **Resumo de dublagem na série** | Na descrição: "🇧🇷 Dublado: T1–T3 · T4 só legendado" | 🔥🔥 | Médio |
| **Lista de fontes mais limpa** | Separadores visuais por grupo ("── Dublados ──", "── 4K ──"), nomes mais curtos e "começa em ~2 s" nas que estão em cache | 🔥🔥 | Baixo |
| **"Porque você assistiu X"** | Fileiras de recomendação com o nome do título que as originou | 🔥🔥 | Baixo |
| **Elenco clicável** | Na página do título, clicar no ator abre a busca com os filmes dele | 🔥 | Baixo |
| **TV ao vivo com grade** | Na página do canal, a programação das próximas horas mais bonita, com "agora" destacado | 🔥 | Baixo |
| **Selo de áudio de cinema** | `Atmos` / `DTS-HD` / `TrueHD` na lista de fontes (só vale com soundbar boa) | 🔥 | Baixo |

## 3. Bot do Telegram

| Melhoria | Detalhe | Impacto | Esforço |
|---|---|---|---|
| **Botões na resposta** | "▶ Abrir no Stremio" (link direto para o título), "📥 Baixar dublado", "🔁 Outra versão" | 🔥🔥 | Baixo |
| **"O que chegou dublado hoje?"** | Comando `/novidades` com os dublados que ficaram prontos nas últimas 24 h | 🔥🔥 | Baixo |
| **Resumo semanal** | Domingo à noite: estreias da semana, dublados novos das suas séries, estado do A71 | 🔥🔥 | Baixo |
| **Lista de desejos** | "me avisa quando sair dublado X" → a madrugada confere todo dia e avisa quando ficar pronto | 🔥🔥🔥 | Médio |
| **`/reiniciar` e `/teste`** | Reiniciar o Comet e rodar o teste automático pelo celular | 🔥 | Baixo |

## 4. Confiabilidade e segurança

| Melhoria | Detalhe | Impacto | Esforço |
|---|---|---|---|
| **Vigia externo (healthchecks.io)** ✋ | O A71 manda um "estou vivo" a cada 5 min; se parar, o healthchecks avisa no seu Telegram (passo a passo na Parte 6) | 🔥🔥🔥 | Seu: 5 min · meu: baixo |
| **Backup diário** | Banco do Comet (histórico de dublados, notas, cache), `.env` **criptografado** e patch: cópia diária enviada pelo bot só para você (ou para uma pasta do PC) | 🔥🔥🔥 | Baixo |
| **Saúde do A71** | Temperatura, bateria, espaço livre e memória no `/status` e aviso no Telegram se esquentar demais ou o disco encher | 🔥🔥 | Baixo |
| **Proteção da porta pública** | Limitar pedidos por IP no Caddy (barra robôs que varrem a internet) e esconder o `/configure` genérico de quem não tem token | 🔥🔥 | Baixo |
| **Aviso de versão nova do Comet original** | Checagem semanal; quando houver, o bot pergunta "atualizo?" e roda a atualização segura | 🔥 | Baixo |
| **Alerta de fonte morta** | Se uma fonte ficar pausada mais de 24 h (site saiu do ar ou mudou de endereço), aviso no Telegram | 🔥 | Baixo |

## 5. Conteúdo

| Melhoria | Detalhe | Impacto | Esforço |
|---|---|---|---|
| **Mais links diretos dublados** | Procurar outros addons que servem vídeo direto em PT-BR (como FenixFlix/FrostStream) e somar | 🔥🔥 | Médio |
| **Animes dublados mais completos** | A madrugada procurar dublagem em todos os animes do seu histórico e dos populares da temporada | 🔥🔥 | Baixo |
| **Trakt / Letterboxd / MyAnimeList** ✋ | Só se você usar algum: as suas listas viram fileiras | 🔥 | Médio |

## 6. O que depende de você (passo a passo)

### 6.1 Reescrita no AdGuard (opcional: deixa a casa um pouco mais rápida)
Hoje, em casa, o pedido sai até o roteador e volta para o A71. Funciona, mas dá uma volta à toa. A reescrita manda direto:
1. No navegador do PC, abra **http://192.168.3.44:3000** (o painel do AdGuard Home) e entre com o usuário e a senha dele.
2. Menu **Filtros** → **Reescritas de DNS**.
3. Botão **Adicionar reescrita de DNS**.
4. Em **Domínio**, escreva: `a71comet.duckdns.org`
5. Em **Resposta**, escreva: `192.168.3.44`
6. **Salvar.**

Pronto. Fora de casa nada muda, porque lá o AdGuard não é usado.

### 6.2 Vigia externo (healthchecks.io)
1. Entre em **https://healthchecks.io** → **Sign Up** (pode entrar com a conta Google). É grátis.
2. Ele cria um projeto. Clique em **Add Check**:
   - **Name:** `Comet A71`
   - **Period** (de quanto em quanto tempo o A71 avisa): **5 minutes**
   - **Grace** (quanto esperar antes de alarmar): **10 minutes**
   - **Save**.
3. Menu **Integrations** → em **Telegram**, clique em **Add Integration** e siga o link: ele abre o bot do healthchecks no Telegram, você toca em **Iniciar**, e ele liga a integração.
4. Volte em **Checks**, abra o `Comet A71` e copie o **Ping URL** (algo como `https://hc-ping.com/xxxxxxxx-xxxx-...`).
5. **Me mande esse Ping URL.** Eu ponho o A71 para avisar a cada 5 minutos. Se ele parar (sem energia, sem internet ou travado), você recebe no Telegram: "Comet A71 is DOWN".

### 6.3 HTTP/3 no 4G (opcional)
No roteador, na regra **a71 comet** (porta 7443), deixe o protocolo em **TCP/UDP**. Se já estiver assim, nada a fazer.

---

## 7. O que não dá (para não gastar tempo)
- **Prévia em vídeo ao passar por cima da capa:** o app da TV não anima imagens (testado com WebP e GIF), e o protocolo do Stremio não tem campo de vídeo para isso.
- **Pular abertura, mudar o player, mudar o tamanho da legenda pelo addon:** é tudo do app, não do addon.
- **Separar TV de celular:** o app não se identifica e, em casa, tudo chega pelo mesmo endereço. O que existe é "em casa × fora de casa".

---

## 8. Ordem sugerida
1. **Agora (rapidez):** compressão, limite de fontes, capas em WebP e pré-desenhadas, cache esperto. Itens 1, 2 e 4 da Parte 0.
2. **Em seguida (velocidade da 1ª busca):** resposta rápida + completa depois e cache do debrid só no que importa.
3. **Interface:** página "Minhas fileiras", dublagem por episódio e resumo de dublagem na série.
4. **Bot:** lista de desejos, botões, `/novidades` e resumo semanal.
5. **Tranquilidade:** vigia externo (assim que você me mandar o Ping URL), backup diário, saúde do A71 e proteção da porta.
