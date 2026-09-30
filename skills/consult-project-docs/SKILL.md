---
name: consult-project-docs
description: Consult the auraFarma living docs in `obsidian/` to get richer project context (goals, business model, architecture decisions, data model, feature behavior, roadmap). Use this WHENEVER you are unsure about WHY something exists, HOW a feature is supposed to work end-to-end, what is "pronto/em andamento/planejado", a non-obvious architecture decision, or how the pieces relate — before guessing or answering from partial code reading. Do NOT use for purely mechanical questions answerable by reading one source file (where is X defined, exact signature).
---

# Consultar a documentacao viva do auraFarma

O projeto mantem documentacao viva em `obsidian/`, em **duas perspectivas, cada
uma em dois formatos**. Quando voce tiver duvida sobre alguma parte do projeto,
**leia esses arquivos antes de chutar** — eles dao o "porque" e o panorama que o
codigo sozinho nao explica.

| Arquivo (em `obsidian/`) | Perspectiva | Bom para |
| --- | --- | --- |
| `auraFarma - Mapa Mental.md` | Tecnica / completa (texto) | objetivo, estado atual, **arquitetura e decisoes**, persistencia, endpoints, IA, roadmap |
| `auraFarma - Mapa Mental.canvas` | Tecnica / completa (mapa) | mesma info, em arvore visual (JSON Canvas) |
| `auraFarma - Como Funciona (texto).md` | Leiga (texto) | o que cada tela/feature faz em linguagem simples |
| `auraFarma - Como Funciona (mapa mental).canvas` | Leiga (mapa) | mesma info leiga, em arvore visual |

Os `.md` e os `.canvas` se referenciam por wikilinks `[[...]]`.

## Quando usar

Use ANTES de responder ou agir quando estiver em duvida sobre:

- **Por que** algo existe ou foi feito de certo jeito (decisao de negocio/arquitetura).
- **Como** uma feature funciona ponta a ponta (ex.: fluxo de 2 estagios da IA, escopos, persistencia por usuario, demo de Pedidos).
- O **estado** de algo: pronto, em andamento ou planejado.
- O **modelo de dados** / endpoints / o "seam" mock vs API, em alto nivel.
- Como as **pecas se relacionam** entre telas/servicos.
- Termos do dominio (SNGPC, compliance, ANVISA, Eurofarma) e o que o produto promete.

NAO precisa para perguntas puramente mecanicas que um arquivo-fonte responde
direto (onde X esta definido, assinatura exata de uma funcao, um typo). Nesses
casos use Grep/Read no codigo.

## Como consultar

1. **Comece pelo texto tecnico**: leia `obsidian/auraFarma - Mapa Mental.md`. Ele
   e o espelho textual mais completo (objetivo, estado atual em tabela,
   arquitetura/decisoes, persistencia, secoes 8.1/8.2 de IA e Pedidos, roadmap).
2. Se a duvida for sobre **comportamento visivel ao usuario** ou voce quer a
   explicacao simples, leia `obsidian/auraFarma - Como Funciona (texto).md`.
3. Os `.canvas` sao JSON (nos + arestas). Para ler o conteudo, prefira os `.md`
   (mesma informacao, mais legivel). Abra o `.canvas` so se precisar entender a
   **estrutura/hierarquia** visual; os textos dos nos estao no campo `text`.
4. Cruze com o codigo: a doc da o "porque" e o panorama; o codigo da o "como"
   exato. Se a doc divergir do codigo, **o codigo e a verdade** — e isso e sinal
   de que a doc precisa ser atualizada (veja abaixo).

## Importante

- A doc reflete o estado de quando foi escrita. Se voce notar que ela esta
  **desatualizada** em relacao ao codigo, use a skill **`update-obsidian-docs`**
  para corrigi-la (ela regenera os mapas e atualiza os textos).
- Nao edite os `.canvas` a mao — isso e papel da `update-obsidian-docs`.
- Estes arquivos sao um complemento ao `CLAUDE.md` (guia tecnico do repo); para
  comandos, estrutura de pastas e como rodar, o `CLAUDE.md` continua sendo a
  referencia primaria.
