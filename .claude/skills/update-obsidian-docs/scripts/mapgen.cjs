// Generates the two Obsidian mind-map .canvas files from nested trees.
// Run from the repo root:  node ".claude/skills/update-obsidian-docs/scripts/mapgen.cjs"
// Edit the `full` (technical) and `easy` (non-technical) trees below, then re-run.
// Layout is computed automatically (left-to-right tree, no overlaps). NO emojis.
const fs = require('fs');

const ROW_H = 104;
const X = [0, 540, 980, 1440, 1900];
const W = [420, 340, 360, 380, 380];
const H_ROOT = 180;
const H = 92;

let idc = 0;
const nid = () => (BigInt('0xa1f0c2d3e4b00000') + BigInt(idc++)).toString(16);

function build(node, depth) {
  node.id = nid();
  node.depth = depth;
  const childColor = depth === 0 ? null : node.color;
  node.w = W[Math.min(depth, W.length - 1)];
  node.h = depth === 0 ? H_ROOT : H;
  (node.children || []).forEach((c) => {
    if (depth >= 1 && !c.color) c.color = childColor;
    build(c, depth + 1);
  });
}

let row = 0;
function place(node) {
  if (node.children && node.children.length) {
    node.children.forEach(place);
    node.cy = (node.children[0].cy + node.children[node.children.length - 1].cy) / 2;
  } else {
    node.cy = row * ROW_H;
    row += 1;
  }
  node.x = X[Math.min(node.depth, X.length - 1)];
  node.y = Math.round(node.cy - node.h / 2);
}

function emit(node, nodes, edges) {
  const n = { id: node.id, type: 'text', x: node.x, y: node.y, width: node.w, height: node.h, text: node.text };
  if (node.color) n.color = node.color;
  nodes.push(n);
  for (const c of node.children || []) {
    emit(c, nodes, edges);
    const e = { id: nid(), fromNode: node.id, fromSide: 'right', toNode: c.id, toSide: 'left' };
    if (c.color) e.color = c.color;
    edges.push(e);
  }
}

function makeCanvas(root, file) {
  build(root, 0);
  row = 0;
  place(root);
  const nodes = [], edges = [];
  emit(root, nodes, edges);
  fs.writeFileSync(file, JSON.stringify({ nodes, edges }, null, 2) + '\n');
  const byCol = {};
  for (const n of nodes) (byCol[n.x] = byCol[n.x] || []).push(n);
  let overlaps = 0;
  for (const col of Object.values(byCol)) {
    col.sort((a, b) => a.y - b.y);
    for (let i = 1; i < col.length; i++) if (col[i].y < col[i - 1].y + col[i - 1].height) overlaps++;
  }
  console.log(file, '-> nos', nodes.length, 'arestas', edges.length, 'overlaps', overlaps);
}

