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
    'market-data-connect': '/api/control/market-data/connect',
    'market-data-disconnect': '/api/control/market-data/disconnect',
    'market-data-reconnect': '/api/control/market-data/reconnect',
    'market-data-start-fixture': '/api/control/market-data/start-fixture',
    'market-data-stop-fixture': '/api/control/market-data/stop-fixture',
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

  renderKeyValue('market-data-status', [
    ['Mode', formatMaybe(state.market_data_status?.market_data_mode)],
    ['Active Source', formatMaybe(state.market_data_status?.active_market_data_source)],
    ['Primary Broker', formatMaybe(state.market_data_status?.primary_market_data_broker)],
    ['Standby Broker', formatMaybe(state.market_data_status?.standby_market_data_broker)],
    ['Primary State', formatMaybe(state.market_data_status?.primary_connection_state)],
    ['Standby State', formatMaybe(state.market_data_status?.standby_connection_state)],
    ['Quote Cache', formatMaybe(state.market_data_status?.quote_cache_size)],
    ['Subscriptions', formatMaybe(state.market_data_status?.active_subscriptions)],
  ]);

  renderKeyValue('market-data-heartbeat', [
    ['Heartbeat State', formatMaybe(state.market_data_heartbeat?.state)],
    ['Last Socket', formatMaybe(state.market_data_heartbeat?.last_socket_message)],
    ['Last Valid Tick', formatMaybe(state.market_data_heartbeat?.last_valid_tick)],
    ['Last Reconnect', formatMaybe(state.market_data_heartbeat?.last_reconnect)],
    ['Reconnect Count', formatMaybe(state.market_data_heartbeat?.reconnect_count)],
    ['Stale Instruments', formatMaybe(state.market_data_heartbeat?.stale_instrument_count)],
  ]);

  renderCards(
    'broker-readiness',
    Object.entries(state.broker_readiness || {}),
    ([broker, snapshot]) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${broker.toUpperCase()}</strong>
          <span>${snapshot.status}</span>
        </div>
        <div class="item-grid">
          <span>Configuration ${snapshot.capabilities?.configuration?.status || 'N/A'}</span>
          <span>Market Data ${snapshot.capabilities?.market_data?.status || 'N/A'}</span>
          <span>Option Chain ${snapshot.capabilities?.option_chain?.status || 'N/A'}</span>
          <span>Execution ${snapshot.capabilities?.execution?.status || 'N/A'}</span>
          <span>Configured ${snapshot.configured ? 'YES' : 'NO'}</span>
          <span>Enabled ${snapshot.enabled ? 'YES' : 'NO'}</span>
          <span>Credentials ${snapshot.credentials_present ? 'PRESENT' : 'MISSING'}</span>
          <span>SDK ${snapshot.sdk_available ? 'AVAILABLE' : 'MISSING'}</span>
          <span>Authenticated ${snapshot.authenticated ? 'YES' : 'NO'}</span>
          <span>Connected ${snapshot.connected ? 'YES' : 'NO'}</span>
          <span>Static IP ${snapshot.static_ip_ready === null || snapshot.static_ip_ready === undefined ? 'N/A' : (snapshot.static_ip_ready ? 'READY' : 'NOT READY')}</span>
          <span>Active ${snapshot.active ? 'YES' : 'NO'}</span>
        </div>
        <p>${snapshot.reason || 'No details provided.'}</p>
      </article>
    `,
    'No broker readiness data.'
  );

  renderCards(
    'market-data-subscriptions',
    state.market_data_subscriptions,
    (subscription) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${subscription.instrument_id}</strong>
          <span>${subscription.source}</span>
        </div>
        <div class="item-grid">
          <span>Status ${subscription.status}</span>
          <span>Last Tick ${subscription.last_tick_at || 'N/A'}</span>
          <span>Retry ${subscription.retry_count}</span>
          <span>Consumers ${subscription.consumer_count}</span>
        </div>
      </article>
    `,
    'No active subscriptions.'
  );

  renderCards(
    'market-data-events',
    state.market_data_events,
    (event) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${event.event_type}</strong>
          <span>${event.source}</span>
        </div>
        <div class="item-grid">
          <span>Severity ${event.severity}</span>
          <span>Action ${event.action_taken || 'N/A'}</span>
        </div>
        <p>${event.reason || event.payload_json?.description || 'No details provided.'}</p>
      </article>
    `,
    'No market-data events.'
  );

  renderCards(
    'market-data-quotes',
    state.market_data_quotes,
    (quote) => `
      <article class="table-row">
        <div><strong>${quote.symbol || quote.instrument_id}</strong><span>${quote.source}</span></div>
        <div>${quote.data_mode} | ${quote.timestamp_ist || quote.timestamp_utc}</div>
        <div>LTP ${formatMoney(quote.ltp)}</div>
        <div>Bid ${formatMoney(quote.bid)} | Ask ${formatMoney(quote.ask)}</div>
        <div>Volume ${formatMaybe(quote.volume)}</div>
      </article>
    `,
    'No quotes in cache.'
  );

  renderCards(
    'market-data-candles',
    state.market_data_candles,
    (candle) => `
      <article class="table-row">
        <div><strong>${candle.instrument_id}</strong><span>${candle.timeframe}</span></div>
        <div>${candle.data_mode} | ${candle.complete ? 'COMPLETE' : 'INCOMPLETE'}</div>
        <div>O ${formatMoney(candle.open)} H ${formatMoney(candle.high)}</div>
        <div>L ${formatMoney(candle.low)} C ${formatMoney(candle.close)}</div>
        <div>Volume ${formatMaybe(candle.volume)}</div>
      </article>
    `,
    'No candles built yet.'
  );

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

  renderCards(
    'audit-timeline',
    state.audit_timeline,
    (entry) => `
      <article class="item-card">
        <div class="item-head">
          <strong>${entry.event_type}</strong>
          <span>${entry.module}</span>
        </div>
        <div class="item-grid">
          <span>Instrument ${entry.instrument_id || 'N/A'}</span>
          <span>Source ${entry.source || 'N/A'}</span>
        </div>
        <p>${entry.reason || 'No reason provided.'}</p>
      </article>
    `,
    'No audit timeline entries.'
  );

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
