// ══════════════════════════════════════════════════════════
//  chat.js  —  One-to-one messaging page logic
//  Imported by chat.html via <script type="module" src="js/chat.js">
// ══════════════════════════════════════════════════════════
import {
  requireAuth, getUser, removeToken,
  messages as msgApi, users,
  toast, timeAgo, initials
} from './api.js';

if (!requireAuth()) throw new Error('Not authenticated');

const currentUser       = getUser();
let   activeChatUserId  = null;
let   pollTimer         = null;
let   lastMsgCount      = 0;
let   allUsersCache     = [];

// ══════════════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════════════
setupNavbar();
await loadConversations();

// Auto-open from ?user=ID
const urlUserId = new URLSearchParams(window.location.search).get('user');
if (urlUserId) await openChat(parseInt(urlUserId));

setupChatInput();
setupNewChatModal();
setupSearch();

// ══════════════════════════════════════════════════════════
//  NAVBAR
// ══════════════════════════════════════════════════════════
function setupNavbar() {
  const el = document.getElementById('nav-user-avatar');
  if (el) el.innerHTML = currentUser.profile_picture
    ? `<img src="${esc(currentUser.profile_picture)}" alt="" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`
    : initials(currentUser.name);

  document.getElementById('logout-btn')?.addEventListener('click', () => {
    removeToken();
    window.location.href = 'login.html';
  });
}

// ══════════════════════════════════════════════════════════
//  CONVERSATIONS LIST
// ══════════════════════════════════════════════════════════
async function loadConversations() {
  const listEl = document.getElementById('chat-list');
  if (!listEl) return;

  try {
    const convos = await msgApi.getConversations();
    if (!convos.length) {
      listEl.innerHTML = `
        <div style="padding:24px;text-align:center;color:var(--text-muted);font-size:0.875rem;">
          No conversations yet.<br>
          <button onclick="document.getElementById('new-chat-modal').classList.add('open')"
                  class="btn btn-primary btn-sm" style="margin-top:12px;">
            Start a Conversation
          </button>
        </div>`;
      return;
    }

    listEl.innerHTML = convos.map(c => `
      <div class="chat-list-item" data-user-id="${c.user.id}" id="convo-${c.user.id}">
        <div class="chat-list-avatar">
          ${c.user.profile_picture
            ? `<img src="${esc(c.user.profile_picture)}" alt="">`
            : initials(c.user.name)}
        </div>
        <div class="chat-list-info">
          <div class="chat-list-name">${esc(c.user.name)}</div>
          <div class="chat-list-preview">${esc(c.last_message || '')}</div>
        </div>
        ${c.unread_count ? `<div class="unread-badge">${c.unread_count}</div>` : ''}
      </div>`).join('');

    listEl.querySelectorAll('[data-user-id]').forEach(item => {
      item.addEventListener('click', () => {
        openChat(parseInt(item.dataset.userId));
        history.replaceState(null, '', `?user=${item.dataset.userId}`);
      });
    });
  } catch {
    listEl.innerHTML = '<div style="padding:16px;color:var(--accent-red);">Failed to load conversations.</div>';
  }
}

// ══════════════════════════════════════════════════════════
//  OPEN CHAT
// ══════════════════════════════════════════════════════════
async function openChat(userId) {
  activeChatUserId = userId;
  if (pollTimer) clearInterval(pollTimer);

  document.querySelectorAll('.chat-list-item').forEach(el => el.classList.remove('active'));
  document.getElementById(`convo-${userId}`)?.classList.add('active');
  document.querySelector(`#convo-${userId} .unread-badge`)?.remove();

  document.getElementById('chat-placeholder').style.display = 'none';
  document.getElementById('chat-main').style.display        = 'flex';

  // Ensure conversation item exists in sidebar (for new chats from modal)
  if (!document.getElementById(`convo-${userId}`)) {
    await loadConversations();
    document.getElementById(`convo-${userId}`)?.classList.add('active');
  }

  try {
    const chatUser = await users.getById(userId);
    document.getElementById('chat-header-info').innerHTML = `
      <div class="chat-list-avatar" style="width:40px;height:40px;">
        ${chatUser.profile_picture
          ? `<img src="${esc(chatUser.profile_picture)}" alt="">`
          : initials(chatUser.name)}
      </div>
      <div style="flex:1;">
        <div class="chat-main-name">${esc(chatUser.name)}</div>
        <div class="chat-main-role">
          ${capitalize(chatUser.role)}${chatUser.college ? ' · ' + esc(chatUser.college) : ''}
        </div>
      </div>
      <a href="profile.html?id=${chatUser.id}" class="btn btn-ghost btn-sm">View Profile</a>`;
  } catch { /* ignore */ }

  await renderMessages(userId);

  // Poll every 3 seconds for new messages
  pollTimer = setInterval(async () => {
    if (activeChatUserId === userId) await renderMessages(userId, true);
  }, 3000);
}

