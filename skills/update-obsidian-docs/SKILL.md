---
name: update-obsidian-docs
description: Keep the four auraFarma Obsidian files in `obsidian/` (two mind-map .canvas + two .md texts) up to date. Use this AFTER implementing a new mechanic/feature, changing the data model or API endpoints, or making an architecture decision you judge important — so the project's mind maps and docs reflect reality. Do NOT use for trivial edits (typos, refactors, small fixes).
---

# Update auraFarma Obsidian docs

This project keeps a small set of living documentation in the `obsidian/` folder.
There are **two perspectives, each in two formats**:

| Arquivo (em `obsidian/`) | Perspectiva | Formato |
| --- | --- | --- |
| `auraFarma - Mapa Mental.canvas` | Tecnica / projeto completo | mapa mental (JSON Canvas) |
| `auraFarma - Mapa Mental.md` | Tecnica / projeto completo | texto |
| `auraFarma - Como Funciona (mapa mental).canvas` | Nao-tecnica (leigo) | mapa mental (JSON Canvas) |
| `auraFarma - Como Funciona (texto).md` | Nao-tecnica (leigo) | texto |

Os `.md` e os `.canvas` se referenciam por wikilinks `[[...]]`.

## Quando usar

Depois de concluir e verificar algo que muda **como o app funciona**: uma
mecanica/feature nova, mudanca no modelo de dados, novos endpoints, troca de
decisao arquitetural relevante, ou um item que saiu de "planejado" para "pronto".
Use seu julgamento — mudancas pequenas (refactor, fix, typo) NAO precisam.

## Regras

- **Sem emojis** em nenhum dos 4 arquivos.
- **Fiel ao codigo real** — descreva o que esta implementado, nao a intencao.
- Mantenha a separacao: o lado **tecnico** pode ter detalhe; o **nao-tecnico**
  deve ficar em linguagem simples (analogias, sem jargao).
- Atualize **as duas formas** da perspectiva afetada (mapa + texto), e geralmente
  as duas perspectivas (tecnica e leiga) quando a mudanca for visivel ao usuario.
- Preserve os wikilinks entre os arquivos.

## Como atualizar os mapas (.canvas)

NAO edite o JSON do canvas a mao (coordenadas/sobreposicao). Em vez disso:

1. Edite as arvores `full` (tecnica) e/ou `easy` (nao-tecnica) em
   `.claude/skills/update-obsidian-docs/scripts/mapgen.cjs`. Cada no e
   `{ text, color?, children? }`; o texto aceita markdown (`**negrito**`, `\n`).
   Ramos de nivel 1 definem a cor (presets "1"-"6"); os filhos herdam.
2. Rode, a partir da **raiz do repo**:
   ```
   node ".claude/skills/update-obsidian-docs/scripts/mapgen.cjs"
   ```
   Ele regenera os dois `.canvas` em `obsidian/` com layout automatico
   (arvore esquerda->direita, sem sobreposicao) e imprime `overlaps 0`.
3. Confirme que a saida diz `overlaps 0` para os dois arquivos.

## Como atualizar os textos (.md)

Edite diretamente:
- `obsidian/auraFarma - Mapa Mental.md` — espelho textual do mapa tecnico
  (objetivo, estado atual em tabela, arquitetura/persistencia, funcionalidades,
  compliance, base de medicamentos, roadmap).
- `obsidian/auraFarma - Como Funciona (texto).md` — espelho do mapa leigo.

Mantenha as secoes coerentes com o que voce mudou no mapa correspondente.

## Checklist

- [ ] Identifiquei a mudanca (mecanica/arquitetura) que justifica a atualizacao.
- [ ] Editei as arvores no `mapgen.cjs` e rodei o gerador (`overlaps 0`).
- [ ] Atualizei o(s) `.md` correspondente(s).
- [ ] Sem emojis; fiel ao codigo; wikilinks preservados.
