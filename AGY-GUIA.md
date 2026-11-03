# Guia: usar o `agy` como ajudante para economizar token

Este guia serve para qualquer IA "principal" (Claude, GPT etc.) que trabalha num projeto e quer **gastar menos da própria cota**. A ideia é passar o trabalho braçal para o `agy`, o CLI do Antigravity, que roda os modelos Gemini com cota separada.

Ele foi escrito a partir do que funcionou (e do que deu errado) entre 30/10 e 03/11/2026 no projeto Comet A71. Foram mais de 25 tarefas delegadas, guardadas em `.orquestra/tarefa-*.md`.

---

## 1. A ideia em uma frase

**A IA principal pensa, especifica e confere. O `agy` digita.**

- **A IA principal:**
  - entende o problema;
  - escreve uma especificação curta e fechada;
  - roda o `agy`;
  - **verifica de forma independente**;
  - corrige o que sobrar.
- **O `agy`:** lê o código, edita os arquivos e roda os comandos de teste. É a parte que mais gasta token: ler arquivos grandes, tentar, errar e repetir.

**Quanto se economiza:** uma tarefa média (100–300 linhas em 2–4 arquivos) gastaria de 50 a 150 mil tokens da IA principal fazendo sozinha. Delegada, gasta de 10 a 25 mil: escrever a especificação mais conferir o resultado.

---

## 2. Quando vale (e quando não vale) delegar

| Delegue ao `agy` | Faça você mesmo |
|---|---|
| Recurso novo bem definido (rota, catálogo, módulo novo) | Mudança de menos de ~20 linhas (escrever a especificação custa mais) |
| Código "braçal": muitos arquivos, padrão repetido | Investigação de causa (bug que ninguém sabe de onde vem) |
| Testes, scripts de verificação, documentação | Decisão de arquitetura e coisas sutis (bytes, CRC, concorrência) |
| Portar algo que já existe para outro lugar | Qualquer coisa com segredo (chave, token) no meio |
| Pesquisa com resposta curta ("liste X e Y") | Segunda rodada que falhou 3 vezes (assuma você) |

**Regra de bolso:** se você consegue escrever o "pronto quando..." em 5 linhas verificáveis, delegue.

---

## 3. O comando

```powershell
agy -p "Execute exatamente o que está em .orquestra/tarefa.md. Não faça nada fora do escopo. NÃO rode tarefas em segundo plano. Ao terminar, rode a verificação descrita e responda em no máximo 5 linhas: arquivos alterados e resultado da verificação." --model gemini-3.8-flash-high --dangerously-skip-permissions --print-timeout 1800s
```

- **Modelo do dia a dia:** `gemini-3.8-flash-high`, rápido e barato.
- **Tarefa difícil:** `gemini-4-argon-high`. A cota é menor e já acabou uma vez (volta em ~5 dias).
- **Nunca use os modelos `claude-*` do `agy`:** gastam a mesma cota que você quer economizar.
- **`-c`** continua a última conversa. Use na rodada de correção, para ele não reler tudo.
- **`--print-timeout 1800s`:** com 900 s, tarefas médias morriam no meio.

### Rodar em segundo plano (a IA principal não fica esperando)

```powershell
# exemplo com o PowerShell da IA principal, em run_in_background
agy -p "..." --model gemini-3.8-flash-high --dangerously-skip-permissions --print-timeout 1800s *> .orquestra/log-tarefa-X.txt
```

Enquanto ele trabalha, a IA principal pode preparar a próxima especificação ou conferir outra parte. Só não pode mexer **nos mesmos arquivos** (veja a seção 6).

---

## 4. A especificação (o que faz o `agy` acertar de primeira)

Salve em `.orquestra/tarefa-<letra>.md`. O modelo abaixo veio da tarefa que melhor funcionou:

```markdown
# Tarefa X: <nome curto>

## Contexto
- Onde roda, caminhos dos arquivos certos (com nome de função), como executar comandos.
- O que JÁ existe e deve ser reaproveitado (ex.: "helper de selo em artwork.py, VALID_BADGES").
- Pegadinhas do ambiente (ex.: "o grep do Android não aceita \|, use grep -E").
- **PROIBIDO:** imprimir chaves/tokens; commit; instalar pacotes; mexer em <arquivos X, Y>;
  rodar coisas em segundo plano; comandos com mais de 300 s.

## 1. <parte 1>
- O comportamento exato, com exemplos de entrada e saída.
- Números concretos (limites, tempos, quantidades), nunca "algum", "uns".

## 2. <parte 2>
...

## Fora de escopo
Tudo o resto.

## Aplicar
Passo a passo para colocar no ar (compilar, reiniciar, regenerar patch...).

## Verificação (sem imprimir segredos)
1. Comando → resultado esperado.
2. ...
5. Testes automáticos → "OK".
```

