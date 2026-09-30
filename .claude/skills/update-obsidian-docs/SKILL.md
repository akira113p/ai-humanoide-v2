---
name: update-obsidian-docs
description: Keep the bot-insta Obsidian vault in `obsidian/` up to date (two mind-map .canvas, two .md texts, and the running Diario). Use this AFTER a relevant change or decision — new feature, changed pipeline/data format, new model/fallback rule, privacy rule, resolved open decision — and to log notes as you go. Do NOT use for trivial edits (typos, refactors, small fixes).
---

# Update bot-insta Obsidian docs

O vault `obsidian/` e a memoria compartilhada do projeto: qualquer agente que mude algo
relevante anota aqui o que mudou. **Duas perspectivas, dois formatos** +
um diario:

| Arquivo (em `obsidian/`) | Perspectiva | Formato |
| --- | --- | --- |
| `Bot Insta - Mapa Mental.canvas` | Tecnica / completa | mapa mental (JSON Canvas) |
| `Bot Insta - Mapa Mental.md` | Tecnica / completa | texto |
| `Bot Insta - Como Funciona (mapa mental).canvas` | Leiga | mapa mental (JSON Canvas) |
| `Bot Insta - Como Funciona (texto).md` | Leiga | texto |
| `Bot Insta - Diario.md` | Cronologica | texto, entradas por data (topo = mais recente) |

Os `.md` e os `.canvas` se referenciam por wikilinks `[[...]]`.

## Quando usar

Depois de concluir e verificar algo que muda **como o bot funciona ou o que foi
decidido**: feature nova, mudanca no formato de `persona/*`, no `CHAIN`/fallback, no
prompt, em regra de privacidade/seguranca, ou um item que saiu de "pendente/em aberto"
para "pronto/decidido". Mudancas pequenas (refactor, fix, typo) NAO precisam.

Para anotacoes menores (o que foi tentado, por que uma opcao foi descartada), basta
uma entrada em `Bot Insta - Diario.md`.

## Regras

- **Sem emojis** em nenhum arquivo do vault.
- **Fiel ao codigo real**: descreva o que esta implementado, nao a intencao. Se o codigo mudou (inclusive por outro agente), leia-o antes de anotar.
- **Privacidade**: so pseudonimos (a persona atual e "Luna Siqueira", interlocutor "Levi"). Nunca nomes reais, handles, telefones, chaves ou trechos de DMs.
- Mantenha a separacao: tecnico com detalhe; leigo em linguagem simples.
- Atualize as duas formas (mapa + texto) da perspectiva afetada.
- Preserve os wikilinks entre os arquivos.
- Sem acentos nos arquivos do vault, como os existentes (ASCII).

## Como atualizar os mapas (.canvas)

NAO edite o JSON do canvas a mao. Em vez disso:

1. Edite as arvores `full` (tecnica) e/ou `easy` (leiga) em
   `.claude/skills/update-obsidian-docs/scripts/mapgen.cjs`. Cada no e
   `{ text, color?, children? }`; o texto aceita markdown (`**negrito**`, `\n`).
   Ramos de nivel 1 definem a cor (presets "1"-"6"); os filhos herdam.
2. Rode, a partir da **raiz do repo**:
   ```
   node ".claude/skills/update-obsidian-docs/scripts/mapgen.cjs"
   ```
   Ele regenera os dois `.canvas` com layout automatico e imprime `overlaps 0`.
3. Confirme `overlaps 0` nos dois arquivos.

## Como atualizar os textos (.md)

Edite diretamente `Bot Insta - Mapa Mental.md` e `Bot Insta - Como Funciona (texto).md`,
mantendo coerencia com o mapa correspondente. No `Diario`, adicione no topo:
`## AAAA-MM-DD - assunto` + 1 a 4 linhas (o que, por que, o que ficou pendente).

## Checklist

- [ ] Identifiquei a mudanca/decisao que justifica a atualizacao.
- [ ] Editei as arvores no `mapgen.cjs` e rodei o gerador (`overlaps 0`).
- [ ] Atualizei o(s) `.md` e adicionei entrada no Diario.
- [ ] Sem emojis; fiel ao codigo; sem dados pessoais; wikilinks preservados.
