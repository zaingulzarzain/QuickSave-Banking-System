/* ============================================================
   QuickSave — single-page banking app
   Talks to the FastAPI backend at /api/v1 (same origin).
   ============================================================ */

const API = '/api/v1';
const $ = (id) => document.getElementById(id);

const state = {
  user: null,
  accounts: [],
  summary: null,
  insights: null,
  insightsDays: 30,
  recent: [],
  tx: { accountId: 'all', type: '', search: '', limit: 10, offset: 0, items: [], total: 0 },
  transferLookup: null,
  admin: { stats: null, users: [], accounts: [], txns: [] },
};
let charts = {};
let chatHistory = [];
let chatBooted = false;

/* ------------------------------ helpers ------------------------------ */

const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const money = (n, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(Number(n || 0));

const parseUTC = (s) => {
  if (!s) return new Date();
  const str = String(s);
  return new Date(/z$/i.test(str) || /[+-]\d{2}:?\d{2}$/.test(str) ? str : str + 'Z');
};
const fmtDate = (s) => parseUTC(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const fmtDateTime = (s) => parseUTC(s).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
const timeAgo = (s) => {
  const mins = Math.max(0, Math.floor((Date.now() - parseUTC(s)) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return mins + 'm ago';
  const h = Math.floor(mins / 60);
  if (h < 24) return h + 'h ago';
  const d = Math.floor(h / 24);
  if (d < 30) return d + 'd ago';
  return fmtDate(s);
};

const CAT_ICON = {
  salary: '💰', income: '📥', rent: '🏠', groceries: '🛒', dining: '🍔',
  transport: '🚕', shopping: '🛍️', utilities: '💡', health: '🏥',
  entertainment: '🎬', transfer: '💸', savings: '🏦', general: '🧾',
};
const TXN_META = {
  deposit: { label: 'Deposit', dir: 1 }, withdrawal: { label: 'Withdrawal', dir: -1 },
  transfer_in: { label: 'Transfer in', dir: 1 }, transfer_out: { label: 'Transfer out', dir: -1 },
};
const miniMd = (s) =>
  esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

function toast(msg, kind = 'ok') {
  const el = document.createElement('div');
  el.className = `toast toast-${kind}`;
  el.innerHTML = `<span>${kind === 'ok' ? '✅' : kind === 'err' ? '⛔' : 'ℹ️'}</span><span>${esc(msg)}</span>`;
  $('toast-root').appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }, 3800);
}

async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth) {
    const t = localStorage.getItem('qs_token');
    if (t) headers['Authorization'] = 'Bearer ' + t;
  }
  const res = await fetch(API + path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  if (res.status === 401 && auth) { logout(true); throw new Error('Session expired — please sign in again.'); }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try { const d = await res.json(); if (d.detail) msg = typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail); } catch (e) { /* keep default */ }
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return res.json();
}

function copyText(text) {
  navigator.clipboard?.writeText(text).then(() => toast('Copied: ' + text, 'info')).catch(() => toast(text, 'info'));
}

