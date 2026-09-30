# AGENTS.md

Instruções para qualquer agente (Claude Code, Codex, Cursor, Gemini CLI etc.) neste repositório.

1. Leia `CLAUDE.md`: visão geral, estrutura, comandos, regras de privacidade e segurança (rígidas) e decisões em aberto. Vale para todos os agentes, não só para o Claude.
2. As skills ficam em `.claude/skills/<nome>/SKILL.md` (frontmatter `name` + `description`, instruções em markdown, scripts e referências na mesma pasta). Se sua ferramenta não carrega skills sozinha, abra o `SKILL.md` cuja `description` combina com a tarefa e siga-o.
3. Memória do projeto: `obsidian/`.
   - Antes de agir com dúvida sobre porquê, estado ou fluxo: siga `.claude/skills/consult-project-docs/SKILL.md`.
   - Depois de mudança ou decisão relevante: siga `.claude/skills/update-obsidian-docs/SKILL.md` (regenera os `.canvas` com `node ".claude/skills/update-obsidian-docs/scripts/mapgen.cjs"`, atualiza os `.md` e acrescenta entrada em `obsidian/Bot Insta - Diario.md`).
4. Só para Claude Code com o plugin claude-mem: `mem-search` e `timeline-report` (usam o worker local). Outros agentes ignoram.
5. Nunca ler em voz alta, imprimir ou commitar `env.env`; nunca enviar dados privados (`meta dados/`, `connections/`, `media/`, `persona/mapa_nomes.json`) a serviço externo; nunca escrever nomes reais, handles, telefones ou trechos de DMs no código, nos prompts ou no vault. Detalhes em `CLAUDE.md`.
