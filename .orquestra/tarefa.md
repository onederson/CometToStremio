# Tarefa: Traduzir a página /configure do Comet para PT-BR com explicações detalhadas

Contexto: PowerShell em `C:\Users\Vendel\Desktop\Projetos\a71\STREMIO`. Comandos no A71: `.\scripts\a71.ps1 '<cmd>'` / `.\scripts\a71.ps1 -Chroot '<cmd>'`.
`comet-ui\index.html` é uma cópia ORIGINAL de `/opt/comet/comet/templates/index.html` (página `https://a71comet.duckdns.org/configure`). Edite SOMENTE `comet-ui\index.html` no PC; mantenha **LF** (zero `\r`) e UTF-8.

Público: usuário brasileiro leigo que usa Stremio + Real-Debrid e quer conteúdo dublado/dual áudio PT-BR.

## Passo A — Entender antes de escrever (obrigatório)
Para CADA opção do formulário, descubra o que ela faz de verdade lendo o JS do próprio `index.html` (qual chave de config gera) e o código Python no A71 que consome essa chave (`grep -rn "<chave>" /opt/comet/comet --include=*.py`). As explicações devem refletir o comportamento real do código, não suposições. Se não conseguir determinar, escreva uma explicação curta e neutra e liste a opção no relatório final.

## Passo B — Traduzir TODO texto visível
Traduza para português do Brasil natural: títulos, `label=`, `placeholder=`, `help-text=`, textos de `<sl-button>`, `<sl-option>`, `<sl-checkbox>`/`<sl-switch>`, `<summary>`/`<details>`, tooltips, `title=`, mensagens em JS (`textContent`, `innerText`, alerts, toasts, erros, "Copied", "Sign up", "Get API key", "Kodi setup completed..." etc.), `<title>` da página.
- Nomes de idiomas exibidos (gerados em JS, ~linha 1109): exibir em português (ex.: "Português", "Inglês", "Espanhol"). Se os nomes vêm de uma tabela no HTML/JS, traduza a exibição; NUNCA altere os códigos/valores.
- Termos técnicos consagrados podem ficar em inglês quando forem o nome do serviço/padrão (Real-Debrid, Torrent, Magnet, Kodi, HDR, Dolby Vision, Remux, BluRay, WEB-DL), mas a explicação deve ser em português.

## Passo C — Explicações detalhadas
Para TODA opção (inclusive as que hoje não têm `help-text`), adicione/expanda `help-text` em PT-BR explicando em 1–3 frases: o que faz, efeito prático no Stremio e, quando fizer sentido, a recomendação para este uso (Real-Debrid + conteúdo PT-BR). Exemplos de recomendações já definidas: "Somente em cache" ativado; resoluções 4K/1080p/720p; Português como preferido; Português + Inglês como permitidos.
Se houver seções/agrupamentos, adicione um parágrafo introdutório curto em PT-BR no topo de cada seção (use o estilo/elementos já existentes na página).

## REGRAS RÍGIDAS (quebrar qualquer uma = refazer)
- NÃO altere: atributos `value=`, `id=`, `name=`, classes, chaves de objetos JS, nomes de variáveis/funções, lógica JS, URLs, ordem dos campos, CSS, e o formato da config codificada no manifest.
- NÃO traduza strings JS que são comparadas/usadas como dados (ex.: `if (x === "Unknown")`, chaves de mapa). Na dúvida, verifique se a string é só exibida.
- Mantenha template placeholders (`${...}`, `{{ ... }}`, `{% ... %}`) intactos.
- Não edite nenhum outro arquivo do projeto exceto `comet-ui\index.html`, `README.md` (Passo E) e o script do Passo D.

## Passo D — Implantar com script reaplicável
Crie `scripts\deploy_ui.ps1` (curto, comentado em PT) que: `adb push comet-ui\index.html /data/local/tmp/index.html` (um arquivo, nome completo) → via `a71.ps1` faz backup único de `/data/debian/opt/comet/comet/templates/index.html` para `index.html.orig` se ainda não existir, copia por cima, `chmod 644`, apaga o tmp, e reinicia o Comet com `pkill -f "python -m comet.main"` (o watchdog religa em até 30 s).
Execute-o. Aguarde ~45 s e valide do PC:
- `(Invoke-WebRequest https://a71comet.duckdns.org/configure -UseBasicParsing).StatusCode` = 200 e o conteúdo contém textos em PT (ex.: "Idiomas").
- `Invoke-RestMethod https://a71comet.duckdns.org/manifest.json` ainda OK.
- Contagem `\r` = 0 em `comet-ui\index.html`.

## Passo E — README
Adicione uma linha na tabela "Mapa de arquivos" para `comet-ui/index.html` e `scripts/deploy_ui.ps1`, e uma nota curta na Seção 0: página /configure traduzida; após atualizar o Comet (`git pull`), reaplicar com `.\scripts\deploy_ui.ps1` (verificando antes se o `index.html` original mudou upstream).

## Fora de escopo
`admin_dashboard.html`, `admin_login.html`, textos dos resultados de stream no Stremio, código Python, `.env`.

## Resposta final (máx. 8 linhas)
Quantos textos traduzidos / help-texts adicionados, opções cuja explicação ficou incerta, strings JS deixadas em inglês de propósito (e por quê), resultado das validações.