function countUp(el, target, { prefix = '', suffix = '', decimals = 0, duration = 900 } = {}) {
  const start = performance.now();
  const step = (now) => {
    const p = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = prefix + (target * eased).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) + suffix;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/* ------------------------------ auth ------------------------------ */

function switchAuthTab(which) {
  const login = which === 'login';
  $('tab-login').classList.toggle('auth-tab-active', login);
  $('tab-register').classList.toggle('auth-tab-active', !login);
  $('form-login').classList.toggle('hidden', !login);
  $('form-register').classList.toggle('hidden', login);
}

async function doLogin(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  btn.disabled = true; btn.textContent = 'Signing in…';
  try {
    const data = await api('/auth/login', {
      method: 'POST', auth: false,
      body: { email: $('login-email').value.trim(), password: $('login-password').value },
    });
    localStorage.setItem('qs_token', data.access_token);
    state.user = data.user;
    toast(`Welcome back, ${data.user.full_name.split(' ')[0]}!`);
    enterApp();
  } catch (err) { toast(err.message, 'err'); btn.disabled = false; btn.textContent = 'Sign in →'; }
  return false;
}

async function doRegister(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  btn.disabled = true; btn.textContent = 'Creating account…';
  try {
    const data = await api('/auth/register', {
      method: 'POST', auth: false,
      body: { full_name: $('reg-name').value.trim(), email: $('reg-email').value.trim(), password: $('reg-password').value },
    });
    localStorage.setItem('qs_token', data.access_token);
    state.user = data.user;
    toast('Account created — $100 welcome bonus added! 🎉');
    enterApp();
  } catch (err) { toast(err.message, 'err'); btn.disabled = false; btn.textContent = 'Create account + claim $100 🎉'; }
  return false;
}

async function demoLogin(email, password) {
  $('login-email').value = email;
  $('login-password').value = password;
  switchAuthTab('login');
  toast('Signing in to demo…', 'info');
  try {
    const data = await api('/auth/login', { method: 'POST', auth: false, body: { email, password } });
    localStorage.setItem('qs_token', data.access_token);
    state.user = data.user;
    enterApp();
  } catch (err) { toast(err.message, 'err'); }
}

function logout(silent = false) {
  localStorage.removeItem('qs_token');
  Object.assign(state, { user: null, accounts: [], summary: null, insights: null, recent: [] });
  chatHistory = []; chatBooted = false;
  Object.values(charts).forEach((c) => c?.destroy()); charts = {};
  $('app').classList.add('hidden');
  $('ai-fab').classList.add('hidden');
  $('ai-panel').classList.add('hidden');
  $('auth-screen').classList.remove('hidden');
  if (location.hash) history.replaceState(null, '', location.pathname);
  if (!silent) toast('Signed out. See you soon!', 'info');
}

function enterApp() {
  $('auth-screen').classList.add('hidden');
  $('app').classList.remove('hidden');
  $('ai-fab').classList.remove('hidden');
  const u = state.user;
  $('user-name').textContent = u.full_name;
  $('user-email').textContent = u.email;
  $('user-avatar').textContent = (u.full_name || '?').trim()[0].toUpperCase();
  $('nav-admin').classList.toggle('hidden', !u.is_admin);
  fetchHealth();
  if (!location.hash) location.hash = '#/dashboard';
  renderRoute();
}

async function fetchHealth() {
  try {
    const h = await api('/health', { auth: false });
    $('ai-badge').textContent = h.llm_configured ? `✨ AI: ${h.ai_provider}` : '✨ AI: Local mode';
    $('ai-engine').textContent = h.llm_configured ? h.ai_provider : 'quicksave-local (offline)';
  } catch (e) { $('ai-badge').textContent = '✨ AI'; }
}

/* ------------------------------ router ------------------------------ */

const TITLES = { dashboard: 'Dashboard', accounts: 'Accounts', transactions: 'Transactions', transfer: 'Transfer money', insights: 'AI Insights', admin: 'Admin console' };

window.addEventListener('hashchange', renderRoute);

function toggleSidebar(open) {
  const sb = $('sidebar'), bd = $('sidebar-backdrop');
  const willOpen = open ?? !sb.classList.contains('open');
  sb.classList.toggle('open', willOpen);
  bd.classList.toggle('show', willOpen);
}

async function renderRoute() {
  if (!localStorage.getItem('qs_token')) return; // on auth screen
  const route = (location.hash.replace('#/', '') || 'dashboard').split('?')[0];
  if (route === 'admin' && !state.user?.is_admin) { location.hash = '#/dashboard'; return; }
  document.querySelectorAll('#nav .nav-link').forEach((a) => a.classList.toggle('active', a.dataset.route === route));
  $('page-title').textContent = TITLES[route] || 'QuickSave';
  toggleSidebar(false);
  const view = $('view');
  view.innerHTML = `<div class="space-y-4"><div class="skeleton h-28"></div><div class="skeleton h-64"></div></div>`;
  try {
    if (route === 'dashboard') await vDashboard(view);
    else if (route === 'accounts') await vAccounts(view);
    else if (route === 'transactions') await vTransactions(view);
    else if (route === 'transfer') await vTransfer(view);
    else if (route === 'insights') await vInsights(view);
    else if (route === 'admin') await vAdmin(view);
    else location.hash = '#/dashboard';
  } catch (err) { view.innerHTML = errorBox(err.message); }
  view.classList.remove('view-enter'); void view.offsetWidth; view.classList.add('view-enter');
  window.scrollTo({ top: 0 });
}

const errorBox = (msg) => `<div class="card p-8 text-center">
  <div class="text-4xl mb-3">😕</div><div class="font-bold text-lg">Something went wrong</div>
  <div class="text-sm text-slate-500 mt-1">${esc(msg)}</div>
  <button class="btn-ghost mt-4" onclick="renderRoute()">↻ Retry</button></div>`;

async function ensureAccounts() {
  if (!state.accounts.length) state.accounts = await api('/accounts');
  return state.accounts;
}

/* ------------------------------ dashboard ------------------------------ */

async function vDashboard(view) {
  const [summary, accounts, recent, insights] = await Promise.all([
    api('/users/me/summary'), api('/accounts'),
    api('/transactions/recent?limit=8'), api('/ai/insights?days=30'),
  ]);
  state.summary = summary; state.accounts = accounts; state.recent = recent; state.insights = insights;

  const firstName = esc(summary.user.full_name.split(' ')[0]);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  view.innerHTML = `
    <div class="card p-6 sm:p-8 mb-6 acct-card bg-gradient-to-br from-white to-emerald-50/60">
      <div class="text-sm font-semibold text-slate-500">${greeting}, ${firstName} 👋</div>
      <div class="text-sm text-slate-500 mt-1">Total balance across ${summary.accounts_count} account(s)</div>
      <div id="dash-total" class="text-4xl sm:text-5xl font-extrabold tracking-tight mt-2 text-ink-900">$0.00</div>
      <div class="flex flex-wrap gap-2 mt-5">
        <a href="#/transfer" class="btn-primary !py-2.5 !px-5 text-sm no-underline">💸 Transfer</a>
        <button class="btn-ghost" onclick="mDeposit()">＋ Deposit</button>
        <a href="#/insights" class="btn-ghost no-underline">✨ AI Insights</a>
      </div>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      ${statCard('📥', 'Income (Sept)', money(summary.month_income), 'text-brand-600')}
      ${statCard('📤', 'Spent (Sept)', money(summary.month_expenses), 'text-red-500')}
      ${statCard('🏦', 'Accounts', summary.accounts_count, 'text-ink-900')}
      ${statCard('✨', 'Savings rate', (insights.savings_rate).toFixed(1) + '%', insights.savings_rate >= 20 ? 'text-brand-600' : 'text-amber-600')}
    </div>

    <div class="grid lg:grid-cols-5 gap-4 mb-6">
      <div class="card p-5 lg:col-span-3">
        <div class="font-bold mb-1">Cash flow <span class="text-xs font-medium text-slate-400">· last 30 days</span></div>
        <div class="h-56"><canvas id="ch-cashflow"></canvas></div>
      </div>
      <div class="card p-5 lg:col-span-2">
        <div class="font-bold mb-1">Spending by category</div>
        <div class="h-56 flex items-center justify-center"><canvas id="ch-cats"></canvas></div>
      </div>
    </div>

    <div class="grid lg:grid-cols-2 gap-4">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div class="font-bold">My accounts</div>
          <a href="#/accounts" class="text-sm font-semibold text-brand-600">View all →</a>
        </div>
        <div class="space-y-3">${accounts.map(miniAccount).join('') || emptyState('No accounts yet')}</div>
      </div>
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <div class="font-bold">Recent activity</div>
          <a href="#/transactions" class="text-sm font-semibold text-brand-600">View all →</a>
        </div>
        <div class="space-y-1">${recent.map((t) => txnRow(t, true)).join('') || emptyState('No transactions yet')}</div>
      </div>
    </div>`;

  countUp($('dash-total'), summary.total_balance, { prefix: '$', decimals: 2 });
  drawCashflow(insights.daily);
  drawCategories(insights.by_category);
}

const statCard = (icon, label, value, cls) => `
  <div class="card p-4 sm:p-5"><div class="text-2xl">${icon}</div>
  <div class="text-xl sm:text-2xl font-extrabold mt-2 ${cls}">${value}</div>
  <div class="text-xs font-semibold text-slate-400 mt-1">${label}</div></div>`;

const miniAccount = (a) => `
  <a href="#/transactions" onclick="prefilterAccount(${a.id})" class="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 transition no-underline">
    <div class="w-10 h-10 rounded-xl ${a.account_type === 'savings' ? 'bg-emerald-100' : 'bg-sky-100'} flex items-center justify-center text-xl">${a.account_type === 'savings' ? '🏦' : '💳'}</div>
    <div class="min-w-0 flex-1">
      <div class="font-bold text-sm truncate">${esc(a.account_name)}</div>
      <div class="text-xs text-slate-400">…${esc(a.account_number.slice(-4))} · ${esc(a.account_type)}</div>
    </div>
    <div class="font-extrabold">${money(a.balance, a.currency)}</div>
  </a>`;

function txnRow(t, compact = false) {
  const meta = TXN_META[t.type] || { label: t.type, dir: 1 };
  const sign = meta.dir >= 0 ? '+' : '−';
  return `
  <div class="flex items-center gap-3 ${compact ? 'py-2' : 'p-3 rounded-xl hover:bg-slate-50'}">
    <div class="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-xl flex-none">${CAT_ICON[t.category] || '🧾'}</div>
    <div class="min-w-0 flex-1">
      <div class="font-semibold text-sm truncate">${esc(t.description)}</div>
      <div class="text-xs text-slate-400">${meta.label} · ${timeAgo(t.created_at)} ${t.category ? `· <span class="cat-pill !py-0">${esc(t.category)}</span>` : ''}</div>
    </div>
    <div class="${meta.dir >= 0 ? 'txn-amt-in' : 'txn-amt-out'} text-sm whitespace-nowrap">${sign}${money(Math.abs(t.amount)).slice(0)}</div>
  </div>`;
}

const emptyState = (msg) => `<div class="text-center text-sm text-slate-400 py-8">🫧<br>${esc(msg)}</div>`;

function destroyCharts() { Object.values(charts).forEach((c) => c?.destroy()); charts = {}; }

function drawCashflow(daily) {
  destroyCharts();
  if (typeof Chart === 'undefined') return;
  Chart.defaults.font.family = 'Inter, sans-serif';
  const labels = daily.map((d) => { const dt = new Date(d.date + 'T00:00'); return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); });
  charts.cf = new Chart($('ch-cashflow'), {
    type: 'bar',
    data: { labels, datasets: [
      { label: 'Income', data: daily.map((d) => d.income), backgroundColor: '#10b981', borderRadius: 4 },
      { label: 'Expenses', data: daily.map((d) => d.expenses), backgroundColor: '#f87171', borderRadius: 4 },
    ]},
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } }, y: { ticks: { callback: (v) => '$' + v } } } },
  });
}

