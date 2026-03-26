/**
 * admin.js — Back2Roots Admin Dashboard
 *
 * Responsibilities:
 *   1. Auth guard — redirect non-admin users to login
 *   2. Load stats and pending users from FastAPI backend
 *   3. Approve / Reject actions with confirmation modal
 *   4. Live filter (search + role chip)
 *   5. Toast notifications
 *   6. Clock, sparklines, sidebar badge
 */

'use strict';

/* ── Config ─────────────────────────────────────────────── */
const API_BASE = 'http://localhost:8000';

/* ── Auth helpers ────────────────────────────────────────── */
function getToken() {
  return localStorage.getItem('token') || sessionStorage.getItem('token') || null;
}

function getUser() {
  try {
    const raw = localStorage.getItem('user') || sessionStorage.getItem('user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function removeToken() {
  ['token', 'user'].forEach(k => {
    localStorage.removeItem(k);
    sessionStorage.removeItem(k);
  });
}

/* ── Auth Guard ──────────────────────────────────────────── */
(function guardAdmin() {
  const token = getToken();
  const user  = getUser();

  if (!token || !user) {
    window.location.replace('login.html');
    return;
  }
  if (user.role !== 'admin') {
    window.location.replace('login.html');
  }
})();

/* ── Fetch wrapper ───────────────────────────────────────── */
async function apiFetch(path, options = {}) {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401 || res.status === 403) {
    removeToken();
    window.location.replace('login.html');
    throw new Error('Unauthorised');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.status === 204 ? null : res.json();
}

/* ── Toast ───────────────────────────────────────────────── */
function toast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-dot"></span><span>${message}</span>`;
  container.prepend(el);

  setTimeout(() => {
    el.classList.add('fade-out');
    el.addEventListener('animationend', () => el.remove(), { once: true });
  }, 3500);
}

/* ── Clock ───────────────────────────────────────────────── */
function startClock() {
  const el = document.getElementById('topbar-time');
  const tick = () => {
    el.textContent = new Date().toLocaleTimeString('en-GB', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
  };
  tick();
  setInterval(tick, 1000);
}

/* ── Sparkline (SVG) ─────────────────────────────────────── */
function drawSparkline(containerId, colorClass) {
  const el = document.getElementById(containerId);
  if (!el) return;

  // Generate fake trend data for visual polish
  const points = Array.from({ length: 8 }, (_, i) =>
    20 + Math.round(Math.sin(i * 0.9) * 8 + Math.random() * 6)
  );

  const w = 64, h = 28;
  const min = Math.min(...points), max = Math.max(...points);
  const range = max - min || 1;

  const coords = points.map((p, i) => ({
    x: (i / (points.length - 1)) * w,
    y: h - ((p - min) / range) * h * 0.85 - 2,
  }));

  const pathD = coords.map((c, i) =>
    (i === 0 ? `M${c.x},${c.y}` : `L${c.x},${c.y}`)
  ).join(' ');

  const fillD = pathD + ` L${w},${h} L0,${h} Z`;

  const color = colorClass === 'blue' ? '#1d8cf8'
              : colorClass === 'cyan' ? '#00d4ff'
              : '#ef4444';

  el.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
      <defs>
        <linearGradient id="grad-${containerId}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stop-color="${color}" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <path d="${fillD}" fill="url(#grad-${containerId})"/>
      <path d="${pathD}" stroke="${color}" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
}

/* ── Sidebar user info ───────────────────────────────────── */
function populateSidebarUser() {
  const user = getUser();
  if (!user) return;

  const name    = user.name || user.email || 'Admin';
  const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  const avatarEl = document.getElementById('sidebar-avatar');
  const nameEl   = document.getElementById('sidebar-user-name');

  if (avatarEl) avatarEl.textContent = initials;
  if (nameEl)   nameEl.textContent   = name;
}

/* ── State ───────────────────────────────────────────────── */
let allPendingUsers = [];    // master list
let filterText  = '';
let filterRole  = 'all';

/* ── Stats ───────────────────────────────────────────────── */
async function loadStats() {
  try {
    // Try a dedicated stats endpoint first; fall back to counting from pending list
    let students = 0, alumni = 0, pending = 0;

    try {
      const data = await apiFetch('/admin/stats');
      students = data.students ?? data.total_students ?? 0;
      alumni   = data.alumni   ?? data.total_alumni   ?? 0;
      pending  = data.pending  ?? data.pending_users  ?? 0;
    } catch {
      // Endpoint may not exist — stats will update when pending list loads
    }

    animateCount('stat-students-val', students);
    animateCount('stat-alumni-val',   alumni);
    // pending count is set after loadPendingUsers resolves

    document.getElementById('stat-students-sub').textContent =
      students > 0 ? `${students} registered` : 'No data';
    document.getElementById('stat-alumni-sub').textContent =
      alumni > 0 ? `${alumni} registered` : 'No data';

    drawSparkline('spark-students', 'blue');
    drawSparkline('spark-alumni',   'cyan');
  } catch (err) {
    console.warn('[admin] stats error:', err);
  }
}

/* Animated count-up */
function animateCount(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = '0';

  if (target === 0) { el.textContent = '0'; return; }

  const duration = 900;
  const start    = performance.now();

  function step(now) {
    const elapsed  = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target).toLocaleString();
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* ── Pending users ───────────────────────────────────────── */
async function loadPendingUsers() {
  const tbody    = document.getElementById('pending-tbody');
  const emptyEl  = document.getElementById('empty-state');
  const errorEl  = document.getElementById('error-state');
  const footerEl = document.getElementById('table-footer');

  // Reset
  errorEl.style.display = 'none';
  emptyEl.style.display = 'none';
  footerEl.style.display = 'none';
  tbody.innerHTML = skeletonRows(3);

  try {
    const data = await apiFetch('/admin/pending-users');

    // Normalise: accept array or {users: [...]}
    allPendingUsers = Array.isArray(data) ? data
                    : Array.isArray(data?.users) ? data.users
                    : [];

    // Update pending stat card
    animateCount('stat-pending-val', allPendingUsers.length);
    document.getElementById('stat-pending-sub').textContent =
      allPendingUsers.length > 0
        ? `${allPendingUsers.length} awaiting review`
        : 'Queue is clear ✓';

    // Sidebar badge
    const badge = document.getElementById('sidebar-pending-count');
    if (badge) {
      badge.textContent = allPendingUsers.length;
      badge.dataset.count = allPendingUsers.length;
    }

    renderTable();
  } catch (err) {
    tbody.innerHTML = '';
    errorEl.style.display = 'block';
    document.getElementById('error-desc').textContent =
      err.message || 'Could not reach the server. Check your connection.';
    console.error('[admin] failed to load pending users:', err);
  }
}

function skeletonRows(n) {
  return Array.from({ length: n }, () => `
    <tr class="skeleton-row">
      <td><div class="skel skel-name"></div></td>
      <td><div class="skel skel-email"></div></td>
      <td><div class="skel skel-chip"></div></td>
      <td><div class="skel skel-date"></div></td>
      <td><div class="skel-actions"></div></td>
    </tr>`).join('');
}

/* ── Render / filter ─────────────────────────────────────── */
function renderTable() {
  const tbody    = document.getElementById('pending-tbody');
  const emptyEl  = document.getElementById('empty-state');
  const footerEl = document.getElementById('table-footer');
  const countLbl = document.getElementById('table-count-label');

  const q = filterText.toLowerCase();
  const filtered = allPendingUsers.filter(u => {
    const matchRole = filterRole === 'all' || u.role === filterRole;
    const matchText = !q
      || (u.name  || '').toLowerCase().includes(q)
      || (u.email || '').toLowerCase().includes(q)
      || (u.role  || '').toLowerCase().includes(q);
    return matchRole && matchText;
  });

  tbody.innerHTML = '';

  if (filtered.length === 0) {
    emptyEl.style.display = 'block';
    footerEl.style.display = 'none';
    return;
  }

  emptyEl.style.display = 'none';
  footerEl.style.display = 'block';
  countLbl.textContent   = `Showing ${filtered.length} of ${allPendingUsers.length} pending user${allPendingUsers.length !== 1 ? 's' : ''}`;

  filtered.forEach((user, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'row-enter';
    tr.style.animationDelay = `${idx * 40}ms`;
    tr.dataset.id = user.id;
    tr.innerHTML = userRow(user);
    tbody.appendChild(tr);

    tr.querySelector('.btn-approve').addEventListener('click', () =>
      confirmAction('approve', user)
    );
    tr.querySelector('.btn-reject').addEventListener('click', () =>
      confirmAction('reject', user)
    );
  });
}

function userRow(user) {
  const name     = user.name  || 'Unknown User';
  const email    = user.email || '—';
  const role     = user.role  || 'unknown';
  const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  const roleClass = ['student', 'alumni'].includes(role) ? role : 'unknown';
  const avClass   = ['student', 'alumni'].includes(role) ? role : 'default';

  const date = user.created_at
    ? new Date(user.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    : '—';

  const uid = user.id ? String(user.id).slice(0, 8) + '…' : '—';

  return `
    <td>
      <div class="user-cell">
        <div class="user-av ${avClass}">${initials}</div>
        <div>
          <div class="user-name">${escHtml(name)}</div>
          <div class="user-id">#${escHtml(uid)}</div>
        </div>
      </div>
    </td>
    <td><span class="email-cell">${escHtml(email)}</span></td>
    <td><span class="role-badge ${roleClass}">${escHtml(role)}</span></td>
    <td><span class="date-cell">${escHtml(date)}</span></td>
    <td>
      <div class="action-wrap">
        <button class="btn-approve" data-id="${escHtml(String(user.id))}">✓ Approve</button>
        <button class="btn-reject"  data-id="${escHtml(String(user.id))}">✕ Reject</button>
      </div>
    </td>`;
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ── Confirm modal ───────────────────────────────────────── */
let pendingAction = null;

function confirmAction(type, user) {
  const modal   = document.getElementById('confirm-modal');
  const iconEl  = document.getElementById('modal-icon');
  const titleEl = document.getElementById('modal-title');
  const bodyEl  = document.getElementById('modal-body');
  const confirmBtn = document.getElementById('modal-confirm');

  const name = user.name || user.email || 'this user';

  if (type === 'approve') {
    iconEl.textContent  = '✓';
    titleEl.textContent = 'Approve User';
    bodyEl.textContent  = `Grant access to ${name}? They will be able to log in immediately.`;
    confirmBtn.className = 'btn-confirm approve';
    confirmBtn.textContent = 'Yes, Approve';
  } else {
    iconEl.textContent  = '🗑';
    titleEl.textContent = 'Reject & Delete User';
    bodyEl.textContent  = `Permanently delete ${name}'s account? This cannot be undone.`;
    confirmBtn.className = 'btn-confirm reject';
    confirmBtn.textContent = 'Yes, Delete';
  }

  pendingAction = { type, user };
  modal.classList.add('open');
}

function closeModal() {
  document.getElementById('confirm-modal').classList.remove('open');
  pendingAction = null;
}

/* ── Approve / Reject API calls ──────────────────────────── */
async function executeAction(type, user) {
  const userId = user.id;
  const row = document.querySelector(`tr[data-id="${userId}"]`);

  // Disable buttons during request
  if (row) {
    row.querySelectorAll('button').forEach(b => (b.disabled = true));
  }

  try {
    if (type === 'approve') {
      await apiFetch(`/admin/verify/${userId}`, { method: 'POST' });
      toast(`✓ ${user.name || user.email} approved successfully`, 'success');
    } else {
      await apiFetch(`/admin/delete/${userId}`, { method: 'DELETE' });
      toast(`🗑 ${user.name || user.email} removed`, 'error');
    }

    // Remove from master list
    allPendingUsers = allPendingUsers.filter(u => u.id !== userId);

    // Animate row out then re-render
    if (row) {
      row.classList.add('row-exit');
      row.addEventListener('animationend', () => {
        renderTable();
        // Update pending stat
        animateCount('stat-pending-val', allPendingUsers.length);
        document.getElementById('stat-pending-sub').textContent =
          allPendingUsers.length > 0
            ? `${allPendingUsers.length} awaiting review`
            : 'Queue is clear ✓';

        const badge = document.getElementById('sidebar-pending-count');
        if (badge) {
          badge.textContent = allPendingUsers.length;
          badge.dataset.count = allPendingUsers.length;
        }
      }, { once: true });
    } else {
      renderTable();
    }
  } catch (err) {
    toast(`Error: ${err.message}`, 'error');
    // Re-enable buttons
    if (row) {
      row.querySelectorAll('button').forEach(b => (b.disabled = false));
    }
  }
}

/* ── Event wiring ────────────────────────────────────────── */
function wireEvents() {
  // Logout
  document.getElementById('logout-btn')?.addEventListener('click', () => {
    removeToken();
    window.location.replace('login.html');
  });

  // Refresh button
  const refreshBtn = document.getElementById('refresh-btn');
  refreshBtn?.addEventListener('click', async () => {
    refreshBtn.classList.add('spinning');
    await loadPendingUsers();
    refreshBtn.classList.remove('spinning');
  });

  // Retry button
  document.getElementById('retry-btn')?.addEventListener('click', loadPendingUsers);

  // Filter input
  document.getElementById('filter-input')?.addEventListener('input', e => {
    filterText = e.target.value.trim();
    renderTable();
  });

  // Role chips
  document.querySelectorAll('.chip[data-role]').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.chip[data-role]').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      filterRole = chip.dataset.role;
      renderTable();
    });
  });

  // Modal confirm
  document.getElementById('modal-confirm')?.addEventListener('click', async () => {
    if (!pendingAction) return;
    const { type, user } = pendingAction;
    closeModal();
    await executeAction(type, user);
  });

  // Modal cancel & backdrop click
  document.getElementById('modal-cancel')?.addEventListener('click', closeModal);
  document.getElementById('confirm-modal')?.addEventListener('click', e => {
    if (e.target === e.currentTarget) closeModal();
  });

  // Sidebar nav highlight
  document.querySelectorAll('.nav-item[data-section]').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      item.classList.add('active');
    });
  });
}

/* ── Boot ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  populateSidebarUser();
  startClock();
  wireEvents();
  loadStats();
  loadPendingUsers();
});