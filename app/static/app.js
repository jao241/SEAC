const messages = document.querySelector('#messages');
const input = document.querySelector('#input');
const dialog = document.querySelector('#dialog');
const form = document.querySelector('#action-form');
const fields = document.querySelector('#fields');
const review = document.querySelector('#review');
const error = document.querySelector('#form-error');
const submit = document.querySelector('#submit');
let history = [];
let action = '';
let token = null;
let busy = false;

function message(role, text, extra = '') {
  document.querySelector('#welcome')?.remove();
  const row = document.createElement('div');
  row.className = 'message ' + role;
  const badge = document.createElement('span');
  badge.className = 'avatar';
  badge.textContent = role === 'assistant' ? '✳' : '•';
  const body = document.createElement('div');
  const label = document.createElement('small');
  label.textContent = role === 'assistant' ? 'SIMPLIFICA' : 'VOCÊ';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (role === 'assistant') {
    const parts = text.split(/(\*\*[^*\n]+\*\*)/g);
    for (const part of parts) {
      if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        const strong = document.createElement('strong');
        strong.textContent = part.slice(2, -2).trim();
        bubble.append(strong);
      } else {
        bubble.append(document.createTextNode(part));
      }
    }
  } else {
    bubble.textContent = text;
  }
  body.append(label, bubble);
  if (extra) {
    const origin = document.createElement('small');
    origin.className = 'origin';
    origin.textContent = extra;
    body.append(origin);
  }
  row.append(badge, body);
  messages.append(row);
  messages.scrollTop = messages.scrollHeight;
}

async function post(url, data) {
  const response = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const json = await response.json();
  if (!response.ok) throw new Error(json.detail || 'Não foi possível concluir a operação.');
  return json;
}

async function send(text) {
  if (busy || !text.trim()) return;
  busy = true;
  input.disabled = true;
  document.querySelector('.send').disabled = true;
  message('user', text);
  const status = document.createElement('div');
  status.className = 'thinking';
  status.textContent = 'Assistente está respondendo…';
  messages.append(status);
  try {
    const result = await post('/api/chat', {mensagem:text, historico:history.slice(-12)});
    status.remove();
    const origens = {
      llm: 'Origem: LLM',
      cache: 'Origem: cache semântico',
      mcp: 'Origem: MCP'
    };
    message('assistant', result.resposta, origens[result.origem] || '');
    history.push({papel:'usuario', texto:text}, {papel:'assistente', texto:result.resposta});
    if (result.confirmacao) showConfirmation(result.confirmacao);
  } catch (e) {
    status.remove();
    message('assistant', e.message);
  } finally {
    busy = false;
    input.disabled = false;
    document.querySelector('.send').disabled = false;
    input.focus();
  }
}

function showConfirmation(proposal) {
  const container = document.createElement('div');
  container.className = 'chat-confirmation';
  const summary = document.createElement('p');
  summary.textContent = proposal.resumo;
  const confirm = document.createElement('button');
  confirm.className = 'primary';
  confirm.textContent = 'Confirmar';
  const cancelButton = document.createElement('button');
  cancelButton.className = 'secondary';
  cancelButton.textContent = 'Cancelar';
  const feedback = document.createElement('p');
  feedback.className = 'error';
  container.append(summary, confirm, cancelButton, feedback);
  messages.append(container);
  messages.scrollTop = messages.scrollHeight;
  confirm.onclick = async () => {
    confirm.disabled = true;
    cancelButton.disabled = true;
    try {
      const result = (await post('/api/confirmar', {token:proposal.token})).resultado;
      if (!result.ok) throw new Error(result.erro || 'Operação não concluída.');
      const text = result.protocolo
        ? `Solicitação registrada. Protocolo: ${result.protocolo}\nServiço: ${result.servico}\nLocal: ${result.local}\nEstado: ${result.estado}`
        : `Cadastro ${result.existente ? 'existente' : 'criado'} para ${result.nome}. Código: ${result.codigo}.`;
      container.remove();
      message('assistant', text);
      history.push({papel:'assistente', texto:text});
    } catch (e) {
      feedback.textContent = e.message;
      confirm.disabled = false;
      cancelButton.disabled = false;
    }
  };
  cancelButton.onclick = async () => {
    confirm.disabled = true;
    cancelButton.disabled = true;
    try {
      await post('/api/cancelar', {token:proposal.token});
      container.remove();
      const text = 'Operação cancelada.';
      message('assistant', text);
      history.push({papel:'assistente', texto:text});
    } catch (e) {
      feedback.textContent = e.message;
      confirm.disabled = false;
      cancelButton.disabled = false;
    }
  };
}

