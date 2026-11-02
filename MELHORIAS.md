# Melhorias possíveis para o Comet A71

*Levantamento de 02/11/2026. Os números da Parte 1 foram medidos pelo endereço público (`:7443`), do jeito que o app do Stremio enxerga o addon.*

Legenda:
- **Impacto:** 🔥🔥🔥 muda o dia a dia · 🔥🔥 bom ganho · 🔥 detalhe.
- **Esforço:** quanto trabalho dá para mim. Nenhum item exige gastar dinheiro.
- ✋ marca o que depende de você.

---

## 0. As 6 primeiras que eu faria (maior ganho por menor esforço)

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
