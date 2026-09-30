---
name: consult-project-docs
description: Consult the bot-insta living docs in `obsidian/` to get project context (goal, current state, architecture decisions, persona pipeline, privacy rules, open decisions). Use this WHENEVER you are unsure about WHY something exists, HOW a part works end-to-end, what is "pronto/pendente/em aberto", a non-obvious decision, or how the pieces relate — before guessing or answering from partial code reading. Do NOT use for purely mechanical questions answerable by reading one source file (where is X defined, exact signature).
---

# Consultar a documentacao viva do bot-insta

O projeto mantem documentacao viva em `obsidian/`. Varios agentes (Claude Code e
outros) trabalham no projeto: cada um **consulta** estes arquivos antes de chutar e
**anota** nelas o que muda (skill `update-obsidian-docs`).

| Arquivo (em `obsidian/`) | Perspectiva | Bom para |
| --- | --- | --- |
| `Bot Insta - Mapa Mental.md` | Tecnica / completa (texto) | objetivo, estado atual, pipeline da persona, runtime, fallback, privacidade, decisoes em aberto |
| `Bot Insta - Mapa Mental.canvas` | Tecnica / completa (mapa) | mesma info em arvore visual (JSON Canvas) |
| `Bot Insta - Como Funciona (texto).md` | Leiga (texto) | o que o bot faz, em linguagem simples |
| `Bot Insta - Como Funciona (mapa mental).canvas` | Leiga (mapa) | mesma info leiga em arvore visual |
| `Bot Insta - Diario.md` | Cronologica | o que mudou e foi decidido, por data |

Os `.md` e os `.canvas` se referenciam por wikilinks `[[...]]`.

## Quando usar

Use ANTES de responder ou agir quando estiver em duvida sobre:

- **Por que** algo existe ou foi decidido (ex.: so modelos gratuitos, anonimizacao antes do LLM, IA que nao se anuncia como IA).
- **Como** o fluxo funciona ponta a ponta (DMs -> persona -> prompt -> humanizar -> envio).
- O **estado**: pronto, pendente ou em aberto (integracao com o Instagram, biografia, painel).
- **Regras de privacidade**: o que e privado e o que pode ir a um LLM.
- O que ja foi tentado/decidido antes: leia o `Diario`.

NAO precisa para perguntas puramente mecanicas que um arquivo-fonte responde
direto. Nesses casos use Grep/Read no codigo.

## Como consultar

1. Comece por `obsidian/Bot Insta - Mapa Mental.md` (espelho textual mais completo).
2. Para historico de decisoes, leia `obsidian/Bot Insta - Diario.md` (topo = mais recente).
3. Para a explicacao simples, leia `Bot Insta - Como Funciona (texto).md`.
4. Os `.canvas` sao JSON (nos + arestas, texto no campo `text`). Prefira os `.md`; abra o `.canvas` so para ver a estrutura.
5. Cruze com o codigo: a doc da o "porque"; o codigo da o "como" exato. Se divergirem, **o codigo e a verdade** e a doc precisa de atualizacao.

## Importante

- Se a doc estiver desatualizada, use `update-obsidian-docs`.
- Nao edite os `.canvas` a mao; a geracao e por `update-obsidian-docs`.
- Para memoria de sessoes anteriores (o que foi feito, como resolvemos X) use `mem-search`.
- `CLAUDE.md` continua sendo a referencia primaria para comandos, estrutura de pastas e regras rigidas.
- Nunca copie para o vault nomes reais, handles, telefones ou chaves.