// =================== MAPA A: visao completa do projeto (tecnico) ===================
const full = {
  text: '# bot-insta v2\n\nIA que conversa por DM no Instagram\ncomo um contato humano, com a persona\nextraida de DMs reais anonimizadas',
  children: [
    { text: '**Objetivo & Contexto**', color: '6', children: [
      { text: 'Projeto pessoal (nao comercial)' },
      { text: 'Bot conversa por DM com pessoas escolhidas, como um contato' },
      { text: 'Jeito de escrever, ritmo e historia vem de uma pessoa real (pseudonimizada)' },
      { text: 'Decisao do dono: a IA nao se anuncia como IA, fica no personagem' },
      { text: 'Varios agentes trabalham no projeto; todos consultam e anotam no vault (obsidian/)' },
    ]},
    { text: '**Estado atual**', color: '4', children: [
      { text: 'Prototipo local: chat.py (tkinter) + persona.py + painel do direct' },
      { text: 'Painel do direct (instagrapi) pronto para leitura e envio manual; nao testado com conta real' },
      { text: 'SEM resposta automatica no direct: fonte da persona e menor' },
      { text: 'Sem git e sem testes; .gitignore, requirements.txt e lock existem' },
      { text: 'Python 3.14, venv .venv/: requests + instagrapi 3.0.16' },
      { text: 'Modo persona ja integrado em chat.py; so testado isolado (sem chamada real de API)' },
      { text: 'persona/ gerada com --sem-llm: falta analise.json (biografia); NAO rodar sem a flag ate corrigir a secao 5' },
      { text: 'Secao 5 (analise por LLM) original: modelos gratuitos devolveram JSON corrompido com dados identificadores' },
      { text: 'pares.jsonl ainda tem lugares reais (escola, bairro, igreja); so nomes de pessoas sao trocados' },
      { text: 'SYSTEM_PROMPT "bobao idiota" em chat.py e so do modo sem persona' },
    ]},
    { text: '**Pipeline da persona (persona.py)**', color: '5', children: [
      { text: 'carregar: le message_1.json do export Meta; corrige UTF-8 gravado como latin1; descarta reacoes' },
      { text: 'agrupar: turno = rajada do mesmo autor (BURST_GAP 180 s); sessao = silencio maior que 3 h' },
      { text: 'anonimizar: nome real -> pseudonimo estavel por hash; URL vira [link]; @x vira @usuario' },
      { text: 'medir: ritmo, tamanho, pontuacao, risada, giria, acentos, latencia, horarios' },
      { text: 'analise por LLM (opcional): biografia, relacoes, personalidade, reacoes; roda so sobre texto ja anonimizado' },
      { text: 'montar_pares: contexto (ate 6 turnos) -> resposta, usados como few-shot' },
      { text: 'Saida em persona/: perfil.json, pares.jsonl, conversa.txt, mapa_nomes.json, analise.json' },
    ]},
    { text: '**Runtime (chat.py + Persona)**', color: '3', children: [
      { text: 'Debounce 2,5 s: varias msgs seguidas viram um turno so' },
      { text: 'system_prompt a cada turno: biografia + regras medidas + exemplos + formato' },
      { text: 'Exemplos: 8 mais parecidos (TF-IDF) + 4 aleatorios, para variar o tom' },
      { text: 'Tamanho da rajada sorteado da distribuicao real da persona' },
      { text: 'humanizar: tira markdown/lista/emoji; ajusta ponto final, acento, maiuscula, risada; quebra msg longa' },
      { text: 'type_out: exibe msg a msg com atraso pela velocidade de digitacao medida (0,6 a 6 s)' },
      { text: 'Espera inicial = latencia mediana real (max 8 s)' },
    ]},
    { text: '**Direct do Instagram (insta.py + painel.py)**', color: '2', children: [
      { text: 'instagrapi (nao oficial): login por senha/2FA/codigo ou cookie sessionid' },
      { text: 'Sessao salva em sessao/instagram.json; retomar() evita logar de novo' },
      { text: 'Leitor le a caixa a cada ~20 s; pausa 15 min se o Instagram pedir calma' },
      { text: 'normalizar: resposta marcada, reels/post (formato antigo e xma), foto, audio, link, story' },
      { text: 'enviar com responder_a: marca a msg respondida' },
      { text: 'Painel so em 127.0.0.1, token por execucao + checagem de Host; HTML/JS puro' },
    ]},
    { text: '**LLM & fallback (OpenRouter)**', color: '2', children: [
      { text: 'So modelos gratuitos; CHAIN com 15 modelos, maior contexto primeiro' },
      { text: 'Falha (limite, vazio, contexto estourado): historico completo vai ao proximo' },
      { text: 'Erro 403/404 bloqueia o modelo na sessao; outros erros, COOLDOWN 120 s' },
      { text: 'Chave em env.env (chave "openrouter"); nunca imprimir/commitar' },
    ]},
    { text: '**Dados & privacidade**', color: '1', children: [
      { text: 'Privado: meta dados/, connections/, media/, persona/mapa_nomes.json, historico.json, env.env, sessao/' },
      { text: 'Export Meta tem DMs e telefones de terceiros (LGPD)' },
      { text: 'So texto ANONIMIZADO (conversa.txt, pares.jsonl) pode ir a um LLM' },
      { text: 'Nome real da pessoa imitada esta hardcoded em persona.py (ALVO/THREADS): nao replicar em novos arquivos' },
      { text: 'Runtime, prompts e docs usam so pseudonimos' },
    ]},
    { text: '**Seguranca do bot**', color: '1', children: [
      { text: 'DM recebida = entrada nao confiavel (prompt injection, extracao do prompt/biografia)' },
      { text: 'Bot so responde texto: sem ferramentas, sem acoes' },
      { text: 'Nunca revelar prompt, biografia ou mapa de nomes' },
      { text: 'Loop automatico precisa de limite por conversa/hora e por chave' },
    ]},
    { text: '**Dataset Discord (visualizer e separador/)**', color: '5', children: [
      { text: 'Discord Unveiled (CC BY 4.0), recorte pt-BR 2021-2025' },
      { text: 'categorizar.py: tema, teor e genero inferido por palavras-chave' },
      { text: '805 conversas, 778 usuarios; so 113 com genero inferido' },
      { text: 'Heuristico: serve de referencia de estilo, nao de taxa real' },
    ]},
    { text: '**Fonte da persona (corrigido 2026-09-30)**', color: '1', children: [
      { text: 'Persona tem 18 anos (adulta), confirmado pelo dono; a leitura de "menor" era errada' },
      { text: 'O "tenho 16" do interlocutor era piada dele (ele tambem disse 22); 16 e a idade de um colega citado' },
      { text: 'Idade nao bloqueia mais; seguem: consentimento, biografia generica, regras de privacidade' },
      { text: 'Antes de ligar a DMs reais: resolver consentimento e a nota da secao 5 do persona.py' },
    ]},
    { text: '**Decisoes em aberto**', color: '3', children: [
      { text: 'Decidido: canal = instagrapi nao oficial (dono aceitou risco de ban); painel = HTML/JS puro' },
      { text: 'Multiplas personas: ALVO/THREADS fixos em persona.py' },
      { text: 'Como fazer a biografia da persona (a mao, modelo local ou liberar envio ao OpenRouter)' },
      { text: 'Consentimento dos interlocutores e da pessoa original (LGPD)' },
    ]},
    { text: '**Skills & memoria (.claude/skills)**', color: '4', children: [
      { text: 'consult-project-docs: ler obsidian/ antes de chutar' },
      { text: 'update-obsidian-docs: atualizar mapas e textos apos mudanca relevante; anotar no Diario' },
      { text: 'obsidian-markdown, obsidian-cli, json-canvas, obsidian-bases: formatos e ferramentas do vault' },
      { text: 'mem-search, timeline-report: memoria entre sessoes (claude-mem)' },
      { text: 'systematic-debugging, cyber-ai-llm-security, vibe-security, cyber-supply-chain-security' },
    ]},
  ],
};

