const API = 'https://agronota-backend.onrender.com';

let token = localStorage.getItem('agronota_token');
let usuario = JSON.parse(localStorage.getItem('agronota_usuario') || 'null');
let operacaoSelecionada = null;
let calculoAtual = null;

document.addEventListener('DOMContentLoaded', () => {
  if (token && usuario) mostrarDashboard();
  document.getElementById('nota-quantidade').addEventListener('input', calcularTotal);
  document.getElementById('nota-valor').addEventListener('input', calcularTotal);
  document.getElementById('login-senha').addEventListener('keydown', e => { if (e.key === 'Enter') fazerLogin(); });
  document.getElementById('btn-entrar').addEventListener('click', fazerLogin);
  document.getElementById('btn-sair').addEventListener('click', sair);
});

function mostrarTela(id) {
  document.querySelectorAll('.tela').forEach(t => t.classList.remove('ativa'));
  document.getElementById(id).classList.add('ativa');
}

function mostrarErro(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.add('visivel');
  setTimeout(() => el.classList.remove('visivel'), 5000);
}

function mostrarSucesso(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.add('visivel');
  setTimeout(() => el.classList.remove('visivel'), 6000);
}

function formatarMoeda(valor) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor);
}

function formatarData(iso) {
  return new Date(iso).toLocaleDateString('pt-BR');
}

async function req(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(API + path, { ...options, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Erro na requisição');
  return data;
}

async function fazerLogin() {
  const email = document.getElementById('login-email').value.trim();
  const senha = document.getElementById('login-senha').value;
  const btn = document.getElementById('btn-entrar');
  if (!email || !senha) return mostrarErro('login-erro', 'Preencha e-mail e senha');
  btn.disabled = true;
  btn.textContent = 'Entrando...';
  try {
    const data = await req('/auth/login', { method: 'POST', body: JSON.stringify({ email, senha }) });
    token = data.access_token;
    usuario = data.usuario;
    localStorage.setItem('agronota_token', token);
    localStorage.setItem('agronota_usuario', JSON.stringify(usuario));
    mostrarDashboard();
  } catch (e) {
    mostrarErro('login-erro', e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Entrar';
  }
}

async function mostrarDashboard() {
  mostrarTela('tela-dashboard');
  document.getElementById('navbar-nome').textContent = usuario?.nome || usuario?.email || '';
  await Promise.all([carregarClientes(), carregarProdutos(), carregarHistorico()]);
}

function sair() {
  token = null;
  usuario = null;
  localStorage.removeItem('agronota_token');
  localStorage.removeItem('agronota_usuario');
  mostrarTela('tela-login');
}

function selecionarOperacao(tipo) {
  operacaoSelecionada = tipo;
  document.getElementById('card-interna').classList.toggle('selecionado', tipo === 'interna');
  document.getElementById('card-interestadual').classList.toggle('selecionado', tipo === 'interestadual');
  const form = document.getElementById('form-nota');
  form.classList.add('visivel');
  document.getElementById('form-titulo').textContent =
    tipo === 'interna' ? '🌾 Nota — Dentro do Estado (CFOP 5.105)' : '🚛 Nota — Para Outro Estado (CFOP 6.105)';
  limparCalculo();
}

async function carregarClientes() {
  try {
    const clientes = await req('/clientes/');
    const sel = document.getElementById('nota-cliente');
    sel.innerHTML = '<option value="">Selecione um cliente...</option>';
    clientes.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = `${c.nome} — ${c.uf}`;
      sel.appendChild(opt);
    });
  } catch (e) { console.error('Erro ao carregar clientes:', e); }
}

async function carregarProdutos() {
  try {
    const produtos = await req('/produtos/');
    const sel = document.getElementById('nota-produto');
    sel.innerHTML = '<option value="">Selecione um produto...</option>';
    produtos.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = `${p.nome} — ${p.unidade}`;
      sel.appendChild(opt);
    });
  } catch (e) { console.error('Erro ao carregar produtos:', e); }
}

