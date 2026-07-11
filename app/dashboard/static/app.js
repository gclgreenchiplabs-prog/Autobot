function formatMoney(value) {
  if (value === null || value === undefined || value === '') return 'N/A';
  const number = Number(value);
  const sign = number > 0 ? '+' : '';
  return `${sign}₹${number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPct(value) {
  if (value === null || value === undefined || value === '') return 'N/A';
  const number = Number(value);
  const sign = number > 0 ? '+' : '';
  return `${sign}${number.toFixed(2)}%`;
}

function renderKeyValue(targetId, entries) {
  const target = document.getElementById(targetId);
  target.innerHTML = entries.map(([label, value]) => `
    <div class="kv-row">
      <span>${label}</span>
      <strong>${value ?? 'N/A'}</strong>
    </div>
  `).join('');
}

function renderCards(targetId, items, renderItem, emptyMessage) {
  const target = document.getElementById(targetId);
  if (!items || items.length === 0) {
    target.innerHTML = `<div class="empty-state">${emptyMessage}</div>`;
    return;
  }
  target.innerHTML = items.map(renderItem).join('');
}

async function postAction(action) {
  const endpoint = action === 'send-status-now' ? '/api/control/send-status-now' : `/api/control/${action}`;
  const response = await fetch(endpoint, { method: 'POST' });
  return response.json();
}

async function refreshState() {
  const response = await fetch('/api/dashboard-state');
  const state = await response.json();

  document.getElementById('hero-status').textContent =
    `${state.lifecycle?.status || 'initialized'} | ${state.session?.session_state || 'UNKNOWN'} | ${state.health?.status || 'NOT_READY'}`;

  renderKeyValue('account-summary', [
    ['Account Equity', formatMoney(state.account_summary?.account_equity)],
    ['Capital Used', formatMoney(state.account_summary?.capital_used_day)],
    ['Capital Available', formatMoney(state.account_summary?.capital_available)],
    ['Realized P&L', formatMoney(state.account_summary?.realized_pnl)],
    ['Unrealized P&L', formatMoney(state.account_summary?.unrealized_pnl)],
    ['Total Day P&L', formatMoney(state.account_summary?.total_day_pnl)],
  ]);

  renderKeyValue('system-overview', [
    ['Execution Mode', state.account_summary?.execution_mode],
    ['Primary Broker', state.account_summary?.configured_primary_broker],
    ['Active Broker', state.account_summary?.active_execution_broker],
    ['Standby Broker', state.account_summary?.standby_broker],
    ['Session', state.session?.session_state],
    ['Database', state.database_path],
  ]);

  renderCards(
    'open-positions',
    state.open_positions,
    (position) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${position.symbol}</strong>
          <span>${position.option_type || position.instrument_type || 'N/A'} | ${position.expiry || 'N/A'}</span>
        </div>
        <div class="item-grid">
          <span>Entry ${formatMoney(position.entry_price)}</span>
          <span>Current ${formatMoney(position.current_price)}</span>
          <span>HWM ${formatMoney(position.highest_price)}</span>
          <span>SL/TSL ${formatMoney(position.current_stop)}</span>
          <span>T1 ${position.t1_status}</span>
          <span>T2 ${position.t2_status}</span>
          <span>T3 ${position.t3_status}</span>
          <span>Next ${formatMoney(position.next_predicted_target)}</span>
          <span>P&L ${formatMoney(position.current_pnl)} (${formatPct(position.current_pnl_pct)})</span>
          <span>Duration ${position.hold_duration_seconds}s</span>
        </div>
        <p>${position.hold_reason}</p>
      </article>
    `,
    'No open positions.'
  );

  renderCards(
    'recently-exited',
    state.recently_exited,
    (trade) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${trade.symbol}</strong>
          <span>${trade.expiry || 'N/A'}</span>
        </div>
        <div class="item-grid">
          <span>Entry ${formatMoney(trade.entry_price)}</span>
          <span>Exit ${formatMoney(trade.exit_price)}</span>
          <span>Holding ${trade.hold_duration_seconds}s</span>
          <span>Exit Reason ${trade.exit_reason || 'N/A'}</span>
          <span>Net P&L ${formatMoney(trade.total_pnl)}</span>
          <span>Capital Released ${formatMoney(trade.capital_released)}</span>
        </div>
      </article>
    `,
    'No recently exited positions.'
  );

  renderCards(
    'notifications',
    state.notifications,
    (notification) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${notification.notification_type}</strong>
          <span>${notification.timestamp_ist}</span>
        </div>
        <div class="item-grid">
          <span>Severity ${notification.severity}</span>
          <span>Delivery ${notification.delivery_status}</span>
        </div>
        <p>${notification.title}</p>
        <p>${notification.summary}</p>
      </article>
    `,
    'No notifications yet.'
  );

  renderCards(
    'detected-events',
    state.events,
    (event) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${event.event_type || 'EVENT'}</strong>
          <span>${event.source || 'unknown source'}</span>
        </div>
        <div class="item-grid">
          <span>Symbol ${event.symbol || 'N/A'}</span>
          <span>Severity ${event.severity || 'INFO'}</span>
          <span>Action ${event.action_taken || 'N/A'}</span>
        </div>
        <p>${event.reason || event.description || 'No details provided.'}</p>
      </article>
    `,
    'No detected events.'
  );

  document.getElementById('tasks').textContent = JSON.stringify(state.tasks, null, 2);
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
