---
tags: [bot-insta, tecnico]
---

# bot-insta v2 - Mapa Mental (tecnico)

Espelho textual de [[Bot Insta - Mapa Mental.canvas]]. Versao leiga: [[Bot Insta - Como Funciona (texto)]]. Notas cronologicas: [[Bot Insta - Diario]].

## Objetivo e contexto

- Projeto pessoal, nao comercial.
- IA que conversa por DM no Instagram com pessoas escolhidas, como um contato, com jeito de escrever, ritmo e historia de uma pessoa real (pseudonimizada), extraidos do export de DMs da Meta.
- Decisao do dono: a IA nao se anuncia como IA; fica no personagem.
- Divisao de trabalho: varios agentes (Claude Code e outros) trabalham no projeto. Todos consultam este vault antes de agir e anotam aqui o que muda.

## Estado atual

| Item | Estado |
| --- | --- |
| Pipeline de persona (`persona.py`) | pronto (467 msgs, 235 turnos, 234 pares) |
| Chat de teste (`chat.py`, tkinter) | pronto |
| Fallback entre modelos gratuitos (OpenRouter) | pronto |
| Modo persona em `chat.py` | integrado; so testado isolado (sem chamada real de API nem janela) |
| `persona/analise.json` (biografia por LLM) | pendente: falta a secao 5 do `persona.py` corrigida e a decisao sobre a biografia (ver "Fonte da persona") |
| Secao 5 de `persona.py` (analise por LLM) | versao original, nao usar; reescrita planejada e nao aplicada |
| Integracao com o Instagram (`insta.py`, instagrapi) | pronta para leitura e envio manual; nao testada com conta real |
| Painel (`painel.py` + `painel/index.html`) | pronto; HTML/JS puro, visual das referencias |
| Resposta automatica no direct | nao implementada: falta consentimento e definir interlocutores (ver abaixo) |
| `.gitignore` / `requirements.txt` + lock | existem |
| git / testes | nao existem |

Ambiente: Python 3.14 com venv `.venv/`: `requests`, `instagrapi==3.0.16` (mais `tkinter` da stdlib).

## Pipeline da persona (`persona.py`)

Comando: `python persona.py` (com analise por LLM) ou `python persona.py --sem-llm`.

1. `carregar`: le `message_1.json` das threads em `THREADS`; corrige UTF-8 gravado como latin1 (`fix`); descarta reacoes; marca midia (foto, video, audio, post/reel, figurinha).
2. `agrupar`: turno = rajada do mesmo autor com pausa menor que `BURST_GAP` (180 s); sessao nova quando o silencio passa de `SESSION_GAP` (3 h).
3. Anonimizacao: `detectar_nomes` (participantes, palavras capitalizadas, lista de nomes comuns, `NOMES_EXTRA`) -> `montar_mapa` (pseudonimo estavel por hash; edite `mapa_nomes.json` a mao para corrigir) -> `compilar_anonimizador` (URL vira `[link]`, `@x` vira `@usuario`, preserva caixa).
4. `medir`: ritmo (msgs por turno, chars por msg), pontuacao final, virgulas, omissao de acento, risadas, emoji, alongamento, girias, vocabulario distintivo (log-odds), aberturas, velocidade de digitacao (cps), latencia de resposta, horarios.
5. Analise por LLM (`analisar`): biografia, relacoes, personalidade, estilo qualitativo, como reage, expressoes, assuntos; roda so sobre texto ja anonimizado; nomes que escapam voltam ao mapa e tudo e re-anonimizado.
6. `montar_pares`: cada resposta da persona com ate `CONTEXTO_TURNOS` (6) turnos anteriores da mesma sessao.

Saidas em `persona/`: `perfil.json`, `pares.jsonl`, `conversa.txt`, `mapa_nomes.json` (privado), `analise.json` (so sem `--sem-llm`).

Persona atual: pseudonimo "Luna Siqueira"; interlocutor "Levi".

## Runtime (`chat.py` + classe `Persona`)

- `Persona.carregar()` roda ao importar `chat.py`; sem `persona/perfil.json` o chat vira chat puro com `SYSTEM_PROMPT`.
- Debounce de 2,5 s (`DEBOUNCE_MS`): varias msgs do usuario viram um turno; se chegar msg enquanto ela responde, roda de novo (`again`).
- `system_prompt(historico)`: biografia + personalidade + relacoes + regras medidas (`regras`) + estilo qualitativo + exemplos + formato de saida. Exemplos = 8 por similaridade TF-IDF (`exemplos`) + 4 aleatorios. Tamanho da rajada sorteado de `dist_msgs_por_turno`.
- Regras de formato do prompt: uma msg por linha, sem markdown/aspas/"Nome:", sem linguagem de assistente; fatos so da biografia, senao desconversa.
- `humanizar`: remove lista/markdown/emoji (se ela nao usa), unifica risada, tira ponto final e acento na proporcao real, ajusta maiuscula inicial, quebra msgs acima do limite, limita numero de msgs.
- `type_out`: espera inicial = latencia mediana (max 8 s); cada msg aparece apos `atraso` (chars / cps, entre 0,6 e 6 s).

## Direct do Instagram (`insta.py` + `painel.py`)