function calcularTotal() {
  const qtd = parseFloat(document.getElementById('nota-quantidade').value) || 0;
  const val = parseFloat(document.getElementById('nota-valor').value) || 0;
  document.getElementById('total-display').textContent = formatarMoeda(qtd * val);
  limparCalculo();
}

function toggleFiscal() {
  const painel = document.getElementById('painel-fiscal');
  const btn = document.getElementById('toggle-fiscal');
  const visivel = painel.classList.toggle('visivel');
  btn.textContent = visivel ? '▲ ocultar detalhes fiscais' : '▼ ver detalhes fiscais';
}

async function calcularNota() {
  const cliente_id = document.getElementById('nota-cliente').value;
  const produto_id = document.getElementById('nota-produto').value;
  const quantidade = parseFloat(document.getElementById('nota-quantidade').value);
  const valor_unitario = parseFloat(document.getElementById('nota-valor').value);
  if (!cliente_id) return mostrarErro('nota-erro', 'Selecione um cliente');
  if (!produto_id) return mostrarErro('nota-erro', 'Selecione um produto');
  if (!quantidade || quantidade <= 0) return mostrarErro('nota-erro', 'Informe uma quantidade válida');
  if (!valor_unitario || valor_unitario <= 0) return mostrarErro('nota-erro', 'Informe um valor válido');
  const btn = document.getElementById('btn-calcular');
  btn.disabled = true;
  btn.textContent = 'Calculando...';
  try {
    const data = await req('/notas/calcular', {
      method: 'POST',
      body: JSON.stringify({ cliente_id, produto_id, quantidade, valor_unitario })
    });
    calculoAtual = data;
    document.getElementById('f-cfop').textContent = data.cfop;
    document.getElementById('f-icms').textContent = formatarMoeda(data.icms_valor);
    document.getElementById('f-difal').textContent = data.difal_valor > 0 ? formatarMoeda(data.difal_valor) : 'N/A';
    document.getElementById('painel-fiscal').classList.add('visivel');
    document.getElementById('toggle-fiscal').textContent = '▲ ocultar detalhes fiscais';
    const alertaGnre = document.getElementById('alerta-gnre');
    if (data.aviso_gnre) {
      document.getElementById('alerta-gnre-texto').textContent = data.aviso_gnre;
      alertaGnre.classList.add('visivel');
    } else {
      alertaGnre.classList.remove('visivel');
    }
    document.getElementById('btn-emitir').style.display = 'block';
    btn.textContent = 'Recalcular';
  } catch (e) {
    mostrarErro('nota-erro', e.message);
  } finally {
    btn.disabled = false;
    if (btn.textContent === 'Calculando...') btn.textContent = 'Calcular impostos';
  }
}