function drawCategories(byCat) {
  if (typeof Chart === 'undefined') return;
  const top = byCat.slice(0, 6);
  if (!top.length) { $('ch-cats').parentElement.innerHTML = emptyState('No spending yet'); return; }
  const palette = ['#059669', '#0ea5e9', '#f59e0b', '#8b5cf6', '#ec4899', '#64748b'];
  charts.cats = new Chart($('ch-cats'), {
    type: 'doughnut',
    data: { labels: top.map((c) => c.category), datasets: [{ data: top.map((c) => c.amount), backgroundColor: palette, borderWidth: 2, borderColor: '#fff' }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } },
  });
}

/* ------------------------------ accounts ------------------------------ */

async function vAccounts(view) {
  await ensureAccounts();
  view.innerHTML = `
    <div class="flex items-center justify-between mb-5">
      <div class="text-sm text-slate-500">${state.accounts.length} account(s) · Total <b class="text-ink-900">${money(state.accounts.reduce((s, a) => s + Number(a.balance), 0))}</b></div>
      <button class="btn-primary !py-2.5 !px-5 text-sm" onclick="mNewAccount()">＋ New account</button>
    </div>
    <div class="grid md:grid-cols-2 gap-4">
      ${state.accounts.map((a) => `
      <div class="card acct-card p-6 ${a.status !== 'active' ? 'opacity-75' : ''}">
        <div class="flex items-start justify-between">
          <div class="w-12 h-12 rounded-2xl ${a.account_type === 'savings' ? 'bg-emerald-100' : 'bg-sky-100'} flex items-center justify-center text-2xl">${a.account_type === 'savings' ? '🏦' : '💳'}</div>
          <div class="flex gap-2">
            <span class="badge badge-slate !text-[11px]">${esc(a.account_type)}</span>
            ${a.status === 'active' ? '<span class="badge !text-[11px]">● Active</span>' : `<span class="badge badge-red !text-[11px]">❄ ${esc(a.status)}</span>`}
          </div>
        </div>
        <div class="font-bold text-lg mt-3">${esc(a.account_name)}</div>
        <button class="text-xs text-slate-400 font-mono hover:text-brand-600" onclick="copyText('${esc(a.account_number)}')">${esc(a.account_number)} ⧉</button>
        <div class="text-3xl font-extrabold mt-2">${money(a.balance, a.currency)}</div>
        <div class="text-xs text-slate-400 mt-1">Opened ${fmtDate(a.created_at)}</div>
        ${a.status === 'active' ? `
        <div class="flex gap-2 mt-4">
          <button class="btn-ghost flex-1 !py-2 text-sm" onclick="mDeposit(${a.id})">＋ Deposit</button>
          <button class="btn-ghost flex-1 !py-2 text-sm" onclick="mWithdraw(${a.id})">－ Withdraw</button>
          <button class="btn-ghost flex-1 !py-2 text-sm" onclick="prefilterAccount(${a.id});location.hash='#/transactions'">🧾 History</button>
        </div>` : `<div class="mt-4 text-sm font-semibold text-red-600 bg-red-50 rounded-xl p-3">❄ This account is frozen. Contact support.</div>`}
      </div>`).join('')}
    </div>`;
}

