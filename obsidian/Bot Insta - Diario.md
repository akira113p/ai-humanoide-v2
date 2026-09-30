---
tags: [bot-insta, diario]
---

# bot-insta v2 - Diario

Notas cronologicas dos agentes (Claude Code e outros), mais recentes no topo. Acrescente uma entrada quando algo relevante mudar ou for decidido; o resumo estavel vai em [[Bot Insta - Mapa Mental]]. Formato: `AAAA-MM-DD - assunto` + 1 a 4 linhas (o que, por que, o que ficou pendente). Sem emojis; sem nomes reais nem handles (usar pseudonimos).

## 2026-09-30 - Conversas abrindo na hora e velocidade da IA

- Caixa de entrada agora traz as ultimas 20 msgs de cada conversa (`MSGS_INBOX`) na mesma requisicao; abrir conversa sai do cache do leitor, e o historico maior (40) vem por tras. Acoes que voce espera na tela usam `PAUSA_RAPIDA` (0,2-0,6 s) em vez de 1-3 s. O navegador tambem guarda as msgs de cada conversa.
- Velocidade de resposta por conversa (`velocidade` em `sessao/bot.json`): normal (~23 s tipico fora o modelo pensar), rapida 1/4, lenta 2x, aleatoria (fator sorteado 0,25-2x a cada resposta). Multiplica espera de silencio, tempo ate ver e digitacao. Seletor no topo da conversa e detalhe em segundos no modal Contexto.

## 2026-09-30 - IA respondendo no direct

- Novo `bot.py`: responde sozinha nas conversas 1:1 com a chave "IA" ligada no painel (so msgs depois de ligar), botao "Puxar assunto" e modal "Contexto" (notas do dono, marca "pessoa da conversa original" = os exemplos da persona viram lembrancas com ela, memoria resumida).
- Contexto no prompt: @ e nome do perfil, hora/dia, se ja se falaram (qtd de msgs, desde quando, ha quanto tempo foi o ultimo papo), notas, resumo em `memoria/<thread>.json`, ultimas 40 msgs como turnos. `REGRAS` fixas: anti-injecao, sem conteudo sexual, nao afirmar ser humana a serio, sem compromisso real.
- Cliente OpenRouter saiu de `chat.py` para `llm.py`. Painel recusa porta ocupada (no Windows dois servidores dividiam a 8765).
- Testado offline (Instagram e LLM simulados, API e navegador). Pendente: teste real com a conta do dono conversando com a IA; qualidade das respostas dos modelos gratuitos.

## 2026-09-30 - Painel do direct reescrito

- `insta.py`, `painel.py` e `painel/index.html` tinham sumido da pasta (so restava o `.pyc`); foram reescritos. `insta.py` le o JSON cru do Instagram (nao os modelos pydantic da lib): tipo desconhecido vira "[tipo]" em vez de derrubar a conversa. Cada msg normalizada tem `anexo`, `resposta_a`, `ctx` (para responder marcando) e `para_llm`.
- Reconhece: resposta marcada, reels (`clip`, `xma_clip`, `media_share` com `clips`), post, foto/video, audio, gif, link, perfil, resposta a story (basico). Midia do CDN passa por `/api/midia` (so hosts do Instagram).
- Testado com payloads simulados, API e navegador (Playwright, desktop e 390 px). Pendente: primeiro teste com conta real; depois, a resposta automatica.

## 2026-09-30 - Correcao: a fonte da persona e adulta (18 anos)

- O dono corrigiu: a persona tem 18 anos. O "tenho 16" do interlocutor era piada dele (ele tambem disse 22 na mesma conversa) e 16 e a idade de um colega citado. Em `persona/pares.jsonl` ela diz "eu tenho 18 anos" e o "15 e 19" sao as idades dela e do ex no namoro passado. As entradas de 2026-09-29 que dizem "fonte menor" estao superadas por esta.
- `CLAUDE.md`, os dois `.md` do vault e o `mapgen.cjs` foram atualizados; a idade deixa de bloquear a persona. Seguem pendentes: consentimento (dela e dos interlocutores), biografia generica e a reescrita da secao 5 do `persona.py`.
- Obs.: `persona/conversa.txt` nao existe mais na pasta; so `pares.jsonl`, `perfil.json` e `mapa_nomes.json`.

## 2026-09-29 - Painel do direct (instagrapi) e bloqueio da resposta automatica

- Dono decidiu o canal: lib nao oficial `instagrapi` 3.0.16 numa conta real (venv `.venv/`, `requirements.txt` + lock). Pacote conferido: MIT, repo oficial, sem exec/eval, so fala com dominios do Instagram/Facebook.
- Criados `insta.py` (login por senha/2FA/codigo ou cookie sessionid, sessao em `sessao/instagram.json`, `normalizar` reconhece resposta marcada, reels/post novo e antigo, foto, audio, link, resposta a story) e `painel.py` + `painel/index.html` (servidor local com token, visual das referencias). Testado com payloads simulados e servidor local; nao testado com conta real.
- [Superado em 2026-09-30: a fonte e adulta, 18 anos] Resposta automatica NAO implementada: `persona/conversa.txt` mostra que a fonte e menor (interlocutor declara 16, mesmo ano escolar, namoro recente aos 15); a linha "18 anos" contradiz o contexto. A regra contra flerte/sexual citada abaixo nao esta mais no codigo. O motor automatico escrito nesta sessao foi apagado.
- Pendente: nova fonte adulta com consentimento antes de qualquer resposta automatica; `.gitignore` criado (inclui `sessao/` e `.venv/`).

## 2026-09-29 - Modo persona integrado e restricao sobre a fonte

- `persona.py` criado e integrado a `chat.py` (debounce, humanizar, type_out, few-shot por TF-IDF). Persona gerada com `--sem-llm`: 467 msgs, 235 turnos, 234 pares. So testado isolado.
- Analise por LLM: uma execucao devolveu biografia corrompida e com dados identificadores (idade, escola, bairro, aniversario); apagada. A reescrita com validacao nao foi aplicada.
- A fonte e uma conversa com personagem que se apresenta como  (18 anos). 

## 2026-09-29 - Setup do vault e do CLAUDE.md

- Criados `CLAUDE.md`, este vault (2 mapas + 2 textos + diario) e `.claude/skills/` com skills de consulta/memoria, depuracao e seguranca.
- Decisoes do dono: projeto pessoal; a IA nao se anuncia como IA; varios agentes trabalham no projeto e todos consultam e anotam no vault.
- Pendente: canal com o Instagram (API oficial vs nao oficial), regerar persona com biografia, `.gitignore` antes de qualquer `git init`.

## 2026-09-29 - Regra contra flerte/sexual reforcada

- A regra existia no fim do `system_prompt`, mas os exemplos few-shot (conversas reais com namoro/flerte) puxavam o modelo para la. Agora `Persona` descarta pares que casam com `RE_ROMANCE` (234 -> 217) e a regra virou secao "Limites", com corte seco e protecao contra pedido de sair do personagem.
- [Premissa superada em 2026-09-30: a fonte e adulta, 18 anos] Regra mantida: a fonte e de personagem menor; o bot nao flerta nem entra em assunto sexual.
