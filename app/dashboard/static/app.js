function formatMoney(value) {
  if (value === null || value === undefined || value === '') return 'N/A';
  const number = Number(value);
  const sign = number > 0 ? '+' : '';
  return `${sign}Rs ${number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPct(value) {
  if (value === null || value === undefined || value === '') return 'N/A';
  const number = Number(value);
  const sign = number > 0 ? '+' : '';
  return `${sign}${number.toFixed(2)}%`;
}

function formatMaybe(value) {
  if (value === null || value === undefined || value === '') return 'N/A';
  return value;
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
  const endpointMap = {
    'send-status-now': '/api/control/send-status-now',
    'import-instruments': '/api/control/import-instruments',
  };
  const endpoint = endpointMap[action] || `/api/control/${action}`;
  const options = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
  if (action === 'import-instruments') {
    options.body = JSON.stringify({ source: 'FIXTURE' });
  }
  const response = await fetch(endpoint, options);
  return response.json();
}

function renderSummaryGrid(targetId, summary) {
  renderKeyValue(targetId, Object.entries(summary || {}).map(([key, value]) => [key.replace(/_/g, ' '), value]));
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

  renderKeyValue('universe-summary', [
    ['Total Companies', state.universe_summary?.total_companies],
    ['Total Instruments', state.universe_summary?.total_instruments],
    ['NSE Count', state.universe_summary?.nse_count],
    ['BSE Count', state.universe_summary?.bse_count],
    ['F&O Count', state.universe_summary?.fno_count],
    ['Conflict Count', state.universe_summary?.conflict_count],
    ['Last Import', formatMaybe(state.universe_summary?.last_import_time)],
    ['Import Source', formatMaybe(state.universe_summary?.import_source)],
  ]);

  renderCards(
    'broker-mapping-summary',
    Object.entries(state.broker_mapping_summary || {}),
    ([broker, stats]) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${broker.toUpperCase()}</strong>
          <span>ready ${stats.READY || 0} | partial ${stats.PARTIAL || 0}</span>
        </div>
        <div class="item-grid">
          <span>Missing ${stats.MISSING || 0}</span>
          <span>Conflict ${stats.CONFLICT || 0}</span>
          <span>Stale ${stats.STALE || 0}</span>
          <span>Not Configured ${stats.NOT_CONFIGURED || 0}</span>
        </div>
      </article>
    `,
    'No broker mapping stats.'
  );

  renderSummaryGrid('data-quality-summary', state.data_quality_summary);
  renderSummaryGrid('liquidity-summary', state.liquidity_summary);
  renderSummaryGrid('stale-data-summary', state.stale_data_summary);

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

  renderCards(
    'instrument-table',
    state.instrument_table,
    (instrument) => `
      <article class="table-row">
        <div><strong>${instrument.company_name}</strong><span>${instrument.symbol}</span></div>
        <div>${instrument.exchange} | ${instrument.segment} | ${instrument.instrument_type}</div>
        <div>F&O ${instrument.fno_eligible ? 'YES' : 'NO'} | Lot ${instrument.lot_size}</div>
        <div>Preferred ${instrument.preferred_exchange || 'N/A'}</div>
        <div>Liquidity ${instrument.liquidity_score || 0} (${instrument.liquidity_class || 'N/A'})</div>
        <div>Quality ${instrument.quality_class || 'N/A'} | Mapping ${instrument.staleness_state || 'N/A'}</div>
        <div>Updated ${instrument.quote_timestamp_utc || instrument.last_updated}</div>
      </article>
    `,
    'No instruments loaded.'
  );

  renderCards(
    'conflicts',
    state.conflicts,
    (conflict) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${conflict.conflict_type}</strong>
          <span>${conflict.resolution_status}</span>
        </div>
        <div class="item-grid">
          <span>Symbol ${conflict.symbol || 'N/A'}</span>
          <span>ISIN ${conflict.isin || 'N/A'}</span>
          <span>Brokers ${(conflict.brokers_involved || []).join(', ') || 'N/A'}</span>
        </div>
        <p>${conflict.reason}</p>
      </article>
    `,
    'No conflicts detected.'
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