**O que mais fez diferença:**
1. **Nomear arquivos e funções.** "Na função `get_meta` de `meta.py`" evita que ele leia o projeto inteiro (é aí que se perde token e tempo).
2. **Lista PROIBIDO explícita.** Sem ela, ele "melhora" coisas fora do escopo.
3. **Exemplos de saída** (`⭐ IMDb 9,3 · 🍅 89%`). Ele copia o formato à risca.
4. **Verificação numerada e objetiva.** Ela vira o seu checklist de conferência.
5. **Uma tarefa = uma entrega.** Tarefas grandes viram A, B, C em sequência (`tarefa-P`, `P2`, `P3`).

---

## 5. Conferir: a parte que você NÃO pode pular

O `agy` (principalmente o flash) **diz "aprovado" mesmo quando a própria verificação falhou**. Confira sempre por conta própria:

1. `git diff --stat` e `git diff`: ele mexeu só onde devia?
2. Compile e rode os testes você mesmo, sem confiar no texto dele.
3. Faça a verificação da especificação **com os seus comandos**, olhando o resultado real (resposta HTTP, número de itens, arquivo gerado).
4. Procure segredos no diff antes de qualquer commit.

**Erros reais que só a conferência pegou:**
- `NameError` numa variável que não existia, que quebrava o fluxo principal.
- DNS sem resposta tratado como "site bloqueado".
- Temporada/episódio mandados como `"n"` para a API, que respondia "arquivo não encontrado".
- Arquivo de cache gravado vazio e marcado como "atualizado" (só ia tentar de novo em 24 h).

**Rodadas:** no máximo 3 por tarefa. Na 2ª e na 3ª, use `-c` com uma lista curta do que falhou ("o teste 3 deu 0 itens; o log mostra X"). Se a 3ª falhar, corrija você mesmo.

---

## 6. Armadilhas que já aconteceram

| Problema | Como evitar |
|---|---|
| Estoura o tempo e sai no meio, com o código pela metade | `--print-timeout 1800s` e tarefas menores |
| Dispara processo em segundo plano e encerra antes de terminar | Escreva "NÃO rode tarefas em segundo plano" no prompt **e** no PROIBIDO |
| Dois processos (você e o `agy`, ou dois `agy`) editando o mesmo arquivo: um apaga o trabalho do outro | Divida por arquivo. Se precisar paralelizar, cada um no seu arquivo |
| Restauração automática (smoke/rollback) desfaz o trabalho em andamento quando o serviço cai | Desligue a restauração durante o trabalho (aqui: `data/smoke.disable`) e religue no fim |
| Mexe em arquivo que não devia ("aproveitei e melhorei") | PROIBIDO + `Fora de escopo: tudo o resto` + conferir o `git diff --stat` |
| Imprime chave/token no log | PROIBIDO explícito + verificações que mostram só "tem chave: sim/não" |
| Cota do modelo forte acaba | Use o flash por padrão; guarde o argon para o difícil |

---

## 7. Fluxo completo (resumo para colar no CLAUDE.md / AGENTS.md)

```text
1. Entendi o pedido → é delegável? (seção 2). Se não, faço eu.
2. Escrevo .orquestra/tarefa-<letra>.md (seção 4), com PROIBIDO e verificação numerada.
3. Desligo o que pode desfazer trabalho (restauração automática).
4. Rodo o agy em segundo plano com log (seção 3).
5. Enquanto isso, trabalho em OUTROS arquivos ou preparo a próxima tarefa.
6. Quando ele termina: diff → compilar → testes → verificação com meus comandos (seção 5).
7. Falhou? Rodada com -c e lista curta do que falhou (máx. 3). Depois disso, assumo.
8. Passou? Religo a restauração, atualizo a documentação e faço commit só se o usuário pediu.
9. Entrego ao usuário UM resumo final (não o vai e vem).
```

---

## 8. Melhorias que eu faria nesse fluxo (ainda não testadas)

- **Verificação como script, não como texto.** Peça na especificação um `verificar_tarefa_X.py` que imprime `OK`/`FALHOU` em cada item. Você só roda e lê. A conferência fica mais barata e o "aprovado" falso some.
- **Teste primeiro.** Na tarefa A, peça só os testes (que devem falhar). Na B, a implementação até os testes passarem. O flash erra bem menos com um alvo executável.
- **Mapa do projeto pronto.** Um `MAPA.md` com 1 linha por arquivo importante ("`stream.py`: monta a lista de fontes; `_svc_order` decide TorBox/RD"). Cite-o no Contexto e o `agy` não precisa explorar.
- **Log curto de volta.** Peça para ele terminar com um bloco `RESULTADO:` de 5 linhas e leia só esse bloco (`Select-String -Context`), não o log inteiro.
- **Paralelo por arquivo.** Duas especificações que não se tocam (ex.: módulo novo em `radio.py` + ajuste em `live_tv.py`) podem rodar em dois `agy` ao mesmo tempo.
