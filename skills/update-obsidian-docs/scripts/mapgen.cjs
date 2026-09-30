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
  text: '# auraFarma\n\nGestao + compliance para farmacias pequenas\ncom integracao de compras via distribuidora',
  children: [
    { text: '**Objetivo & Negocio**', color: '6', children: [
      { text: 'Resolve burocracia + desorganizacao de farmacias pequenas' },
      { text: 'Modelo SaaS: mensalidade por farmacia' },
      { text: 'Clientes: farmacias pequenas (foco em genericos)' },
      { text: 'Modelo de dois lados', children: [
        { text: 'Farmacia: gestao completa + compra facil integrada' },
        { text: 'Distribuidora: canal de venda digital + visibilidade da demanda' },
      ]},
      { text: 'Eurofarma: parceria escolar, valor de marca; papel tecnico secundario' },
      { text: 'Integracao de pedidos mira a distribuidora, nao a Eurofarma diretamente' },
    ]},
    { text: '**Arquitetura**', color: '4', children: [
      { text: 'Frontend: React + TS + Vite' },
      { text: 'Backend: Node + Express' },
      { text: 'Banco principal: MongoDB Atlas (auth, estoque, vendas, contagem)' },
      { text: 'Banco de compliance: PostgreSQL Neon (SNGPC, controlados, lotes, receitas)' },
      { text: 'Auth: cookie httpOnly + bcrypt + Google' },
      { text: 'Busca: em memoria no Node + Fuse.js' },
      { text: 'Dados (estoque/vendas/...): 1 doc por produto no Mongo, campos curtos (alias)' },
      { text: 'Carga: GET /api/estado (1 chamada) + rate-limit por usuario' },
      { text: 'IA: OpenRouter, chave server-side, fluxo de 2 estagios + seletor de escopo' },
      { text: 'Decisoes', children: [
        { text: 'CSV ANVISA em memoria (nao sobe pro Mongo)' },
        { text: 'estoque/vendas no Mongo; front fala pela API' },
        { text: 'compliance (SNGPC) no PostgreSQL: precisa de integridade relacional e ACID' },
        { text: 'dois bancos convivem: migrar tudo custaria 5-8 semanas; adicionar Postgres custa 2-3' },
        { text: 'segredos so no .env (VITE_ nunca recebe segredo)' },
        { text: 'cookie httpOnly + Secure + SameSite' },
        { text: 'IA: chave so no backend; 2 estagios (planeja -> consulta dados escopados -> responde)' },
      ]},
    ]},
    { text: '**Estado atual**', color: '5', children: [
      { text: 'Pronto', children: [
        { text: '9 telas (React/Vite)' },
        { text: 'Login / registro / logout + Google OAuth' },
        { text: 'bcrypt + sessao cookie httpOnly' },
        { text: 'MongoDB conectado' },
        { text: 'Base ANVISA 11.7k + busca fuzzy (Fuse.js)' },
        { text: 'Estoque/vendas/solicitados/contagem no MongoDB (por usuario)' },
        { text: 'Assistente IA (OpenRouter) + resumo automatico no Dashboard/Relatorios' },
        { text: 'Observabilidade de producao: logs JSON, request-ID, health detalhado, metricas, alertas' },
        { text: 'Conexao PostgreSQL Neon: camada pronta (pool pg, SSL, health, shutdown); sem tabelas ainda' },
      ]},
      { text: 'Divida tecnica', children: [
        { text: 'Pedidos: demo de logistica so em localStorage; precisa persistir no banco antes do beta' },
      ]},
      { text: 'Em andamento', children: [
        { text: 'Alertas de validade (campo ja existe no produto)' },
      ]},
      { text: 'Planejado', children: [
        { text: 'SNGPC (PostgreSQL Neon)' },
        { text: 'Importacao CSV / NF-e' },
        { text: 'Integracao distribuidora (API real)' },
        { text: 'Sistema de pagamento' },
      ]},
    ]},
    { text: '**Funcionalidades**', color: '2', children: [
      { text: 'MVP escolar (prioridade)', children: [
        { text: 'Conectar frontend ao backend (feito)' },
        { text: 'Busca inteligente no estoque (feito)' },
        { text: 'Controle de estoque no Mongo (feito)' },
        { text: 'Controle de validade com alertas' },
        { text: 'Pedido para distribuidora: demo de logistica (feito, so no navegador)' },
        { text: 'Assistente IA sobre os dados da farmacia (feito)' },
        { text: 'SNGPC: controlados -> ANVISA (PostgreSQL)' },
      ]},
      { text: 'Produto real (pos-banca)', children: [
        { text: 'Persistir Pedidos no banco (divida tecnica)' },
        { text: 'API real com distribuidora' },
        { text: 'Importar estoque via CSV' },
        { text: 'Importar NF-e (XML)' },
        { text: 'Outros fornecedores' },
        { text: 'Pagamento integrado' },
        { text: 'Rastreabilidade de psicotropicos por lote' },
        { text: 'Painel de alvaras e licencas' },
        { text: 'Relatorios para o CRF' },
      ]},
    ]},
    { text: '**SNGPC (planejado)**', color: '1', children: [
      { text: 'Nao e API de tempo real: farmacia gera XML e envia periodicamente para a ANVISA' },
      { text: 'Campo listaPortaria344 no produto (A1/A2/B1/B2/C1...) define fluxo e relatorio' },
      { text: 'Venda de controlado precisa: lote, CRM medico, numero receita, CPF/RG comprador, endereco' },
      { text: 'Implementacao em 3 camadas', children: [
        { text: '1. Formularios de entrada/saida (Postgres)' },
        { text: '2. Gerador de XML no formato ANVISA' },
        { text: '3. Envio automatico (ultimo; homologacao burocratica)' },
      ]},
      { text: 'Venda normal continua como esta; venda de controlado ganha documento separado' },
    ]},
    { text: '**Compliance (outros)**', color: '1', children: [
      { text: 'Controle de validade', children: [ { text: 'alertas de vencimento; vencido na prateleira e infracao grave' } ]},
      { text: 'NF-e XML', children: [ { text: 'entrada automatica de mercadoria por nota fiscal' } ]},
      { text: 'Alvaras e licencas', children: [ { text: 'painel de vencimento (sanitario, CRF, funcionamento)' } ]},
      { text: 'Relatorios CRF', children: [ { text: 'geracao automatica para o Conselho' } ]},
      { text: 'Rastreabilidade por lote', children: [ { text: 'facilita recall de psicotropicos' } ]},
    ]},
    { text: '**Base de medicamentos**', color: '3', children: [
      { text: 'Fonte: ANVISA (dados abertos)' },
      { text: '11.759 medicamentos (catalogo de busca)' },
      { text: 'Campos: nome, principio ativo, classe, empresa' },
      { text: 'Em memoria no Node (nao no Mongo)' },
      { text: 'Busca fuzzy via Fuse.js (tolera erro de digitacao)' },
      { text: 'Atualizacao: job semanal baixando CSV (planejado)' },
    ]},
    { text: '**Assistente IA (OpenRouter)**', color: '4', children: [
      { text: 'Chave fica so no backend; o front nunca a ve' },
      { text: 'Resumo automatico (texto pronto) no Dashboard e Relatorios' },
      { text: 'Tela Assistente: 1 pergunta por vez, sem contexto anterior' },
      { text: 'Historico das respostas so no navegador (localStorage)' },
      { text: 'Fluxo de 2 estagios (mais barato)', children: [
        { text: 'IA pequena planeja quais dados buscar' },
        { text: 'backend roda consultas escopadas por usuario' },
        { text: 'IA principal responde com os dados certos' },
      ]},
      { text: 'Seletor de escopo limita onde a IA enxerga (menos erro)' },
      { text: 'Fallback de modelos: troca de modelo se um falhar' },
    ]},
    { text: '**Pedidos (logistica distribuidora)**', color: '2', children: [
      { text: 'Demo de reposicao com o distribuidor (Eurofarma como exemplo)' },
      { text: 'Sugere quantidade a repor a partir do estoque minimo' },
      { text: 'Estagios do pedido: aguardando, confirmado, separacao, entregue' },
      { text: 'DIVIDA TECNICA: vive so no navegador (localStorage) - precisa persistir no banco' },
    ]},
    { text: '**Observabilidade & Monitoramento**', color: '4', children: [
      { text: 'Request-ID unico por requisicao (cabecalho X-Request-Id), propagado front->back' },
      { text: 'Logs estruturados em JSON (1 linha por evento); nivel via LOG_LEVEL' },
      { text: 'Erros com stack trace completo + contexto no log; nunca na resposta HTTP' },
      { text: '/api/health detalhado: ok, status, banco, uptime, memoria, versao' },
      { text: 'Metricas de performance: tempo (media/p95), memoria, CPU, contadores por status' },
      { text: 'Query logging com tempo no Mongoose + marca de query lenta' },
      { text: 'Cache em memoria com tracking de hit/miss' },
      { text: 'Alertas configuraveis por threshold com cooldown' },
      { text: 'Deploy health-gated no Render + rollback documentado' },
    ]},
    { text: '**Roadmap & Proximos passos**', color: '6', children: [
      { text: 'Imediato: controle de validade com alertas' },
      { text: 'Depois: SNGPC (maior trabalho, PostgreSQL Neon)' },
      { text: 'Depois: persistir Pedidos no banco (divida tecnica)' },
      { text: 'Validacao: mostrar para donos de farmacias reais (meses 3-4)' },
      { text: 'Banca (~6 meses): mostrar que a ideia funciona' },
      { text: 'Diferenciais', children: [
        { text: 'autenticacao nivel profissional' },
        { text: 'base real da ANVISA' },
        { text: 'compliance burocratico (SNGPC)' },
        { text: 'integracao com distribuidora' },
        { text: 'parceria Eurofarma (credibilidade)' },
      ]},
    ]},
  ],
};