input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && !e.repeat) {
    e.preventDefault();
    if (!busy && input.value.trim()) {
      document.querySelector('#chat-form').requestSubmit();
    }
  }
});

document.querySelector('#chat-form').addEventListener('submit', e => {
  e.preventDefault();
  const text = input.value.trim();
  input.value = '';
  send(text);
});
document.querySelector('#reset').addEventListener('click', () => {
  if (busy) return;
  history = [];
  messages.innerHTML = '';
  message('assistant', 'Olá! Como posso ajudar você hoje?');
});
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => send(button.dataset.prompt)));

const templates = {
  cadastro: ['Criar cadastro', '<label>Nome fictício<input name="nome" required minlength="2" maxlength="120" placeholder="Ex.: Ana Exemplo"></label><label>Identificador fictício<input name="identificador" required minlength="2" maxlength="60" placeholder="Ex.: pessoa-001"></label>'],
  solicitacao: ['Nova solicitação', '<label>Código de cadastro<input name="cidadao" required placeholder="CID-..."></label><label>Serviço<select name="servico" required><option value="">Selecione um serviço</option></select></label><label>Local fictício<input name="local" required minlength="2" maxlength="120" placeholder="Ex.: Praça das Nuvens"></label>'],
  consulta: ['Consultar protocolo', '<label>Protocolo<input name="protocolo" required placeholder="DEMO-..."></label>']
};
async function openAction(type) {
  action = type; token = null;
  error.textContent = '';
  review.hidden = true;
  fields.hidden = false;
  submit.textContent = type === 'consulta' ? 'Consultar →' : 'Continuar →';
  document.querySelector('#dialog-title').textContent = templates[type][0];
  fields.innerHTML = templates[type][1];
  dialog.showModal();
  if (type === 'solicitacao') {
    try {
      const response = await fetch('/api/servicos');
      if (!response.ok) throw new Error();
      const services = await response.json();
      const select = fields.querySelector('select');
      services.forEach(service => select.add(new Option(service.nome, service.codigo)));
    } catch {
      error.textContent = 'Não foi possível carregar os serviços.';
    }
  }
}
document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => openAction(button.dataset.action)));
async function cancel() {
  if (token) await post('/api/cancelar', {token}).catch(() => {});
  token = null;
  dialog.close();
}
document.querySelector('#close').onclick = cancel;
document.querySelector('#cancel').onclick = cancel;
dialog.addEventListener('cancel', e => { e.preventDefault(); cancel(); });
form.addEventListener('submit', async e => {
  e.preventDefault();
  error.textContent = '';
  submit.disabled = true;
  try {
    if (token) {
      const result = (await post('/api/confirmar', {token})).resultado;
      if (!result.ok) throw new Error(result.erro || 'Operação não concluída.');
      token = null;
      dialog.close();
      const text = action === 'cadastro'
        ? `Cadastro ${result.existente ? 'existente' : 'criado'} para ${result.nome}. Código: ${result.codigo}.`
        : `Solicitação registrada. Protocolo: ${result.protocolo}\nServiço: ${result.servico}\nLocal: ${result.local}\nEstado: ${result.estado}`;
      message('assistant', text);
    } else {
      const result = await post('/api/acao', {tipo:action, dados:Object.fromEntries(new FormData(form))});
      if (action === 'consulta') {
        if (!result.resultado.ok) throw new Error(result.resultado.erro);
        const r = result.resultado;
        dialog.close();
        message('assistant', `Protocolo: ${r.protocolo}\nServiço: ${r.servico}\nLocal: ${r.local}\nEstado: ${r.estado}`);
      } else {
        token = result.token;
        fields.hidden = true;
        review.hidden = false;
        review.textContent = result.resumo;
        submit.textContent = 'Confirmar →';
      }
    }
  } catch (e) { error.textContent = e.message; }
  finally { submit.disabled = false; }
});