async function emitirNota() {
  if (!calculoAtual) return;
  const btn = document.getElementById('btn-emitir');
  btn.disabled = true;
  btn.textContent = 'Emitindo...';
  const cliente_id = document.getElementById('nota-cliente').value;
  const produto_id = document.getElementById('nota-produto').value;
  const quantidade = parseFloat(document.getElementById('nota-quantidade').value);
  const valor_unitario = parseFloat(document.getElementById('nota-valor').value);
  const gnre_ciente = calculoAtual.gnre_necessaria;
  try {
    const data = await req(`/notas/emitir?gnre_ciente=${gnre_ciente}`, {
      method: 'POST',
      body: JSON.stringify({ cliente_id, produto_id, quantidade, valor_unitario })
    });
    mostrarSucesso('nota-sucesso', `✅ Nota nº ${data.nota.numero} registrada com sucesso!`);
    limparForm();
    await carregarHistorico();
  } catch (e) {
    mostrarErro('nota-erro', e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Emitir Nota Fiscal →';
  }
}

async function carregarHistorico() {
  try {
    const notas = await req('/notas/');
    const container = document.getElementById('historico-items');
    if (!notas.length) {
      container.innerHTML = '<p style="color: var(--texto-claro); font-size: 0.875rem;">Nenhuma nota emitida ainda.</p>';
      return;
    }
    container.innerHTML = notas.slice(0, 10).map(n => `
      <div class="nota-item">
        <div class="nota-info">
          <div class="nota-num">NF-e nº ${String(n.numero).padStart(6, '0')} · ${n.cfop}</div>
          <div class="nota-cliente">${n.clientes?.nome || 'Cliente'} — ${n.clientes?.uf || ''}</div>
          <div class="nota-data">${formatarData(n.criado_em)}</div>
        </div>
        <div style="text-align:right">
          <div class="nota-valor">${formatarMoeda(n.valor_total)}</div>
          <span class="badge-status badge-${n.status}">${n.status}</span>
        </div>
      </div>
    `).join('');
  } catch (e) { console.error('Erro ao carregar histórico:', e); }
}

function limparCalculo() {
  calculoAtual = null;
  document.getElementById('btn-emitir').style.display = 'none';
  document.getElementById('painel-fiscal').classList.remove('visivel');
  document.getElementById('alerta-gnre').classList.remove('visivel');
}

function limparForm() {
  document.getElementById('nota-cliente').value = '';
  document.getElementById('nota-produto').value = '';
  document.getElementById('nota-quantidade').value = '';
  document.getElementById('nota-valor').value = '';
  document.getElementById('total-display').textContent = 'R$ 0,00';
  document.getElementById('btn-calcular').textContent = 'Calcular impostos';
  limparCalculo();
}

// ─── MODAL CLIENTE ────────────────────────────────────────────
function abrirModalCliente() {
  document.getElementById('modal-cliente').style.display = 'flex';
}

function fecharModalCliente() {
  document.getElementById('modal-cliente').style.display = 'none';
  ['cli-cpf','cli-nome','cli-cidade','cli-ie'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('cli-uf').value = 'GO';
  document.getElementById('cli-contribuinte').checked = false;
  document.getElementById('cli-erro').classList.remove('visivel');
}

async function salvarCliente() {
  const cpf_cnpj = document.getElementById('cli-cpf').value.trim();
  const nome = document.getElementById('cli-nome').value.trim();
  const uf = document.getElementById('cli-uf').value;
  const cidade = document.getElementById('cli-cidade').value.trim();
  const inscricao_estadual = document.getElementById('cli-ie').value.trim();
  const is_contribuinte = document.getElementById('cli-contribuinte').checked;
  if (!cpf_cnpj) return mostrarErro('cli-erro', 'Informe o CPF ou CNPJ');
  if (!nome) return mostrarErro('cli-erro', 'Informe o nome');
  if (!uf) return mostrarErro('cli-erro', 'Selecione o estado');
  if (!cidade) return mostrarErro('cli-erro', 'Informe a cidade');
  try {
    await req('/clientes/', { method: 'POST', body: JSON.stringify({ cpf_cnpj, nome, uf, cidade, inscricao_estadual, is_contribuinte }) });
    await carregarClientes();
    fecharModalCliente();
  } catch(e) { mostrarErro('cli-erro', e.message); }
}

// ─── MODAL PRODUTO ────────────────────────────────────────────
function abrirModalProduto() {
  document.getElementById('modal-produto').style.display = 'flex';
}

function fecharModalProduto() {
  document.getElementById('modal-produto').style.display = 'none';
  ['pro-nome','pro-ncm','pro-valor'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('pro-beneficio').checked = false;
  document.getElementById('pro-erro').classList.remove('visivel');
}

async function salvarProduto() {
  const nome = document.getElementById('pro-nome').value.trim();
  const ncm = document.getElementById('pro-ncm').value.trim().replace(/\D/g,'');
  const unidade = document.getElementById('pro-unidade').value;
  const valor_unitario = parseFloat(document.getElementById('pro-valor').value) || null;
  const tem_beneficio_fiscal = document.getElementById('pro-beneficio').checked;
  if (!nome) return mostrarErro('pro-erro', 'Informe o nome do produto');
  if (!ncm || ncm.length !== 8) return mostrarErro('pro-erro', 'NCM deve ter 8 dígitos');
  try {
    await req('/produtos/', { method: 'POST', body: JSON.stringify({ nome, ncm, unidade, valor_unitario, tem_beneficio_fiscal }) });
    await carregarProdutos();
    fecharModalProduto();
  } catch(e) { mostrarErro('pro-erro', e.message); }
}