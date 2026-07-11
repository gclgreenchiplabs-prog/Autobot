async function postAction(action) {
  const response = await fetch(`/api/control/${action}`, { method: 'POST' });
  return response.json();
}

async function refreshState() {
  const response = await fetch('/api/dashboard-state');
  const state = await response.json();
  document.getElementById('state').textContent = JSON.stringify(state, null, 2);
}

document.querySelectorAll('[data-action]').forEach((button) => {
  button.addEventListener('click', async () => {
    const action = button.getAttribute('data-action');
    await postAction(action);
    await refreshState();
  });
});

refreshState();