// ══════════════════════════════════════════════════════════
//  RENDER MESSAGES
// ══════════════════════════════════════════════════════════
async function renderMessages(userId, silent = false) {
  const container = document.getElementById('chat-messages');
  if (!container) return;

  try {
    const msgs = await msgApi.getConversation(userId);
    if (msgs.length === lastMsgCount && silent) return;
    lastMsgCount = msgs.length;

    if (!msgs.length) {
      container.innerHTML = '<div class="chat-empty"><div class="empty-icon">👋</div><p>Say hello!</p></div>';
      return;
    }

    const wasAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 80;

    container.innerHTML = msgs.map(m => {
      const sent = m.sender_id === currentUser.id;
      return `
        <div class="message-bubble ${sent ? 'sent' : 'received'}">
          <div class="message-text">${esc(m.content)}</div>
          <div class="message-time">${timeAgo(m.created_at)}${sent && m.is_read ? ' · ✓✓' : ''}</div>
        </div>`;
    }).join('');

    if (!silent || wasAtBottom) container.scrollTop = container.scrollHeight;

    // Update sidebar preview
    const lastMsg = msgs[msgs.length - 1];
    const preview = document.querySelector(`#convo-${userId} .chat-list-preview`);
    if (preview && lastMsg) preview.textContent = lastMsg.content.slice(0, 60);
  } catch { /* silent fail on poll */ }
}

// ══════════════════════════════════════════════════════════
//  SEND MESSAGE
// ══════════════════════════════════════════════════════════
function setupChatInput() {
  const input   = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');

  async function send() {
    if (!activeChatUserId) { toast('Select a conversation first.', 'error'); return; }
    const content = input?.value.trim();
    if (!content) return;

    input.value = '';
    input.style.height = '';

    try {
      await msgApi.send({ receiver_id: activeChatUserId, content });
      await renderMessages(activeChatUserId);
    } catch (err) { toast(err.message, 'error'); }
  }

  sendBtn?.addEventListener('click', send);
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });

  // Auto-resize textarea
  input?.addEventListener('input', () => {
    input.style.height = '';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
}

// ══════════════════════════════════════════════════════════
//  NEW CHAT MODAL
// ══════════════════════════════════════════════════════════
function setupNewChatModal() {
  const modal    = document.getElementById('new-chat-modal');
  const closeBtn = document.getElementById('new-chat-close');
  const openBtn  = document.getElementById('new-chat-btn');

  openBtn?.addEventListener('click', async () => {
    modal?.classList.add('open');
    if (!allUsersCache.length) {
      try {
        const [alumni, students] = await Promise.all([users.getAlumni(), users.getStudents()]);
        allUsersCache = [...alumni, ...students].filter(u => u.id !== currentUser.id);
      } catch { toast('Could not load users.', 'error'); return; }
    }
    renderUserResults(allUsersCache);
  });

  closeBtn?.addEventListener('click', () => modal?.classList.remove('open'));
  modal?.addEventListener('click', e => { if (e.target === modal) modal.classList.remove('open'); });

  document.getElementById('user-search-input')?.addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    renderUserResults(allUsersCache.filter(u =>
      u.name.toLowerCase().includes(q) ||
      (u.college || '').toLowerCase().includes(q) ||
      (u.skills  || '').toLowerCase().includes(q)
    ));
  });
}

function renderUserResults(list) {
  const el = document.getElementById('user-search-results');
  if (!el) return;

  if (!list.length) {
    el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);">No users found.</div>';
    return;
  }

  el.innerHTML = list.map(u => `
    <div class="chat-list-item" data-uid="${u.id}" style="cursor:pointer;">
      <div class="chat-list-avatar">
        ${u.profile_picture ? `<img src="${esc(u.profile_picture)}" alt="">` : initials(u.name)}
      </div>
      <div class="chat-list-info">
        <div class="chat-list-name">${esc(u.name)}</div>
        <div class="chat-list-preview">${capitalize(u.role)}${u.college ? ' · ' + esc(u.college) : ''}</div>
      </div>
      <span class="role-badge ${u.role}">${capitalize(u.role)}</span>
    </div>`).join('');

  el.querySelectorAll('[data-uid]').forEach(item => {
    item.addEventListener('click', () => {
      document.getElementById('new-chat-modal')?.classList.remove('open');
      openChat(parseInt(item.dataset.uid));
      history.replaceState(null, '', `?user=${item.dataset.uid}`);
    });
  });
}

// ══════════════════════════════════════════════════════════
//  SIDEBAR SEARCH FILTER
// ══════════════════════════════════════════════════════════
function setupSearch() {
  document.getElementById('chat-search')?.addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('.chat-list-item').forEach(item => {
      const name = item.querySelector('.chat-list-name')?.textContent.toLowerCase() || '';
      item.style.display = name.includes(q) ? '' : 'none';
    });
  });
}

// ══════════════════════════════════════════════════════════
//  UTILS
// ══════════════════════════════════════════════════════════
function esc(s) {
  return String(s || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function capitalize(s) { return s ? s[0].toUpperCase() + s.slice(1) : ''; }
