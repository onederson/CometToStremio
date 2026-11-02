# Como criar o bot do Telegram do Comet (passo a passo, sem complicação)

O bot é um "contato" no seu Telegram que conversa com o Comet do A71. Com ele você vai poder:

- pedir um filme ou episódio pelo celular ("Duna 2 dublado") e o Comet já deixa pronto no Real-Debrid;
- receber aviso quando chegar episódio dublado de uma série que você acompanha;
- receber aviso se o A71 cair ou se a assinatura do Real-Debrid/TorBox estiver para vencer.

Leva uns **3 minutos**. Você só precisa do Telegram instalado (celular ou PC).

---

## Passo 1: abrir o "BotFather"

O BotFather é o robô oficial do próprio Telegram que cria bots.

1. Abra o Telegram.
2. Toque na **lupa** (busca) e digite: `BotFather`
3. Abra o que tem o **selo azul de verificado** ✔️ e o nome **@BotFather**.
   - ⚠️ Cuidado com imitações: tem que ser exatamente `@BotFather`, com o selo azul.
4. Toque em **Iniciar** (ou **Start**) lá embaixo.

## Passo 2: criar o bot

1. Na conversa com o BotFather, envie a mensagem:
   ```
   /newbot
   ```
2. Ele pergunta o **nome** do bot (é o nome que aparece na conversa, pode ter espaço). Envie, por exemplo:
   ```
   Comet A71
   ```
3. Ele pergunta o **nome de usuário** (o "@" do bot). Regras: sem espaço, sem acento, e **tem que terminar com `bot`**. Envie, por exemplo:
   ```
   comet_a71_casa_bot
   ```
   - Se ele responder que já existe ("Sorry, this username is already taken"), invente outro, ex.: `comet_a71_vendel_bot`, `meu_comet_2026_bot`.

## Passo 3: copiar o token

Quando der certo, o BotFather manda uma mensagem que começa com **"Done! Congratulations on your new bot."**.

Nela tem uma linha assim (o seu vai ser diferente):

```
Use this token to access the HTTP API:
7123456789:AAH-xYzAbCdEfGhIjKlMnOpQrStUvWxYz12
```

Esse texto comprido (`números:letras`) é o **token**. Toque nele para copiar.

> 🔒 O token é como a senha do bot: quem tiver ele controla o bot. Mande só para mim (aqui na conversa do Claude). Não poste em grupo nem em print público.

## Passo 4: "acordar" o bot

Isso é necessário para o bot poder te mandar mensagens.

1. Na mesma mensagem do BotFather tem um link `t.me/seu_bot` (ex.: `t.me/comet_a71_casa_bot`). Toque nele.
2. Toque em **Iniciar** (ou **Start**).
3. Mande qualquer mensagem, por exemplo: `oi`

Ele ainda não vai responder nada. Isso é normal: o Comet só vai "ligar" o bot depois que eu configurar.

## Passo 5: me mandar o token

Cole o token aqui na conversa comigo. Eu:

1. guardo ele no `.env` do A71 (fora do GitHub);
2. descubro o seu chat automaticamente (pela mensagem `oi` do passo 4);
3. ligo o bot e te mando a primeira mensagem de teste.

---

## Depois de pronto: como usar

Converse com o bot como se fosse uma pessoa:

| Você manda | O que acontece |
|---|---|
| `Duna 2 dublado` | o Comet acha o filme, manda o Real-Debrid baixar a melhor versão dublada e avisa quando estiver ⚡ pronto |
| `The Last of Us T2E3` | o mesmo, para um episódio |
| `/status` | resumo do A71: se está tudo ok, memória, últimos avisos |
| `/ajuda` | lista do que ele sabe fazer |

Só você consegue usar: o bot ignora qualquer outra pessoa que encontre ele.

---

## Deu algum problema?

| Problema | O que fazer |
|---|---|
| Não acho o BotFather | Busque por `@BotFather` (com o @) e confira o selo azul ✔️ |
| "This username is already taken" | Escolha outro nome de usuário, sempre terminando em `bot` |
| "Sorry, too many attempts" | Espere alguns minutos e tente de novo |
| Perdi o token | No BotFather, mande `/mybots` → escolha o bot → **API Token** |
| Acho que o token vazou | No BotFather: `/mybots` → o bot → **API Token** → **Revoke current token**, e me mande o novo |
| Quero apagar o bot | No BotFather: `/mybots` → o bot → **Delete Bot** |
