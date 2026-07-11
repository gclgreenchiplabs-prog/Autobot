async function postAction(action) {
  const response = await fetch(`/api/control/${action}`, { method: 'POST' });
  return response.json();
}

async function refreshState() {
  const response = await fetch('/api/dashboard-state');
  const state = await response.json();
  document.getElementById('state').textContent = JSON.stringify(state, null, 2);
  document.getElementById('health').textContent = JSON.stringify(state.health, null, 2);
  document.getElementById('database').textContent = JSON.stringify({ database_path: state.database_path || 'data/market_move.db', ready: true }, null, 2);
  document.getElementById('session').textContent = JSON.stringify(state.session, null, 2);
  document.getElementById('tasks').textContent = JSON.stringify(state.tasks, null, 2);
  document.getElementById('services').textContent = JSON.stringify({ readiness: state.health?.status || 'NOT_READY' }, null, 2);
  document.getElementById('events').textContent = JSON.stringify(state.events || [], null, 2);
}

document.querySelectorAll('[data-action]').forEach((button) => {
  button.addEventListener('click', async () => {
    const action = button.getAttribute('data-action');
    await postAction(action);
    await refreshState();
  });
});

refreshState();