/* ------------------------------ transactions ------------------------------ */

function prefilterAccount(id) { state.tx.accountId = String(id); state.tx.offset = 0; }

async function vTransactions(view) {
  await ensureAccounts();
  view.innerHTML = `
    <div class="card p-5 mb-4">
      <div class="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div><label class="lbl">Account</label><select id="f-account" class="sel" onchange="txFilter({accountId:this.value})">
          <option value="all">All accounts</option>
          ${state.accounts.map((a) => `<option value="${a.id}">…${a.account_number.slice(-4)} · ${esc(a.account_name)}</option>`).join('')}
        </select></div>
        <div><label class="lbl">Type</label><select id="f-type" class="sel" onchange="txFilter({type:this.value})">
          <option value="">All types</option><option value="deposit">Deposits</option>
          <option value="withdrawal">Withdrawals</option><option value="transfer_in">Transfers in</option><option value="transfer_out">Transfers out</option>
        </select></div>
        <div class="lg:col-span-2"><label class="lbl">Search</label>
          <input id="f-search" class="inp" placeholder="e.g. starbucks, salary…" value="${esc(state.tx.search)}" onkeydown="if(event.key==='Enter')txFilter({search:this.value})" />
        </div>
        <div class="flex items-end gap-2">
          <button class="btn-primary !py-2.5 text-sm flex-1" onclick="txFilter({search:$('f-search').value})">Search</button>
          <button class="btn-ghost !py-2.5 text-sm" onclick="exportCSV()" title="Download CSV">⬇</button>
        </div>
      </div>
    </div>
    <div class="card p-2 sm:p-4">
      <div id="txn-list"></div>
      <div class="flex items-center justify-between px-3 py-3">
        <div id="txn-count" class="text-xs text-slate-400"></div>
        <div class="flex gap-2">
          <button id="txn-prev" class="btn-ghost !py-1.5 text-sm" onclick="txPage(-1)">← Prev</button>
          <button id="txn-next" class="btn-ghost !py-1.5 text-sm" onclick="txPage(1)">Next →</button>
        </div>
      </div>
    </div>`;
  $('f-account').value = String(state.tx.accountId);
  $('f-type').value = state.tx.type;
  await loadTxns();
}

function txFilter(patch) {
  Object.assign(state.tx, patch, { offset: 0 });
  loadTxns();
}
function txPage(dir) {
  const f = state.tx;
  f.offset = Math.max(0, Math.min(Math.max(0, f.total - f.limit), f.offset + dir * f.limit));
  loadTxns();
}

async function loadTxns() {
  const f = state.tx;
  $('txn-list').innerHTML = `<div class="space-y-2 p-2"><div class="skeleton h-14"></div><div class="skeleton h-14"></div><div class="skeleton h-14"></div></div>`;
  const qs = `${f.type ? `&type=${f.type}` : ''}${f.search ? `&search=${encodeURIComponent(f.search)}` : ''}`;
  if (String(f.accountId) === 'all') {
    const pages = await Promise.all(state.accounts.map((a) => api(`/accounts/${a.id}/transactions?limit=100&offset=0${qs}`)));
    const merged = pages.flatMap((p) => p.items).sort((x, y) => parseUTC(y.created_at) - parseUTC(x.created_at));
    f.total = merged.length;
    f.items = merged.slice(f.offset, f.offset + f.limit);
  } else {
    const p = await api(`/accounts/${f.accountId}/transactions?limit=${f.limit}&offset=${f.offset}${qs}`);
    f.items = p.items; f.total = p.total;
  }
  $('txn-list').innerHTML = f.items.length
    ? `<div class="divide-y divide-slate-50">${f.items.map((t) => txnRow(t)).join('')}</div>`
    : emptyState('No transactions match your filters');
  $('txn-count').textContent = f.total ? `Showing ${f.offset + 1}–${Math.min(f.offset + f.limit, f.total)} of ${f.total}` : '0 results';
  $('txn-prev').disabled = f.offset <= 0;
  $('txn-next').disabled = f.offset + f.limit >= f.total;
}