// =================== MAPA B: como funciona (nao-tecnico) ===================
const easy = {
  text: '# auraFarma\n\nSistema para farmacias pequenas\ncuidarem do estoque, das vendas e da burocracia',
  children: [
    { text: '**O que e e pra quem**', color: '6', children: [
      { text: 'Para farmacias pequenas' },
      { text: 'Resolve a burocracia e a desorganizacao' },
      { text: 'E alugado por mensalidade (SaaS)' },
      { text: 'Integra pedidos com a distribuidora dentro do proprio sistema' },
      { text: 'Eurofarma: parceria escolar que da credibilidade ao projeto' },
    ]},
    { text: '**O que ja funciona hoje**', color: '4', children: [
      { text: '9 telas prontas' },
      { text: 'Entrar com usuario/senha ou com o Google' },
      { text: 'Senha guardada de forma segura' },
      { text: 'Estoque e vendas ficam salvos no servidor (banco), por farmacia' },
      { text: 'Busca em 11.7k remedios reais' },
      { text: 'Um assistente de IA que responde perguntas sobre a farmacia' },
      { text: 'Uma "tela de saude" que mostra se o sistema esta bem' },
    ]},
    { text: '**As telas**', color: '5', children: [
      { text: 'Dashboard', children: [ { text: 'visao geral do dia: resumos e grafico' } ]},
      { text: 'Estoque', children: [ { text: 'lista de remedios: buscar, adicionar, editar' } ]},
      { text: 'Nova venda (caixa)', children: [ { text: 'monta o carrinho; o estoque baixa sozinho' } ]},
      { text: 'Solicitados', children: [ { text: 'remedios que clientes pediram e faltam' } ]},
      { text: 'Pedidos', children: [ { text: 'pedir reposicao para a Eurofarma e acompanhar a entrega' } ]},
      { text: 'Historico', children: [ { text: 'todas as vendas ja feitas' } ]},
      { text: 'Contagem', children: [ { text: 'conferir a prateleira vs o sistema' } ]},
      { text: 'Relatorios', children: [ { text: 'analises do periodo' } ]},
      { text: 'Assistente IA', children: [ { text: 'pergunte e ele consulta seus dados pra responder' } ]},
    ]},
    { text: '**Busca inteligente de remedios**', color: '3', children: [
      { text: 'Catalogo real da ANVISA (11.7k remedios)' },
      { text: 'Aceita erro de digitacao', children: [ { text: "digitar 'amoxalina' acha 'AMOXICILINA'" } ]},
      { text: 'Acha por nome, principio ativo e categoria' },
      { text: 'Preenche o cadastro sozinho ao escolher' },
    ]},
    { text: '**Onde os dados ficam**', color: '2', children: [
      { text: 'Agora: no servidor (banco de dados), por farmacia' },
      { text: 'Carregam rapido numa unica chamada' },
      { text: 'Antes ficavam so no navegador' },
      { text: 'Cada conta enxerga so os seus dados' },
    ]},
    { text: '**O assistente de IA**', color: '4', children: [
      { text: 'Voce escolhe a area (estoque, vendas...) e faz uma pergunta' },
      { text: 'Ele olha so os seus dados daquela area pra responder' },
      { text: 'Responde uma pergunta por vez, sem lembrar das anteriores' },
      { text: 'As respostas ficam guardadas so no seu navegador' },
      { text: 'Tambem escreve um resumo do dia/semana/mes sozinho' },
    ]},
    { text: '**A burocracia que vai resolver**', color: '1', children: [
      { text: 'SNGPC: avisa a ANVISA sobre controlados automaticamente' },
      { text: 'Validade: avisa antes do remedio vencer' },
      { text: 'NF-e: lanca a mercadoria pela nota fiscal' },
      { text: 'Alvaras: avisa quando licencas vao vencer' },
      { text: 'Relatorios para o Conselho de Farmacia' },
    ]},
    { text: '**Login e seguranca**', color: '6', children: [
      { text: 'Cadastro: usuario, farmacia, e-mail e senha' },
      { text: 'Senha embaralhada (ninguem le a original)' },
      { text: 'Cracha seguro mantem voce logado' },
      { text: 'Opcao de entrar com o Google' },
    ]},
    { text: '**De olho na saude do sistema**', color: '4', children: [
      { text: 'Uma tela de saude diz se esta tudo bem (verde), meio ruim (amarelo) ou fora do ar (vermelho)' },
      { text: 'Cada pedido ao sistema ganha um numero de protocolo, pra achar problemas depois' },
      { text: 'O sistema anota tudo o que faz num registro organizado (os "logs")' },
      { text: 'Avisa sozinho quando algo sai do normal: lentidao, falta de memoria, muitos erros' },
      { text: 'Se uma atualizacao nasce com defeito, ele volta para a versao boa sozinho' },
    ]},
  ],
};

makeCanvas(full, 'obsidian/auraFarma - Mapa Mental.canvas');
idc = 0;
makeCanvas(easy, 'obsidian/auraFarma - Como Funciona (mapa mental).canvas');
