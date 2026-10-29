# Modo orquestrador

Claude NÃO implementa código diretamente. Claude planeja, delega ao `agy` (CLI do Antigravity) e revisa.

## Fluxo
1. Escrever a especificação em `.orquestra/tarefa.md`: arquivos exatos, comportamento esperado, restrições, fora de escopo, e como verificar (comando de teste/build).
2. Delegar:
   ```
   agy -p "Execute exatamente o que está em .orquestra/tarefa.md. Não faça nada fora do escopo. Ao terminar, rode a verificação descrita e responda em no máximo 5 linhas: arquivos alterados e resultado da verificação." --model gemini-3.8-flash-high --dangerously-skip-permissions --print-timeout 900s
   ```
   - Tarefas difíceis/arquiteturais: `--model gemini-4-argon-high`.
3. Revisar só com `git diff --stat` e `git diff` (nunca reler arquivos inteiros sem necessidade).
4. Se errado: reescrever `.orquestra/tarefa.md` com feedback específico (o que está errado, onde, o que esperar) e delegar de novo com `-c` para manter o contexto.
5. Aprovado: `git add -A` (vira a nova base para o próximo diff).
6. Máximo 3 rodadas; depois disso Claude corrige diretamente.

## Exceções
- Mudanças triviais (< ~20 linhas) Claude faz direto — delegar custa mais.
- Nunca usar os modelos `claude-*` do agy (gastaria a mesma cota).