async function exportCSV() {
  toast('Preparing CSV…', 'info');
  try {
    const f = state.tx;
    let items;
    if (String(f.accountId) === 'all') {
      const pages = await Promise.all(state.accounts.map((a) => api(`/accounts/${a.id}/transactions?limit=500&offset=0`)));
      items = pages.flatMap((p) => p.items);
    } else {
      items = (await api(`/accounts/${f.accountId}/transactions?limit=500&offset=0`)).items;
    }
    const rows = [['id', 'date', 'account_id', 'type', 'amount', 'balance_after', 'description', 'category']];
    items.forEach((t) => rows.push([t.id, t.created_at, t.account_id, t.type, t.amount, t.balance_after, `"${String(t.description).replace(/"/g, '""')}"`, t.category]));
    const blob = new Blob([rows.map((r) => r.join(',')).join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `quicksave-transactions-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    toast(`Exported ${items.length} transactions ⬇`);
  } catch (err) { toast(err.message, 'err'); }
}

/* ------------------------------ transfer ------------------------------ */

async function vTransfer(view) {
  await ensureAccounts();
  const active = state.accounts.filter((a) => a.status === 'active');
  state.transferLookup = null;
  view.innerHTML = `
  <div class="grid lg:grid-cols-5 gap-4">
    <div class="card p-6 lg:col-span-3">
      <div class="font-bold text-lg mb-1">Send money ⚡</div>
      <div class="text-sm text-slate-500 mb-5">Instant settlement between QuickSave accounts. Try <button class="font-mono text-brand-600 font-bold" onclick="fillDemoTarget()">QS1000000003</button> (Alex Carter).</div>
      <div class="space-y-4">
        <div><label class="lbl">From account</label>
          <select id="t-from" class="sel">${active.map((a) => `<option value="${a.id}">${esc(a.account_name)} (…${a.account_number.slice(-4)}) — ${money(a.balance)}</option>`).join('')}</select>
        </div>
        <div><label class="lbl">To account number</label>
          <div class="flex gap-2">
            <input id="t-to" class="inp font-mono uppercase" placeholder="QS + 10 digits" maxlength="12" />
            <button class="btn-ghost whitespace-nowrap" onclick="lookupTarget()">🔍 Verify</button>
          </div>
          <div id="t-lookup" class="mt-2"></div>
        </div>
        <div><label class="lbl">Amount (USD)</label>
          <input id="t-amount" type="number" min="0.01" step="0.01" class="inp" placeholder="0.00" />
        </div>
        <div><label class="lbl">Note (optional)</label>
          <input id="t-desc" class="inp" placeholder="e.g. Dinner split" maxlength="120" />
        </div>
        <button class="btn-primary w-full" onclick="doTransfer(this)">Send →</button>
      </div>
    </div>
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-6">
        <div class="font-bold mb-3">💡 How it works</div>
        <ul class="text-sm text-slate-600 space-y-2">
          <li>✅ Recipient is verified before you send</li>
          <li>⚡ Both ledger entries commit atomically</li>
          <li>🧾 Full audit trail on both sides</li>
          <li>✨ AI auto-categorizes every transfer</li>
        </ul>
      </div>
      <div class="card p-6">
        <div class="font-bold mb-3">Recent transfers</div>
        <div id="t-recent" class="space-y-1 text-sm"><div class="skeleton h-10"></div></div>
      </div>
    </div>
  </div>`;
  try {
    const recent = await api('/transactions/recent?limit=20');
    const transfers = recent.filter((t) => t.type.startsWith('transfer')).slice(0, 5);
    $('t-recent').innerHTML = transfers.length ? transfers.map((t) => txnRow(t, true)).join('') : '<div class="text-sm text-slate-400">No transfers yet — yours will show up here.</div>';
  } catch (e) { $('t-recent').innerHTML = ''; }
}

function fillDemoTarget() { $('t-to').value = 'QS1000000003'; lookupTarget(); }

async function lookupTarget() {
  const num = $('t-to').value.trim();
  const box = $('t-lookup');
  if (!num) { box.innerHTML = ''; return; }
  box.innerHTML = `<div class="text-sm text-slate-400">Verifying…</div>`;
  try {
    const r = await api(`/accounts/lookup/${encodeURIComponent(num)}`);
    state.transferLookup = r;
    box.innerHTML = `<div class="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-xl p-3">
      <div class="w-9 h-9 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold">${esc(r.owner_display[0] || '?')}</div>
      <div><div class="font-bold text-sm">Send to ${esc(r.owner_display)}</div>
      <div class="text-xs text-slate-500">${esc(r.account_name)} · ${esc(r.account_type)} · ${esc(r.account_number)}</div></div>
      <div class="ml-auto text-emerald-600 font-bold">✓</div></div>`;
  } catch (err) {
    state.transferLookup = null;
    box.innerHTML = `<div class="text-sm font-semibold text-red-600 bg-red-50 rounded-xl p-3">⛔ ${esc(err.message)}</div>`;
  }
}

async function doTransfer(btn) {
  const fromId = $('t-from').value;
  const to = $('t-to').value.trim();
  const amount = parseFloat($('t-amount').value);
  const desc = $('t-desc').value.trim();
  if (!fromId || !to) return toast('Select source and destination accounts', 'err');
  if (!amount || amount <= 0) return toast('Enter a valid amount', 'err');
  btn.disabled = true; btn.textContent = 'Sending…';
  try {
    const r = await api('/transactions/transfer', { method: 'POST', body: { from_account_id: Number(fromId), to_account_number: to, amount, description: desc } });
    state.accounts = await api('/accounts');
    openModal(`
      <div class="text-center">
        <div class="text-5xl mb-3">🎉</div>
        <div class="font-extrabold text-xl">Sent ${money(r.debit.amount)}!</div>
        <div class="text-sm text-slate-500 mt-1">${esc(desc) || 'Transfer'} → <b class="font-mono">${esc(to.toUpperCase())}</b></div>
        <div class="bg-slate-50 rounded-xl p-4 mt-4 text-sm text-left space-y-1">
          <div class="flex justify-between"><span class="text-slate-500">Reference</span><b>#${r.debit.id}</b></div>
          <div class="flex justify-between"><span class="text-slate-500">Your new balance</span><b>${money(r.debit.balance_after)}</b></div>
        </div>
        <button class="btn-primary w-full mt-4" onclick="closeModal();location.hash='#/transactions'">View receipt 🧾</button>
      </div>`);
    toast('Transfer completed ⚡');
  } catch (err) { toast(err.message, 'err'); }
  btn.disabled = false; btn.textContent = 'Send →';
}

/* ------------------------------ insights ------------------------------ */

async function vInsights(view) {
  const days = state.insightsDays;
  view.innerHTML = `
    <div class="flex flex-wrap items-center gap-2 mb-5">
      ${[7, 30, 90].map((d) => `<button onclick="setInsightsDays(${d})" class="${d === days ? 'btn-primary !py-2 !px-4 text-sm' : 'btn-ghost !py-2 !px-4 text-sm'}">Last ${d} days</button>`).join('')}
    </div>
    <div id="ins-body"><div class="space-y-4"><div class="skeleton h-32"></div><div class="skeleton h-56"></div></div></div>`;
  await loadInsights();
}
function setInsightsDays(d) { state.insightsDays = d; vInsights($('view')); }

async function loadInsights() {
  const ins = await api(`/ai/insights?days=${state.insightsDays}`);
  state.insights = ins;
  const maxCat = Math.max(1, ...ins.by_category.map((c) => c.amount));
  $('ins-body').innerHTML = `
    <div class="card p-6 mb-4 bg-gradient-to-br from-white to-violet-50/60 view-enter">
      <div class="flex items-center gap-2 mb-2">
        <span class="badge">✨ QuickSave AI</span>
        <span class="text-[11px] text-slate-400 font-mono">${esc(ins.provider)}</span>
      </div>
      <p class="text-[15px] leading-relaxed">${esc(ins.narrative)}</p>
      <button class="text-sm font-bold text-brand-600 mt-3" onclick="toggleChat(true);setTimeout(()=>askAI('Tell me more about my spending'),300)">Discuss this with AI →</button>
    </div>
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
      ${statCard('📥', 'Income', money(ins.income), 'text-brand-600')}
      ${statCard('📤', 'Expenses', money(ins.expenses), 'text-red-500')}
      ${statCard('⚖️', 'Net', money(ins.net), ins.net >= 0 ? 'text-brand-600' : 'text-red-500')}
      ${statCard('🎯', 'Savings rate', ins.savings_rate.toFixed(1) + '%', ins.savings_rate >= 20 ? 'text-brand-600' : 'text-amber-600')}
    </div>
    <div class="grid lg:grid-cols-2 gap-4">
      <div class="card p-5">
        <div class="font-bold mb-4">Top categories</div>
        <div class="space-y-3">${ins.by_category.slice(0, 7).map((c) => `
          <div><div class="flex justify-between text-sm mb-1"><span class="font-semibold">${CAT_ICON[c.category] || '•'} ${esc(c.category)} <span class="text-slate-400 font-normal">×${c.count}</span></span><b>${money(c.amount)}</b></div>
          <div class="h-2 bg-slate-100 rounded-full"><div class="h-2 bg-gradient-to-r from-emerald-400 to-emerald-600 rounded-full" style="width:${(c.amount / maxCat * 100).toFixed(1)}%"></div></div></div>`).join('') || emptyState('No spending in this period')}
        </div>
      </div>
      <div class="space-y-4">
        <div class="card p-5">
          <div class="font-bold mb-3">🚨 Worth a look</div>
          ${ins.anomalies.length ? ins.anomalies.map((t) => txnRow(t, true)).join('') : '<div class="text-sm text-slate-500">✅ No unusual transactions detected. Nice and steady.</div>'}
        </div>
        <div class="card p-5">
          <div class="font-bold mb-3">💎 Biggest expenses</div>
          ${ins.top_expenses.length ? ins.top_expenses.map((t) => txnRow(t, true)).join('') : emptyState('Nothing here yet')}
        </div>
      </div>
    </div>`;
}

/* ------------------------------ admin ------------------------------ */

async function vAdmin(view) {
  const [stats, users, accounts, txns] = await Promise.all([
    api('/admin/stats'), api('/admin/users?limit=50'),
    api('/admin/accounts?limit=50'), api('/admin/transactions?limit=15'),
  ]);
  state.admin = { stats, users, accounts, txns };
  view.innerHTML = `
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      ${statCard('👥', 'Total users', stats.total_users, 'text-ink-900')}
      ${statCard('💳', 'Accounts', stats.total_accounts, 'text-ink-900')}
      ${statCard('💰', 'Total deposits', money(stats.total_balance), 'text-brand-600')}
      ${statCard('⚡', 'Volume (7d)', money(stats.volume_7d), 'text-violet-600')}
    </div>
    <div class="card p-5 mb-4">
      <div class="font-bold mb-3">🏦 Accounts <span class="text-xs font-medium text-slate-400">· freeze / unfreeze</span></div>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr><th>Account</th><th>Owner</th><th>Type</th><th>Balance</th><th>Status</th><th></th></tr></thead>
        <tbody>${accounts.map((a) => `
          <tr><td><b class="font-mono text-[13px]">${esc(a.account_number)}</b><div class="text-xs text-slate-400">${esc(a.account_name)}</div></td>
          <td class="text-[13px]">${esc(a.owner_name)}<div class="text-xs text-slate-400">${esc(a.owner_email)}</div></td>
          <td><span class="cat-pill">${esc(a.account_type)}</span></td>
          <td class="font-bold">${money(a.balance)}</td>
          <td>${a.status === 'active' ? '<span class="badge !text-[11px]">● Active</span>' : '<span class="badge badge-red !text-[11px]">❄ Frozen</span>'}</td>
          <td class="text-right"><button class="btn-ghost !py-1 !px-3 text-xs" onclick="setStatus(${a.id},'${a.status === 'active' ? 'frozen' : 'active'}')">${a.status === 'active' ? '❄ Freeze' : '☀ Unfreeze'}</button></td></tr>`).join('')}
        </tbody></table></div>
    </div>
    <div class="grid lg:grid-cols-2 gap-4">
      <div class="card p-5">
        <div class="font-bold mb-3">👥 Users</div>
        <div class="tbl-wrap"><table class="tbl">
          <thead><tr><th>User</th><th>Accts</th><th>Balance</th></tr></thead>
          <tbody>${users.map((u) => `
            <tr><td><b class="text-[13px]">${esc(u.user.full_name)}</b> ${u.user.is_admin ? '<span class="badge badge-amber !text-[10px]">admin</span>' : ''}<div class="text-xs text-slate-400">${esc(u.user.email)}</div></td>
            <td>${u.accounts_count}</td><td class="font-bold">${money(u.total_balance)}</td></tr>`).join('')}
          </tbody></table></div>
      </div>
      <div class="card p-5">
        <div class="font-bold mb-3">🧾 Latest platform activity</div>
        <div class="space-y-1">${txns.map((t) => txnRow(t, true)).join('')}</div>
      </div>
    </div>`;
}

async function setStatus(id, status) {
  try {
    await api(`/admin/accounts/${id}/status`, { method: 'PATCH', body: { status } });
    toast(status === 'frozen' ? 'Account frozen ❄' : 'Account reactivated ☀');
    vAdmin($('view'));
  } catch (err) { toast(err.message, 'err'); }
}

/* ------------------------------ modals ------------------------------ */

function openModal(html) {
  $('modal-root').innerHTML = `<div class="modal-overlay" onclick="if(event.target===this)closeModal()"><div class="modal-card">${html}</div></div>`;
}
function closeModal() { $('modal-root').innerHTML = ''; }
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { closeModal(); toggleChat(false); } });

const accountOptions = (selected) => state.accounts
  .filter((a) => a.status === 'active')
  .map((a) => `<option value="${a.id}" ${a.id === selected ? 'selected' : ''}>${esc(a.account_name)} (…${a.account_number.slice(-4)}) — ${money(a.balance)}</option>`).join('');

async function mDeposit(preselect) {
  await ensureAccounts();
  openModal(`
    <div class="font-extrabold text-xl mb-1">＋ Deposit</div>
    <div class="text-sm text-slate-500 mb-4">Funds arrive instantly.</div>
    <label class="lbl">Account</label><select id="m-account" class="sel mb-3">${accountOptions(preselect)}</select>
    <label class="lbl">Amount</label><input id="m-amount" type="number" min="0.01" step="0.01" class="inp mb-3" placeholder="0.00" />
    <label class="lbl">Description</label><input id="m-desc" class="inp mb-4" placeholder="e.g. Cash deposit" maxlength="120" />
    <div class="flex gap-2"><button class="btn-ghost flex-1" onclick="closeModal()">Cancel</button>
    <button class="btn-primary flex-1" onclick="submitMoney('deposit', this)">Deposit</button></div>`);
}
async function mWithdraw(preselect) {
  await ensureAccounts();
  openModal(`
    <div class="font-extrabold text-xl mb-1">－ Withdraw</div>
    <div class="text-sm text-slate-500 mb-4">Overdrafts are blocked automatically.</div>
    <label class="lbl">Account</label><select id="m-account" class="sel mb-3">${accountOptions(preselect)}</select>
    <label class="lbl">Amount</label><input id="m-amount" type="number" min="0.01" step="0.01" class="inp mb-3" placeholder="0.00" />
    <label class="lbl">Description</label><input id="m-desc" class="inp mb-4" placeholder="e.g. ATM cash" maxlength="120" />
    <div class="flex gap-2"><button class="btn-ghost flex-1" onclick="closeModal()">Cancel</button>
    <button class="btn-primary flex-1" onclick="submitMoney('withdraw', this)">Withdraw</button></div>`);
}
async function submitMoney(kind, btn) {
  const id = $('m-account').value, amount = parseFloat($('m-amount').value), desc = $('m-desc').value.trim();
  if (!amount || amount <= 0) return toast('Enter a valid amount', 'err');
  btn.disabled = true;
  try {
    const t = await api(`/accounts/${id}/${kind === 'deposit' ? 'deposit' : 'withdraw'}`, { method: 'POST', body: { amount, description: desc } });
    state.accounts = await api('/accounts');
    closeModal();
    toast(`${kind === 'deposit' ? 'Deposited' : 'Withdrew'} ${money(t.amount)} — new balance ${money(t.balance_after)}`);
    renderRoute();
  } catch (err) { toast(err.message, 'err'); btn.disabled = false; }
}

function mNewAccount() {
  openModal(`
    <div class="font-extrabold text-xl mb-1">💳 Open account</div>
    <div class="text-sm text-slate-500 mb-4">Free, instant, no paperwork.</div>
    <label class="lbl">Nickname</label><input id="m-name" class="inp mb-3" placeholder="e.g. Travel fund" maxlength="60" />
    <label class="lbl">Type</label><select id="m-type" class="sel mb-3"><option value="savings">🏦 Savings</option><option value="checking">💳 Checking</option></select>
    <label class="lbl">Initial deposit (optional)</label><input id="m-initial" type="number" min="0" step="0.01" class="inp mb-4" placeholder="0.00" />
    <div class="flex gap-2"><button class="btn-ghost flex-1" onclick="closeModal()">Cancel</button>
    <button class="btn-primary flex-1" onclick="submitNewAccount(this)">Open account</button></div>`);
}
async function submitNewAccount(btn) {
  const name = $('m-name').value.trim() || 'My Account';
  btn.disabled = true;
  try {
    const a = await api('/accounts', { method: 'POST', body: { account_name: name, account_type: $('m-type').value, initial_deposit: parseFloat($('m-initial').value) || 0 } });
    state.accounts = await api('/accounts');
    closeModal();
    toast(`Account ${a.account_number} opened! 🎉`);
    renderRoute();
  } catch (err) { toast(err.message, 'err'); btn.disabled = false; }
}

/* ------------------------------ AI chat ------------------------------ */

function toggleChat(force) {
  const panel = $('ai-panel');
  const show = force ?? panel.classList.contains('hidden');
  panel.classList.toggle('hidden', !show);
  if (show && !chatBooted) {
    chatBooted = true;
    const name = state.user ? esc(state.user.full_name.split(' ')[0]) : 'there';
    pushMsg('ai', `Hi ${name}! 👋 I'm <strong>QuickSave AI</strong>. Ask me about your balances, spending, or savings — I know your accounts.`);
    renderChips(['What\'s my total balance?', 'Summarize my spending', 'Any unusual transactions?', 'Give me a savings tip']);
  }
  if (show) setTimeout(() => $('ai-text').focus(), 100);
}

function pushMsg(role, html) {
  const box = $('ai-messages');
  const el = document.createElement('div');
  el.className = `msg msg-${role === 'user' ? 'user' : 'ai'}`;
  el.innerHTML = html;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function renderChips(suggestions) {
  $('ai-chips').innerHTML = (suggestions || []).map((s) => `<button class="ai-chip" onclick="askAI(${JSON.stringify(s).replace(/"/g, '&quot;')})">${esc(s)}</button>`).join('');
}

function askAI(text) { $('ai-text').value = text; sendChat(new Event('submit')); }

async function sendChat(e) {
  e.preventDefault();
  const input = $('ai-text');
  const text = input.value.trim();
  if (!text) return false;
  input.value = '';
  pushMsg('user', esc(text));
  renderChips([]);
  const typing = pushMsg('ai', `<div class="msg-typing" style="padding:0"><span></span><span></span><span></span></div>`);
  $('ai-send').disabled = true;
  try {
    const r = await api('/ai/chat', { method: 'POST', body: { message: text, history: chatHistory.slice(-6) } });
    typing.innerHTML = miniMd(r.reply);
    $('ai-messages').scrollTop = $('ai-messages').scrollHeight;
    chatHistory.push({ role: 'user', content: text }, { role: 'assistant', content: r.reply });
    renderChips(r.suggestions || []);
  } catch (err) {
    typing.innerHTML = `⚠️ ${esc(err.message)}`;
  }
  $('ai-send').disabled = false;
  return false;
}

/* ------------------------------ init ------------------------------ */

async function init() {
  // Animate hero counters on the auth screen
  document.querySelectorAll('.hero-stat-num').forEach((el) => countUp(el, Number(el.dataset.count)));
  const token = localStorage.getItem('qs_token');
  if (!token) { $('auth-screen').classList.remove('hidden'); return; }
  try {
    state.user = await api('/auth/me');
    enterApp();
  } catch (e) {
    localStorage.removeItem('qs_token');
    $('auth-screen').classList.remove('hidden');
  }
}

init();
