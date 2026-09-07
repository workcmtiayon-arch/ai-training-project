const page = document.body;
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
const taskList = document.querySelector('#task-list');
const taskStatus = document.querySelector('#task-status');
const priorityLabels = {high: 'Haute', medium: 'Moyenne', low: 'Basse'};
const priorityClasses = {high: 'bg-orange-50 text-orange-700', medium: 'bg-blue-50 text-blue-700', low: 'bg-slate-100 text-slate-600'};

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken, ...(options.headers || {})},
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Une erreur est survenue.');
  return data;
}

function renderTasks(tasks) {
  taskList.replaceChildren();
  if (!tasks.length) {
    taskList.innerHTML = '<p class="p-3 text-sm text-slate-400">Aucune tâche pour le moment.</p>';
    return;
  }
  tasks.forEach(task => {
    const card = document.createElement('article');
    card.className = 'rounded-xl border border-blue-100 p-3';
    const top = document.createElement('div');
    top.className = 'flex items-start gap-2';
    const title = document.createElement('h3');
    title.className = `flex-1 text-sm font-medium ${task.is_done ? 'text-slate-400 line-through' : 'text-slate-800'}`;
    title.textContent = task.title;
    const priority = document.createElement('span');
    priority.className = `rounded-full px-2 py-0.5 text-[10px] font-medium ${priorityClasses[task.priority]}`;
    priority.textContent = priorityLabels[task.priority];
    top.append(title, priority);
    card.appendChild(top);

    if (task.description) {
      const description = document.createElement('p');
      description.className = 'mt-1 text-xs text-slate-500';
      description.textContent = task.description;
      card.appendChild(description);
    }

    const actions = document.createElement('div');
    actions.className = 'mt-3 flex items-center justify-between';
    const state = document.createElement('span');
    state.className = `text-xs ${task.is_done ? 'text-emerald-600' : 'text-slate-400'}`;
    state.textContent = task.is_done ? '✓ Terminée' : 'À faire';
    actions.appendChild(state);

    const buttons = document.createElement('div');
    buttons.className = 'flex gap-1';
    [['✓', 'toggle'], ['✎', 'edit'], ['×', 'delete']].forEach(([label, action]) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.action = action;
      button.dataset.id = task.id;
      button.className = 'rounded px-2 py-1 text-xs text-blue-700 hover:bg-blue-50';
      button.textContent = label;
      button.title = action;
      buttons.appendChild(button);
    });
    actions.appendChild(buttons);
    card.appendChild(actions);
    taskList.appendChild(card);
  });
}

async function loadTasks() {
  try {
    const data = await api(page.dataset.taskListUrl);
    renderTasks(data.tasks);
  } catch (error) {
    taskList.innerHTML = `<p class="p-3 text-sm text-rose-500">${error.message}</p>`;
  }
}

document.querySelector('#refresh-tasks').addEventListener('click', loadTasks);

document.querySelector('#task-form').addEventListener('submit', async event => {
  event.preventDefault();
  taskStatus.textContent = '';
  try {
    await api(page.dataset.taskCreateUrl, {
      method: 'POST',
      body: JSON.stringify({
        title: document.querySelector('#task-title').value.trim(),
        description: document.querySelector('#task-description').value.trim(),
        priority: document.querySelector('#task-priority').value,
      }),
    });
    event.target.reset();
    await loadTasks();
  } catch (error) {
    taskStatus.textContent = error.message;
  }
});

taskList.addEventListener('click', async event => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const id = button.dataset.id;
  const action = button.dataset.action;
  try {
    if (action === 'delete' && !confirm('Supprimer cette tâche ?')) return;
    if (action === 'delete') await api(`/api/tasks/${id}/delete/`, {method: 'POST'});
    if (action === 'toggle') {
      const card = button.closest('article');
      const done = card.querySelector('span.text-emerald-600') !== null;
      await api(`/api/tasks/${id}/update/`, {method: 'POST', body: JSON.stringify({is_done: !done})});
    }
    if (action === 'edit') {
      const title = prompt('Nouveau titre :');
      if (title === null || !title.trim()) return;
      await api(`/api/tasks/${id}/update/`, {method: 'POST', body: JSON.stringify({title: title.trim()})});
    }
    await loadTasks();
  } catch (error) {
    taskStatus.textContent = error.message;
  }
});

const form = document.querySelector('#chat-form');
const input = document.querySelector('#message-input');
const messages = document.querySelector('#messages');
const sendButton = document.querySelector('#send-button');
const status = document.querySelector('#status');

function addMessage(role, content) {
  document.querySelector('#empty-state')?.remove();
  const row = document.createElement('div');
  row.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'}`;
  const bubble = document.createElement('div');
  bubble.className = `max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${role === 'user' ? 'rounded-br-sm bg-blue-600 text-white' : 'rounded-bl-sm bg-blue-50 text-slate-700'}`;
  bubble.textContent = content;
  row.appendChild(bubble);
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

async function streamChatMessage(content) {
  const response = await fetch(page.dataset.chatUrl, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
    body: JSON.stringify({message: content}),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || 'Une erreur est survenue.');
  }
  if (!response.body) throw new Error('Le navigateur ne supporte pas le flux de réponse.');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let assistantBubble = null;

  const processEvents = events => {
    events.forEach(event => {
      if (!event.trim()) return;
      const payload = JSON.parse(event.replace(/^data:\s*/, ''));
      if (payload.type === 'chunk') {
        if (!assistantBubble) assistantBubble = addMessage('assistant', '');
        assistantBubble.textContent += payload.content;
        messages.scrollTop = messages.scrollHeight;
      }
      if (payload.type === 'error') throw new Error(payload.error);
    });
  };

  while (true) {
    const {value, done} = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
    const events = buffer.split('\n\n');
    buffer = events.pop();
    processEvents(events);
    if (done) break;
  }
  if (buffer.trim()) processEvents([buffer]);
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const content = input.value.trim();
  if (!content) return;
  addMessage('user', content);
  input.value = '';
  sendButton.disabled = true;
  status.textContent = 'L’assistant réfléchit…';
  try {
    await streamChatMessage(content);
    await loadTasks();
  } catch (error) {
    status.textContent = error.message;
  } finally {
    sendButton.disabled = false;
    if (status.textContent === 'L’assistant réfléchit…') status.textContent = '';
    input.focus();
  }
});

input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

messages.scrollTop = messages.scrollHeight;
loadTasks();