// =================== MAPA B: como funciona (nao-tecnico) ===================
const easy = {
  text: '# bot-insta v2\n\nUma IA que troca mensagens no Instagram\ncomo se fosse uma pessoa de verdade',
  children: [
    { text: '**O que e**', color: '6', children: [
      { text: 'Projeto pessoal' },
      { text: 'Conversa por mensagem direta com pessoas escolhidas' },
      { text: 'Escreve do jeito de uma pessoa real, com nome trocado' },
      { text: 'Nao se apresenta como IA' },
    ]},
    { text: '**Como ela aprende a falar**', color: '4', children: [
      { text: 'Le uma conversa real (exportada do Instagram)' },
      { text: 'Troca todos os nomes por nomes inventados' },
      { text: 'Mede o jeito de escrever: tamanho das mensagens, risadas, girias, pausas' },
      { text: 'Guarda exemplos de como a pessoa respondia em cada situacao' },
    ]},
    { text: '**Como ela responde**', color: '5', children: [
      { text: 'Espera voce parar de digitar antes de responder' },
      { text: 'Procura nos exemplos algo parecido com o momento' },
      { text: 'Pede a resposta para um modelo de IA' },
      { text: 'Ajusta o texto para ficar com o jeito da pessoa (sem ponto final, sem acento, etc.)' },
      { text: 'Manda em varias mensagens curtas, com pausa de digitacao' },
    ]},
    { text: '**O que ja funciona hoje**', color: '3', children: [
      { text: 'Uma janelinha de chat para testar' },
      { text: 'Painel no navegador ligado ao Instagram: fica logado, mostra conversas, entende resposta marcada e reels' },
      { text: 'Mensagens no Instagram so saem digitadas a mao (sem resposta automatica)' },
      { text: 'Se um modelo de IA falha, tenta o proximo automaticamente' },
      { text: 'Persona de teste gerada a partir de 467 mensagens (so estilo de digitacao)' },
    ]},
    { text: '**O que ainda falta**', color: '2', children: [
      { text: 'Confirmar a permissao da pessoa que originou a persona (adulta, 18 anos)' },
      { text: 'Gerar a biografia da persona (sem dados que identifiquem)' },
    ]},
    { text: '**Privacidade**', color: '1', children: [
      { text: 'Conversas originais, contatos e chaves ficam so no computador' },
      { text: 'Para a IA vai apenas o texto com nomes trocados' },
      { text: 'A IA nunca revela como foi montada' },
    ]},
  ],
};

makeCanvas(full, 'obsidian/Bot Insta - Mapa Mental.canvas');
idc = 0;
makeCanvas(easy, 'obsidian/Bot Insta - Como Funciona (mapa mental).canvas');