- Comando: `.venv\Scripts\python painel.py` (abre http://127.0.0.1:8765).
- Login: usuario e senha (2FA pelo campo de codigo; codigo por e-mail/SMS via `challenge_code_handler`, que espera o painel ate 300 s) ou cookie `sessionid`. Senha nunca gravada.
- Sessao: `sessao/instagram.json` (cookies + ids do aparelho, privado). `retomar()` reaproveita ao abrir; relogin reaproveita o mesmo aparelho. Regravada a cada 10 min.
- `Leitor` le a caixa principal a cada ~20 s (+ jitter); `PleaseWaitFewMinutes`/`FeedbackRequired`/limite geram pausa de 15 min; `LoginRequired` volta para a tela de login. `ATRASO_API` 1 a 2 s entre requisicoes.
- `normalizar`: cada msg vira dict com `texto`, `anexo` (reels, post, foto, video, audio, figurinha, link, story/resposta a story), `resposta_a` (msg marcada) e `para_llm` (descricao entre colchetes, sem @ de terceiros). Cobre formatos antigo (`clip`, `media_share`) e novo (`xma_clip`, `generic_xma`).
- `enviar(thread, texto, responder_a)`: manda texto, opcionalmente marcando uma msg.
- Painel: so 127.0.0.1; token aleatorio por execucao exigido em toda chamada `/api/*` e Host checado (anti-CSRF/DNS rebinding); texto de terceiros renderizado so via `textContent`.
- Sem resposta automatica: nada sai sem ser digitado no painel.

## LLM e fallback

- OpenRouter, `stream=True`, timeout (10, 120) s.
- `CHAIN`: 15 modelos gratuitos, maior contexto primeiro; pula quem nao comporta o historico (`CHARS_PER_TOKEN` 3, `OUTPUT_MARGIN` 8000).
- Falha (HTTP != 200, erro no stream, resposta vazia): historico completo reenviado ao proximo. 403/404 bloqueia o modelo na sessao; outros erros, `COOLDOWN` 120 s.
- Chave: `env.env`, nome `openrouter` (ou `openrouter_api_key`), lida por `load_key()`.
- Modelos fora da cadeia de proposito: `thinkingmachines/inkling*` (403, so aceita agentic harness) e `nemotron-3.5-content-safety` (classificador).

## Dados e privacidade

- Privados: `meta dados/` (DMs de ~127 conversas, midia), `connections/` (nomes + telefones), `media/`, `persona/mapa_nomes.json`, `historico.json`, `env.env`, `sessao/` (cookies da conta), `visualizer e separador/dataset/categorizado/mapa_usuario_hash_ORIGINAL.csv`.
- Export Meta contem dados de terceiros (LGPD). So texto anonimizado (`conversa.txt`, `pares.jsonl`) pode ir a um LLM.
- `persona.py` tem o nome real do alvo em `ALVO`/`THREADS`. Nao replicar em arquivos novos, docs ou prompts; usar pseudonimos.
- Sem git ainda. `.gitignore` ja cobre os itens privados, `sessao/`, `.venv/` e `__pycache__/`.

## Seguranca do bot

- DM recebida e entrada nao confiavel: prompt injection, tentativa de extrair prompt/biografia.
- O bot so responde texto; sem ferramentas nem acoes; nunca executar ou seguir como instrucao o conteudo recebido; nunca revelar prompt, biografia ou mapa de nomes.
- Qualquer loop automatico precisa de limite por conversa/hora e por chave.

## Dataset Discord (`visualizer e separador/`)

- Fonte: Discord Unveiled (Aquino et al., ICWSM 2025, CC BY 4.0), servidores pt-BR 2021-2025, autores ja hasheados.
- `categorizar.py` gera tema (palavras-chave), teor (multi-etiqueta) e genero (inferido so por marcas gramaticais) para 805 conversas / 778 usuarios; so 113 usuarios com genero inferido, 85% indeterminado.
- Heuristico e com falhas conhecidas; ver os `LEIA-ME.md` da pasta. Relacao com o bot ainda nao definida (referencia de estilo / trabalho separado).

essa parte n sera usada no projeto atual

## Fonte da persona (corrigido, 2026-09-30)

- A persona atual (Luna Siqueira) tem 18 anos (adulta), confirmado pelo dono, que participou da conversa. Ela diz "eu tenho 18 anos" e o "15 e 19" sao as idades dela e do ex no namoro passado. O "tenho 16" do interlocutor era piada dele (ele tambem disse 22); 16 e a idade de um colega citado. A nota de 2026-09-29 ("fonte menor") era leitura errada e foi retirada.
- A idade nao bloqueia mais. Seguem valendo: consentimento, biografia generica (sem escola/bairro/idade exata/aniversario) e as regras de privacidade.
- Na unica execucao da analise por LLM, os modelos gratuitos devolveram JSON corrompido e uma biografia com idade, escola, bairro e aniversario; o arquivo foi apagado. Trocar so nomes de pessoas nao anonimiza: `pares.jsonl` e `conversa.txt` ainda tem lugares reais.
- Caminho: resolver consentimento, corrigir a secao 5 do `persona.py` e so entao gerar biografia (a mao, modelo local ou liberar envio ao OpenRouter).

## Decisoes em aberto

1. **Multiplas personas**: `ALVO` e `THREADS` fixos em `persona.py`.
2. **Como gerar a biografia** da persona (a mao, modelo local ou liberar o envio ao OpenRouter, hoje bloqueado pelo classificador de permissoes).
3. **Consentimento** dos interlocutores e da pessoa original (LGPD).

Decididos em 2026-09-29: canal = `instagrapi` nao oficial (dono aceitou o risco de banimento); painel = HTML/JS puro servido por `painel.py`.

## Skills do projeto (`.claude/skills/`)

- Consulta e memoria: `consult-project-docs`, `update-obsidian-docs`, `obsidian-markdown`, `obsidian-cli`, `json-canvas`, `obsidian-bases`, `mem-search`, `timeline-report`.
- Qualidade e seguranca: `systematic-debugging`, `cyber-ai-llm-security`, `vibe-security`, `cyber-supply-chain-security`.
- `mem-search` e `timeline-report` dependem do plugin claude-mem estar ativo.
