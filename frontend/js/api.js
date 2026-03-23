// ══════════════════════════════════════════════════════════
//  api.js  —  Centralized API communication layer
// ══════════════════════════════════════════════════════════

const API_BASE = 'http://localhost:8000';

// ── Token management ─────────────────────────────────────

export function getToken() {
  return localStorage.getItem('token');
}

export function setToken(token) {
  localStorage.setItem('token', token);
}

export function removeToken() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem('user'));
  } catch {
    return null;
  }
}

export function setUser(user) {
  localStorage.setItem('user', JSON.stringify(user));
}

export function isLoggedIn() {
  return !!getToken();
}

// ── Core fetch wrapper ────────────────────────────────────

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    removeToken();
    window.location.href = '/login.html';
    throw new Error('Unauthorized');
  }

  // 204 No Content
  if (res.status === 204) return null;

  const data = await res.json();
  if (!res.ok) {
    const msg = data.detail || JSON.stringify(data);
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

// ── Auth ──────────────────────────────────────────────────

export const auth = {
  register: (payload) => apiFetch('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => apiFetch('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
};

// ── Users ─────────────────────────────────────────────────

export const users = {
  me: () => apiFetch('/users/me'),
  update: (payload) => apiFetch('/users/me', { method: 'PUT', body: JSON.stringify(payload) }),
  getById: (id) => apiFetch(`/users/${id}`),
  getAlumni: () => apiFetch('/users/alumni'),
  getStudents: () => apiFetch('/users/students'),
  // Admin
  listAll: () => apiFetch('/users/'),
  deleteUser: (id) => apiFetch(`/users/${id}`, { method: 'DELETE' }),
};

// ── Posts ─────────────────────────────────────────────────

export const posts = {
  getFeed: (skip = 0, limit = 20) => apiFetch(`/posts?skip=${skip}&limit=${limit}`),
  getUserPosts: (userId) => apiFetch(`/posts/user/${userId}`),
  create: (payload) => apiFetch('/posts', { method: 'POST', body: JSON.stringify(payload) }),
  delete: (id) => apiFetch(`/posts/${id}`, { method: 'DELETE' }),
};

// ── Comments ──────────────────────────────────────────────

export const comments = {
  create: (payload) => apiFetch('/comments', { method: 'POST', body: JSON.stringify(payload) }),
  delete: (id) => apiFetch(`/comments/${id}`, { method: 'DELETE' }),
};

// ── Likes ─────────────────────────────────────────────────

export const likes = {
  toggle: (postId) => apiFetch('/likes', { method: 'POST', body: JSON.stringify({ post_id: postId }) }),
};

// ── Messages ──────────────────────────────────────────────

export const messages = {
  send: (payload) => apiFetch('/messages', { method: 'POST', body: JSON.stringify(payload) }),
  getConversation: (userId) => apiFetch(`/messages/${userId}`),
  getConversations: () => apiFetch('/messages/conversations'),
};

// ── Mentorship ────────────────────────────────────────────

export const mentorship = {
  send: (payload) => apiFetch('/mentorship', { method: 'POST', body: JSON.stringify(payload) }),
  respond: (id, status) => apiFetch(`/mentorship/${id}`, { method: 'PUT', body: JSON.stringify({ status }) }),
  myRequests: () => apiFetch('/mentorship/my-requests'),
  pending: () => apiFetch('/mentorship/pending'),
};

// ── AI ────────────────────────────────────────────────────

export const ai = {
  recommendations: () => apiFetch('/ai/recommendations'),
  chatbot: (message) => apiFetch('/ai/chatbot', { method: 'POST', body: JSON.stringify({ message }) }),
};

// ── Helpers ───────────────────────────────────────────────

/** Show a toast notification */
export function toast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(el);

  setTimeout(() => {
    el.style.animation = 'fadeOut 0.3s forwards';
    setTimeout(() => el.remove(), 300);
  }, duration);
}

/** Format relative time */
export function timeAgo(dateStr) {
  const now = new Date();
  const then = new Date(dateStr);
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return then.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

/** Get initials from name */
export function initials(name = '') {
  return name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?';
}

/** Create avatar HTML */
export function avatarHTML(user, size = 'md') {
  const sizeClass = { sm: '32px', md: '46px', lg: '72px' }[size] || '46px';
  if (user.profile_picture) {
    return `<img src="${user.profile_picture}" alt="${user.name}" style="width:${sizeClass};height:${sizeClass};border-radius:50%;object-fit:cover;">`;
  }
  const init = initials(user.name);
  const colors = ['#0a66c2','#057642','#b45309','#6d28d9','#be185d','#0e7490'];
  const bg = colors[user.id % colors.length];
  return `<div style="width:${sizeClass};height:${sizeClass};border-radius:50%;background:${bg};color:white;display:grid;place-items:center;font-weight:700;font-size:${parseInt(sizeClass)*0.38}px;font-family:'Sora',sans-serif;">${init}</div>`;
}

/** Guard: redirect to login if not authenticated */
export function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = '/login.html';
    return false;
  }
  return true;
}

/** Guard: redirect to dashboard if already authenticated */
export function redirectIfAuth() {
  if (isLoggedIn()) {
    window.location.href = '/dashboard.html';
    return true;
  }
  return false;
}

// ── Search ────────────────────────────────────────────────

export const search = {
  all:   (q, type='all', skip=0, limit=20) =>
    apiFetch(`/search?q=${encodeURIComponent(q)}&type=${type}&skip=${skip}&limit=${limit}`),
  users: (q, role='', limit=10) =>
    apiFetch(`/search/users?q=${encodeURIComponent(q)}${role ? '&role='+role : ''}&limit=${limit}`),
};

// ── Notifications ─────────────────────────────────────────

export const notifications = {
  list:       (skip=0, limit=30) => apiFetch(`/notifications?skip=${skip}&limit=${limit}`),
  unreadCount: ()                 => apiFetch('/notifications/unread'),
  readAll:    ()                  => apiFetch('/notifications/read-all', { method:'PUT' }),
  readOne:    (id)                => apiFetch(`/notifications/${id}/read`, { method:'PUT' }),
};

// ── Upload ────────────────────────────────────────────────

export const upload = {
  avatar: (file) => {
    const form = new FormData();
    form.append('file', file);
    const token = getToken();
    return fetch(`${API_BASE}/upload/avatar`, {
      method:  'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body:    form,
    }).then(async r => {
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail || 'Upload failed'); }
      return r.json();
    });
  },
  postImage: (file) => {
    const form = new FormData();
    form.append('file', file);
    const token = getToken();
    return fetch(`${API_BASE}/upload/post-image`, {
      method:  'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body:    form,
    }).then(async r => {
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail || 'Upload failed'); }
      return r.json();
    });
  },
};

// ── Password reset ────────────────────────────────────────

export const passwordReset = {
  forgot: (email)              =>
    apiFetch('/auth/forgot-password',  { method:'POST', body:JSON.stringify({ email }) }),
  reset:  (token, new_password) =>
    apiFetch('/auth/reset-password',   { method:'POST', body:JSON.stringify({ token, new_password }) }),
  change: (current_password, new_password) =>
    apiFetch('/auth/change-password',  { method:'POST', body:JSON.stringify({ current_password, new_password }) }),
};
