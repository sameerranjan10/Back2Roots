// ══════════════════════════════════════════════════════════
//  dashboard.js — Complete dashboard module
//  Feed · Posts · Comments · Likes · Search · Notifications
//  Alumni Browse · Mentorship · Admin · Chatbot · File Upload
// ══════════════════════════════════════════════════════════
import {
  requireAuth, getUser, removeToken,
  posts, comments, likes, mentorship, ai, users,
  search, notifications, upload,
  toast, timeAgo, initials
} from './api.js';

// ── State ─────────────────────────────────────────────────
const currentUser   = (() => { if (!requireAuth()) throw new Error(); return getUser(); })();
let feedSkip        = 0;
let feedExhausted   = false;
let loadingFeed     = false;
let searchTimer     = null;

// ══════════════════════════════════════════════════════════
//  BOOT
// ══════════════════════════════════════════════════════════
setupNavbar();
setupLeftSidebar();
setupPostCreation();
setupMentorshipModal();
setupChatbot();
setupInfiniteScroll();
setupSearchBar();

// Load data for visible section
await loadFeed(true);
await loadRightSidebar();
await loadNotifications();
startNotificationPolling();

// Section-specific lazy loaders
window.addEventListener('hashchange', onHashChange);
onHashChange();

// ══════════════════════════════════════════════════════════
//  NAVBAR
// ══════════════════════════════════════════════════════════
function setupNavbar() {
  const avatarEl = document.getElementById('nav-user-avatar');
  if (avatarEl) avatarEl.innerHTML = currentUser.profile_picture
    ? `<img src="${esc(currentUser.profile_picture)}" alt="" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`
    : initials(currentUser.name);

  const nameEl = document.getElementById('nav-user-name');
  const roleEl = document.getElementById('nav-user-role');
  if (nameEl) nameEl.textContent = currentUser.name;
  if (roleEl) roleEl.textContent = capitalize(currentUser.role);

  document.getElementById('logout-btn')?.addEventListener('click', () => {
    removeToken(); window.location.href = 'login.html';
  });
  document.getElementById('mobile-logout')?.addEventListener('click', () => {
    removeToken(); window.location.href = 'login.html';
  });

  // Show admin items
  if (currentUser.role === 'admin') {
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = '');
  }

  // Mobile profile summary
  const mobProfile = document.getElementById('mobile-profile-summary');
  if (mobProfile) {
    mobProfile.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:42px;height:42px;border-radius:50%;background:var(--primary);color:white;
                    display:grid;place-items:center;font-weight:700;font-size:16px;flex-shrink:0;overflow:hidden;">
          ${currentUser.profile_picture
            ? `<img src="${esc(currentUser.profile_picture)}" alt="" style="width:100%;height:100%;object-fit:cover;">`
            : initials(currentUser.name)}
        </div>
        <div>
          <div style="font-weight:600;font-size:0.9rem;">${esc(currentUser.name)}</div>
          <div style="font-size:0.78rem;color:var(--text-muted);">${capitalize(currentUser.role)}</div>
        </div>
      </div>`;
  }

  // Mark all read button
  document.getElementById('mark-all-read')?.addEventListener('click', async () => {
    try {
      await notifications.readAll();
      document.querySelectorAll('.notif-item').forEach(el => el.classList.add('read'));
      const badge = document.getElementById('notif-badge');
      if (badge) { badge.textContent = ''; badge.classList.remove('show'); }
      toast('All notifications marked as read', 'info');
    } catch (err) { toast(err.message, 'error'); }
  });
}

// ══════════════════════════════════════════════════════════
//  LEFT SIDEBAR
// ══════════════════════════════════════════════════════════
function setupLeftSidebar() {
  const el = document.getElementById('profile-sidebar-card');
  if (!el) return;
  const skillCount = (currentUser.skills || '').split(',').filter(Boolean).length;
  el.innerHTML = `
    <div class="profile-card-banner"></div>
    <div class="profile-card-info">
      <a href="profile.html" class="profile-card-avatar"
         style="display:flex;align-items:center;justify-content:center;text-decoration:none;">
        ${currentUser.profile_picture
          ? `<img src="${esc(currentUser.profile_picture)}" alt="">`
          : `<span style="font-size:26px;font-weight:700;">${initials(currentUser.name)}</span>`}
      </a>
      <div class="profile-card-name">${esc(currentUser.name)}</div>
      <div class="profile-card-role">
        <span class="role-badge ${currentUser.role}">${capitalize(currentUser.role)}</span>
      </div>
      <div class="profile-card-college">${esc(currentUser.college || 'College not set')}</div>
    </div>
    <hr class="profile-card-divider">
    <div style="padding:0 16px 16px;">
      <div class="profile-stat-row">
        <span class="label">Skills</span>
        <span class="value">${skillCount}</span>
      </div>
      <div style="margin-top:6px;">
        <a href="profile.html" style="font-size:0.8rem;color:var(--primary);">View full profile →</a>
      </div>
    </div>`;
}

// ══════════════════════════════════════════════════════════
//  LIVE SEARCH BAR
// ══════════════════════════════════════════════════════════
function setupSearchBar() {
  const input    = document.getElementById('global-search-input');
  const dropdown = document.getElementById('search-dropdown');
  if (!input || !dropdown) return;

  input.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = input.value.trim();
    if (!q) { dropdown.classList.remove('open'); dropdown.innerHTML = ''; return; }
    searchTimer = setTimeout(() => runSearch(q), 300);
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Escape') { dropdown.classList.remove('open'); input.blur(); }
    if (e.key === 'Enter' && input.value.trim()) {
      dropdown.classList.remove('open');
      // Navigate to full results (show in feed area)
      showSearchResults(input.value.trim());
    }
  });

  document.addEventListener('click', e => {
    if (!input.contains(e.target) && !dropdown.contains(e.target))
      dropdown.classList.remove('open');
  });
}

async function runSearch(q) {
  const dropdown = document.getElementById('search-dropdown');
  try {
    const data = await search.all(q, 'all', 0, 5);
    const items = [];

    data.users.slice(0, 4).forEach(u => {
      items.push(`
        <a href="profile.html?id=${u.id}" class="search-result-item" style="text-decoration:none;">
          <div style="width:32px;height:32px;border-radius:50%;background:var(--primary);color:white;
                      display:grid;place-items:center;font-size:12px;font-weight:700;flex-shrink:0;overflow:hidden;">
            ${u.profile_picture
              ? `<img src="${esc(u.profile_picture)}" alt="" style="width:100%;height:100%;object-fit:cover;">`
              : initials(u.name)}
          </div>
          <div>
            <div style="font-weight:600;font-size:0.875rem;color:var(--text);">${esc(u.name)}</div>
            <div style="font-size:0.75rem;color:var(--text-muted);">${capitalize(u.role)}${u.college ? ' · ' + esc(u.college) : ''}</div>
          </div>
          <span class="role-badge ${u.role}" style="margin-left:auto;">${capitalize(u.role)}</span>
        </a>`);
    });

    data.posts.slice(0, 2).forEach(p => {
      items.push(`
        <div class="search-result-item" onclick="highlightPost(${p.id})" style="cursor:pointer;">
          <span style="font-size:18px;">📝</span>
          <div>
            <div style="font-weight:600;font-size:0.8rem;color:var(--text);">${esc(p.author?.name || 'Post')}</div>
            <div style="font-size:0.75rem;color:var(--text-muted);">${esc(p.content.slice(0, 60))}…</div>
          </div>
        </div>`);
    });

    if (!items.length) {
      items.push(`<div style="padding:14px 16px;color:var(--text-muted);font-size:0.875rem;">No results for "${esc(q)}"</div>`);
    }

    dropdown.innerHTML = items.join('');
    dropdown.classList.add('open');
  } catch { /* silent */ }
}

async function showSearchResults(q) {
  // Switch to feed section and show results
  window.location.hash = '';
  window.showSection?.('feed');
  const feedEl = document.getElementById('feed-container');
  if (!feedEl) return;
  feedEl.innerHTML = `<div style="padding:16px 0;font-size:0.9rem;color:var(--text-secondary);">
    Search results for "<strong>${esc(q)}</strong>"</div><div class="loading-spinner"></div>`;
  try {
    const data = await search.all(q, 'all', 0, 20);
    feedEl.innerHTML = `<div style="padding:12px 0 4px;font-size:0.9rem;color:var(--text-secondary);">
      Found ${data.total_users} people · ${data.total_posts} posts for "<strong>${esc(q)}</strong>"
      <a href="dashboard.html" style="float:right;font-size:0.8rem;">Clear ✕</a></div>`;

    if (data.users.length) {
      feedEl.insertAdjacentHTML('beforeend', `<div class="card" style="margin-bottom:12px;">
        <div class="card-header"><h3>👥 People</h3></div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;padding:14px;">
          ${data.users.map(u => `
            <a href="profile.html?id=${u.id}" style="display:flex;align-items:center;gap:8px;
               padding:10px;border:1px solid var(--border);border-radius:var(--radius);text-decoration:none;
               color:inherit;transition:var(--transition);" onmouseover="this.style.background='var(--bg)'"
               onmouseout="this.style.background=''">
              <div style="width:36px;height:36px;border-radius:50%;background:var(--primary);color:white;
                          display:grid;place-items:center;font-size:13px;font-weight:700;flex-shrink:0;overflow:hidden;">
                ${u.profile_picture ? `<img src="${esc(u.profile_picture)}" alt="" style="width:100%;height:100%;object-fit:cover;">` : initials(u.name)}
              </div>
              <div style="min-width:0;">
                <div style="font-weight:600;font-size:0.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${esc(u.name)}</div>
                <div style="font-size:0.72rem;color:var(--text-muted);">${capitalize(u.role)}</div>
              </div>
            </a>`).join('')}
        </div>
      </div>`);
    }

    if (data.posts.length) {
      data.posts.forEach(p => feedEl.insertAdjacentHTML('beforeend', renderPostCard(p)));
      bindFeedActions();
    }

    if (!data.users.length && !data.posts.length) {
      feedEl.insertAdjacentHTML('beforeend', `<div class="empty-state">
        <div class="empty-icon">🔍</div><h3>No results found</h3>
        <p>Try different keywords.</p></div>`);
    }
  } catch (err) { toast(err.message, 'error'); }
}

window.highlightPost = function(postId) {
  const el = document.querySelector(`[data-post-id="${postId}"]`);
  if (el) { el.scrollIntoView({ behavior:'smooth', block:'center' }); el.style.outline = '2px solid var(--primary)'; setTimeout(() => el.style.outline = '', 2000); }
};

// ══════════════════════════════════════════════════════════
//  NOTIFICATIONS
// ══════════════════════════════════════════════════════════
async function loadNotifications() {
  const listEl  = document.getElementById('notif-list');
  const badge   = document.getElementById('notif-badge');
  if (!listEl) return;

  try {
    const [notifList, { unread_count }] = await Promise.all([
      notifications.list(0, 20),
      notifications.unreadCount(),
    ]);

    if (badge) {
      badge.textContent = unread_count > 9 ? '9+' : String(unread_count);
      badge.classList.toggle('show', unread_count > 0);
    }

    if (!notifList.length) {
      listEl.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.875rem;">No notifications yet.</div>';
      return;
    }

    const icons = { like:'👍', comment:'💬', mentorship_request:'🎓', mentorship_update:'✅', message:'✉️', system:'📢' };

    listEl.innerHTML = notifList.map(n => `
      <div class="notif-item ${n.is_read ? 'read' : 'unread'}" data-notif-id="${n.id}"
           onclick="handleNotifClick(${n.id},'${esc(n.link || '')}')"
           style="display:flex;align-items:flex-start;gap:10px;padding:12px 16px;cursor:pointer;
                  border-bottom:1px solid var(--border);transition:var(--transition);
                  ${n.is_read ? '' : 'background:var(--primary-light);'}">
        <span style="font-size:18px;flex-shrink:0;">${icons[n.type] || '📢'}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-size:0.85rem;color:var(--text);${n.is_read ? '' : 'font-weight:600;'}">${esc(n.message)}</div>
          <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px;">${timeAgo(n.created_at)}</div>
        </div>
        ${!n.is_read ? '<div style="width:8px;height:8px;border-radius:50%;background:var(--primary);flex-shrink:0;margin-top:4px;"></div>' : ''}
      </div>`).join('');
  } catch { /* silently fail */ }
}

window.handleNotifClick = async function(id, link) {
  try { await notifications.readOne(id); } catch { /* ignore */ }
  const el = document.querySelector(`[data-notif-id="${id}"]`);
  if (el) { el.style.background = ''; el.classList.add('read'); }
  if (link) window.location.href = link;
};

function startNotificationPolling() {
  setInterval(async () => {
    try {
      const { unread_count } = await notifications.unreadCount();
      const badge = document.getElementById('notif-badge');
      if (badge) {
        badge.textContent = unread_count > 9 ? '9+' : String(unread_count);
        badge.classList.toggle('show', unread_count > 0);
      }
    } catch { /* ignore */ }
  }, 30_000); // every 30s
}

// ══════════════════════════════════════════════════════════
//  HASH-BASED SECTION ROUTING
// ══════════════════════════════════════════════════════════
async function onHashChange() {
  const hash = window.location.hash.replace('#', '');
  const sections = ['feed', 'alumni', 'mentorship', 'admin'];
  sections.forEach(s => {
    const el = document.getElementById(`section-${s}`);
    if (el) el.style.display = s === (hash || 'feed') ? 'block' : 'none';
  });

  // Sidebar active state
  document.querySelectorAll('.sidebar-nav-item').forEach(el => el.classList.remove('active'));

  if (hash === 'alumni' && !document.getElementById('alumni-browse-grid').children.length) {
    await loadAlumniBrowse();
  } else if (hash === 'mentorship') {
    await loadMentorshipPanel();
  } else if (hash === 'admin' && currentUser.role === 'admin') {
    await loadAdminPanel();
  }
}

// Expose for inline HTML onclick
window.showSection = function(name) {
  window.location.hash = name === 'feed' ? '' : name;
};

// ══════════════════════════════════════════════════════════
//  POST CREATION (with file upload)
// ══════════════════════════════════════════════════════════
function setupPostCreation() {
  const triggerInput = document.getElementById('post-trigger');
  const composeArea  = document.getElementById('post-compose-area');
  const textarea     = document.getElementById('post-textarea');
  const imageUrl     = document.getElementById('post-image-url');
  const imageFile    = document.getElementById('post-image-file');
  const submitBtn    = document.getElementById('post-submit');
  const cancelBtn    = document.getElementById('post-cancel');
  const avatarEl     = document.getElementById('create-post-avatar');

  if (avatarEl) avatarEl.innerHTML = currentUser.profile_picture
    ? `<img src="${esc(currentUser.profile_picture)}" alt="" style="width:44px;height:44px;border-radius:50%;object-fit:cover;">`
    : initials(currentUser.name);

  triggerInput?.addEventListener('focus', () => {
    composeArea?.classList.add('open'); textarea?.focus();
  });
  cancelBtn?.addEventListener('click', () => {
    composeArea?.classList.remove('open');
    if (textarea)   textarea.value   = '';
    if (imageUrl)   imageUrl.value   = '';
    if (imageFile)  imageFile.value  = '';
    window.clearImagePreview?.();
  });

  // File input → upload then put URL in imageUrl field
  imageFile?.addEventListener('change', async () => {
    const file = imageFile.files[0];
    if (!file) return;
    submitBtn.disabled = true; submitBtn.textContent = 'Uploading…';
    try {
      const res = await upload.postImage(file);
      if (imageUrl) imageUrl.value = res.url;
      toast('Image uploaded!', 'success');
    } catch (err) {
      toast('Upload failed: ' + err.message, 'error');
      imageFile.value = '';
    } finally {
      submitBtn.disabled = false; submitBtn.textContent = 'Post';
    }
  });

  submitBtn?.addEventListener('click', async () => {
    const content = textarea?.value.trim();
    if (!content) { toast('Post cannot be empty.', 'error'); return; }
    submitBtn.disabled = true; submitBtn.textContent = 'Posting…';
    try {
      await posts.create({ content, image_url: imageUrl?.value.trim() || null });
      if (textarea)   textarea.value  = '';
      if (imageUrl)   imageUrl.value  = '';
      if (imageFile)  imageFile.value = '';
      window.clearImagePreview?.();
      composeArea?.classList.remove('open');
      feedSkip = 0; feedExhausted = false;
      await loadFeed(true);
      toast('Posted! 🎉', 'success');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      submitBtn.disabled = false; submitBtn.textContent = 'Post';
    }
  });
}

// ══════════════════════════════════════════════════════════
//  FEED
// ══════════════════════════════════════════════════════════
async function loadFeed(reset = false) {
  if (loadingFeed || (feedExhausted && !reset)) return;
  const feedEl  = document.getElementById('feed-container');
  const endMsg  = document.getElementById('feed-end-msg');
  if (!feedEl || feedEl.closest('[style*="display: none"]')) return;

  if (reset) {
    feedSkip = 0; feedExhausted = false;
    feedEl.innerHTML = '<div class="loading-spinner"></div>';
    if (endMsg) endMsg.style.display = 'none';
  }

  loadingFeed = true;
  try {
    const batch = await posts.getFeed(feedSkip, 10);
    feedSkip += batch.length;
    if (batch.length < 10) { feedExhausted = true; if (endMsg && feedSkip > 0) endMsg.style.display = 'block'; }

    if (reset) feedEl.innerHTML = '';

    if (!batch.length && feedSkip === 0) {
      feedEl.innerHTML = `<div class="empty-state">
        <div class="empty-icon">📰</div><h3>No posts yet</h3>
        <p>Be the first to share something!</p></div>`;
      return;
    }

    batch.forEach(p => feedEl.insertAdjacentHTML('beforeend', renderPostCard(p)));
    bindFeedActions();
  } catch (err) { toast('Failed to load feed.', 'error'); }
  finally { loadingFeed = false; }
}

function renderPostCard(post) {
  const a      = post.author || {};
  const isOwn  = a.id === currentUser.id;
  const isAdm  = currentUser.role === 'admin';
  const badges = (a.skills||'').split(',').filter(Boolean).slice(0,2)
    .map(s=>`<span class="skill-tag" style="font-size:0.7rem;padding:1px 7px;">${esc(s.trim())}</span>`).join('');

  const commentsHtml = (post.comments||[]).slice(0,2).map(c=>`
    <div class="comment-item">
      <div class="comment-avatar">${c.author?.profile_picture?`<img src="${esc(c.author.profile_picture)}" alt="">`:initials(c.author?.name||'?')}</div>
      <div class="comment-bubble">
        <div class="comment-author">${esc(c.author?.name||'')}</div>
        <div class="comment-text">${esc(c.content)}</div>
        <div class="comment-time">${timeAgo(c.created_at)}</div>
      </div>
    </div>`).join('');

  return `
  <div class="post-card" data-post-id="${post.id}">
    <div class="post-header">
      <a href="profile.html?id=${a.id}" class="post-author-avatar">
        ${a.profile_picture?`<img src="${esc(a.profile_picture)}" alt="">`:initials(a.name||'?')}
      </a>
      <div class="post-author-info">
        <div class="post-author-name"><a href="profile.html?id=${a.id}">${esc(a.name)}</a></div>
        <div class="post-author-meta">
          <span class="role-badge ${a.role}">${capitalize(a.role)}</span>
          ${a.college?`· ${esc(a.college)}`:''}
        </div>
        ${badges?`<div style="margin-top:3px;display:flex;gap:4px;flex-wrap:wrap;">${badges}</div>`:''}
        <div style="font-size:0.75rem;color:var(--text-muted);margin-top:1px;">${timeAgo(post.created_at)}</div>
      </div>
      ${(isOwn||isAdm)?`
      <div class="post-menu">
        <button class="post-menu-btn" data-menu-toggle="${post.id}">⋯</button>
        <div class="post-menu-dropdown" id="post-menu-${post.id}">
          <button class="post-menu-item" data-delete-post="${post.id}">🗑️ Delete Post</button>
        </div>
      </div>`:''}
    </div>
    <div class="post-content">${esc(post.content)}</div>
    ${post.image_url?`<img class="post-image" src="${esc(post.image_url)}" alt="" onerror="this.style.display='none'">`:''}
    <div class="post-stats">
      <span>${post.likes_count>0?`👍 ${post.likes_count} like${post.likes_count!==1?'s':''}`:'&nbsp;'}</span>
      <span>${post.comments?.length||0} comment${post.comments?.length!==1?'s':''}</span>
    </div>
    <div class="post-actions">
      <button class="post-action ${post.liked_by_me?'liked':''}" data-like-post="${post.id}">
        <span class="post-action-icon">👍</span> Like
      </button>
      <button class="post-action" data-toggle-comments="${post.id}">
        <span class="post-action-icon">💬</span> Comment
      </button>
      ${a.role==='alumni'&&currentUser.role==='student'?`
      <button class="post-action" data-mentorship-btn="${a.id}" data-mentorship-name="${esc(a.name||'')}">
        <span class="post-action-icon">🎓</span> Mentorship
      </button>`:''}
      <button class="post-action" data-message-btn="${a.id}">
        <span class="post-action-icon">✉️</span> Message
      </button>
    </div>
    <div class="post-comments" id="comments-${post.id}" style="display:none;">
      <div class="comments-list" id="comments-list-${post.id}">${commentsHtml}</div>
      <div class="comment-input-row">
        <div class="comment-avatar">
          ${currentUser.profile_picture?`<img src="${esc(currentUser.profile_picture)}" alt="">`:initials(currentUser.name)}
        </div>
        <input class="comment-input" id="comment-input-${post.id}"
               placeholder="Add a comment…" maxlength="500">
        <button class="btn btn-primary btn-sm" data-submit-comment="${post.id}">Post</button>
      </div>
    </div>
  </div>`;
}

function bindFeedActions() {
  // Likes
  document.querySelectorAll('[data-like-post]:not([data-bound])').forEach(btn => {
    btn.dataset.bound = '1';
    btn.addEventListener('click', async () => {
      const postId = parseInt(btn.dataset.likePost);
      try {
        const res = await likes.toggle(postId);
        btn.classList.toggle('liked', res.liked);
        const card  = btn.closest('[data-post-id]');
        const stats = card?.querySelector('.post-stats span');
        if (stats) stats.innerHTML = res.likes_count > 0
          ? `👍 ${res.likes_count} like${res.likes_count!==1?'s':''}` : '&nbsp;';
      } catch (err) { toast(err.message, 'error'); }
    });
  });

  // Toggle comments
  document.querySelectorAll('[data-toggle-comments]:not([data-bound])').forEach(btn => {
    btn.dataset.bound = '1';
    btn.addEventListener('click', () => {
      const sec = document.getElementById(`comments-${btn.dataset.toggleComments}`);
      if (sec) {
        sec.style.display = sec.style.display === 'none' ? 'block' : 'none';
        if (sec.style.display === 'block')
          document.getElementById(`comment-input-${btn.dataset.toggleComments}`)?.focus();
      }
    });
  });

  // Submit comment
  document.querySelectorAll('[data-submit-comment]:not([data-bound])').forEach(btn => {
    btn.dataset.bound = '1';
    btn.addEventListener('click', async () => {
      const postId  = parseInt(btn.dataset.submitComment);
      const input   = document.getElementById(`comment-input-${postId}`);
      const content = input?.value.trim();
      if (!content) return;
      try {
        await comments.create({ post_id: postId, content });
        const list = document.getElementById(`comments-list-${postId}`);
        list?.insertAdjacentHTML('beforeend', `
          <div class="comment-item">
            <div class="comment-avatar">${currentUser.profile_picture?`<img src="${esc(currentUser.profile_picture)}" alt="">`:initials(currentUser.name)}</div>
            <div class="comment-bubble">
              <div class="comment-author">${esc(currentUser.name)}</div>
              <div class="comment-text">${esc(content)}</div>
              <div class="comment-time">just now</div>
            </div>
          </div>`);
        if (input) input.value = '';
      } catch (err) { toast(err.message, 'error'); }
    });
  });

  // Post menu toggle
  document.querySelectorAll('[data-menu-toggle]:not([data-bound])').forEach(btn => {
    btn.dataset.bound = '1';
    btn.addEventListener('click', e => {
      e.stopPropagation();
      const menuId = `post-menu-${btn.dataset.menuToggle}`;
      document.querySelectorAll('.post-menu-dropdown.open').forEach(el => {
        if (el.id !== menuId) el.classList.remove('open');
      });
      document.getElementById(menuId)?.classList.toggle('open');
    });
  });

  // Delete post
  document.querySelectorAll('[data-delete-post]:not([data-bound])').forEach(btn => {
    btn.dataset.bound = '1';
    btn.addEventListener('click', async () => {
      if (!confirm('Delete this post?')) return;
      try {
        await posts.delete(parseInt(btn.dataset.deletePost));
        btn.closest('[data-post-id]')?.remove();
        toast('Post deleted.', 'success');
      } catch (err) { toast(err.message, 'error'); }
    });
  });

  // Message user
  document.querySelectorAll('[data-message-btn]:not([data-bound])').forEach(btn => {
    btn.dataset.bound = '1';
    btn.addEventListener('click', () => window.location.href = `chat.html?user=${btn.dataset.messageBtn}`);
  });

  // Mentorship
  document.querySelectorAll('[data-mentorship-btn]:not([data-bound])').forEach(btn => {
    btn.dataset.bound = '1';
    btn.addEventListener('click', () => openMentorshipModal(parseInt(btn.dataset.mentorshipBtn), btn.dataset.mentorshipName));
  });

  // Close menus on outside click
  document.addEventListener('click', () => {
    document.querySelectorAll('.post-menu-dropdown.open').forEach(el => el.classList.remove('open'));
  });
}

function setupInfiniteScroll() {
  window.addEventListener('scroll', async () => {
    if (loadingFeed || feedExhausted) return;
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500)
      await loadFeed(false);
  });
}

// ══════════════════════════════════════════════════════════
//  RIGHT SIDEBAR — AI Recommendations
// ══════════════════════════════════════════════════════════
async function loadRightSidebar() {
  const container = document.getElementById('alumni-suggestions');
  if (!container) return;
  try {
    const recs = await ai.recommendations();
    if (!recs.length) {
      container.innerHTML = '<div style="padding:12px;font-size:0.85rem;color:var(--text-muted);">Add skills to your profile for better matches!</div>';
      return;
    }
    container.innerHTML = recs.slice(0, 5).map(rec => `
      <div class="suggestion-item">
        <div class="suggestion-avatar">
          ${rec.user.profile_picture?`<img src="${esc(rec.user.profile_picture)}" alt="">`:initials(rec.user.name)}
        </div>
        <div class="suggestion-info">
          <div class="suggestion-name"><a href="profile.html?id=${rec.user.id}" style="color:inherit;text-decoration:none;">${esc(rec.user.name)}</a></div>
          <div class="suggestion-meta">${esc(rec.user.college||'Alumni')}</div>
          <div class="suggestion-reason">${esc(rec.reason)}</div>
        </div>
        <button class="btn-connect-sm" onclick="openMentorshipModal(${rec.user.id},'${esc(rec.user.name)}')">Connect</button>
      </div>`).join('');
  } catch { /* silent */ }
}

// ══════════════════════════════════════════════════════════
//  ALUMNI BROWSE SECTION
// ══════════════════════════════════════════════════════════
async function loadAlumniBrowse() {
  const grid = document.getElementById('alumni-browse-grid');
  if (!grid) return;
  grid.innerHTML = '<div class="loading-spinner"></div>';
  try {
    const alumniList = await users.getAlumni();
    if (!alumniList.length) {
      grid.innerHTML = '<p style="padding:16px;color:var(--text-muted);">No alumni registered yet.</p>';
      return;
    }
    grid.innerHTML = alumniList.map(u => `
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-lg);
                  padding:16px;text-align:center;transition:var(--transition);"
           onmouseover="this.style.boxShadow='var(--shadow-md)'" onmouseout="this.style.boxShadow=''">
        <a href="profile.html?id=${u.id}" style="text-decoration:none;color:inherit;">
          <div style="width:56px;height:56px;border-radius:50%;background:var(--primary);color:white;
                      display:grid;place-items:center;font-size:20px;font-weight:700;margin:0 auto 10px;overflow:hidden;">
            ${u.profile_picture?`<img src="${esc(u.profile_picture)}" alt="" style="width:100%;height:100%;object-fit:cover;">`:initials(u.name)}
          </div>
          <div style="font-weight:600;font-size:0.9rem;margin-bottom:3px;">${esc(u.name)}</div>
          <div style="font-size:0.78rem;color:var(--text-muted);margin-bottom:8px;">${esc(u.college||'Alumni')}</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;justify-content:center;">
            ${(u.skills||'').split(',').filter(Boolean).slice(0,2).map(s=>`<span class="skill-tag" style="font-size:0.7rem;">${esc(s.trim())}</span>`).join('')}
          </div>
        </a>
        <div style="margin-top:10px;display:flex;gap:6px;justify-content:center;flex-wrap:wrap;">
          <button class="btn-connect-sm" onclick="window.location.href='chat.html?user=${u.id}'">✉️ Message</button>
          ${currentUser.role==='student'?`<button class="btn-connect-sm" style="border-color:var(--accent-green);color:var(--accent-green);" onclick="openMentorshipModal(${u.id},'${esc(u.name)}')">🎓 Mentor</button>`:''}
        </div>
      </div>`).join('');
  } catch (err) { grid.innerHTML = '<p style="padding:16px;color:var(--accent-red);">Failed to load alumni.</p>'; }
}

// ══════════════════════════════════════════════════════════
//  MENTORSHIP MODAL & PANEL
// ══════════════════════════════════════════════════════════
function openMentorshipModal(alumniId, alumniName) {
  document.getElementById('mentorship-alumni-id').value        = alumniId;
  document.getElementById('mentorship-alumni-name').textContent = alumniName;
  document.getElementById('mentorship-modal')?.classList.add('open');
}
window.openMentorshipModal = openMentorshipModal;

function setupMentorshipModal() {
  const modal     = document.getElementById('mentorship-modal');
  const closeBtn  = document.getElementById('mentorship-modal-close');
  const cancelBtn = document.getElementById('mentorship-modal-cancel');
  const submitBtn = document.getElementById('mentorship-submit');
  const msgInput  = document.getElementById('mentorship-message');

  const closeModal = () => { modal?.classList.remove('open'); if (msgInput) msgInput.value = ''; };
  closeBtn?.addEventListener('click', closeModal);
  cancelBtn?.addEventListener('click', closeModal);
  modal?.addEventListener('click', e => { if (e.target === modal) closeModal(); });

  submitBtn?.addEventListener('click', async () => {
    const alumniId = parseInt(document.getElementById('mentorship-alumni-id').value);
    const message  = msgInput?.value.trim() || null;
    submitBtn.disabled = true; submitBtn.textContent = 'Sending…';
    try {
      await mentorship.send({ alumni_id: alumniId, message });
      toast('Mentorship request sent! 🎓', 'success');
      closeModal();
    } catch (err) { toast(err.message, 'error'); }
    finally { submitBtn.disabled = false; submitBtn.textContent = 'Send Request'; }
  });
}

async function loadMentorshipPanel() {
  const titleEl   = document.getElementById('mentorship-panel-title');
  const container = document.getElementById('mentorship-requests-container');
  const myEl      = document.getElementById('my-mentorship-container');
  if (!container) return;

  if (currentUser.role === 'alumni') {
    if (titleEl) titleEl.textContent = '🎓 Pending Requests';
    try {
      const reqs = await mentorship.pending();
      container.innerHTML = !reqs.length
        ? '<div class="empty-state" style="padding:20px;"><div class="empty-icon">🎓</div><p>No pending requests.</p></div>'
        : reqs.map(r => `
          <div class="mentorship-card" id="mreq-${r.id}">
            <div class="suggestion-avatar" style="width:42px;height:42px;flex-shrink:0;">
              ${r.student.profile_picture?`<img src="${esc(r.student.profile_picture)}" alt="">`:initials(r.student.name)}
            </div>
            <div class="mentorship-info">
              <div class="mentorship-name"><a href="profile.html?id=${r.student.id}">${esc(r.student.name)}</a></div>
              <div class="mentorship-message">${esc(r.message||'No message.')}</div>
              <div class="mentorship-actions">
                <button class="btn btn-primary btn-sm" data-accept="${r.id}">✓ Accept</button>
                <button class="btn btn-ghost btn-sm"   data-reject="${r.id}">✗ Decline</button>
              </div>
            </div>
            <span style="font-size:0.72rem;color:var(--text-muted);">${timeAgo(r.created_at)}</span>
          </div>`).join('');

      container.querySelectorAll('[data-accept]').forEach(btn =>
        btn.addEventListener('click', () => respondMentorship(parseInt(btn.dataset.accept), 'accepted')));
      container.querySelectorAll('[data-reject]').forEach(btn =>
        btn.addEventListener('click', () => respondMentorship(parseInt(btn.dataset.reject), 'rejected')));
    } catch { container.innerHTML = '<p style="padding:12px;color:var(--accent-red);">Failed to load.</p>'; }

  } else if (currentUser.role === 'student') {
    if (titleEl) titleEl.textContent = '🎓 My Mentorship Requests';
    container.innerHTML = '';
    try {
      const reqs = await mentorship.myRequests();
      myEl.innerHTML = !reqs.length
        ? '<div style="padding:12px;font-size:0.85rem;color:var(--text-muted);">No requests yet.</div>'
        : reqs.map(r => `
          <div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--border);">
            <div class="suggestion-avatar" style="width:36px;height:36px;flex-shrink:0;">
              ${r.alumni.profile_picture?`<img src="${esc(r.alumni.profile_picture)}" alt="">`:initials(r.alumni.name)}
            </div>
            <div style="flex:1;">
              <div style="font-weight:600;font-size:0.875rem;"><a href="profile.html?id=${r.alumni.id}">${esc(r.alumni.name)}</a></div>
              <div style="font-size:0.78rem;color:var(--text-muted);">${timeAgo(r.created_at)}</div>
            </div>
            <span class="status-badge ${r.status}">${r.status}</span>
          </div>`).join('');
    } catch { myEl.innerHTML = '<p style="color:var(--accent-red);">Failed to load.</p>'; }
  }
}

async function respondMentorship(id, status) {
  try {
    await mentorship.respond(id, status);
    document.getElementById(`mreq-${id}`)?.remove();
    toast(`Request ${status}! ${status==='accepted'?'🎉':''}`, status==='accepted'?'success':'info');
  } catch (err) { toast(err.message, 'error'); }
}

// ══════════════════════════════════════════════════════════
//  ADMIN PANEL
// ══════════════════════════════════════════════════════════
async function loadAdminPanel() {
  if (currentUser.role !== 'admin') return;
  const container = document.getElementById('admin-users-container');
  const statsEl   = document.getElementById('admin-stats');
  if (!container) return;

  try {
    const allUsers = await users.listAll();
    const c = { total: allUsers.length, students: 0, alumni: 0, admins: 0 };
    allUsers.forEach(u => { if(u.role==='student') c.students++; else if(u.role==='alumni') c.alumni++; else c.admins++; });

    if (statsEl) statsEl.innerHTML = `
      <div class="stat-card"><div class="stat-icon blue">👥</div><div><div class="stat-value">${c.total}</div><div class="stat-label">Total Users</div></div></div>
      <div class="stat-card"><div class="stat-icon green">🎓</div><div><div class="stat-value">${c.students}</div><div class="stat-label">Students</div></div></div>
      <div class="stat-card"><div class="stat-icon amber">🏛️</div><div><div class="stat-value">${c.alumni}</div><div class="stat-label">Alumni</div></div></div>
      <div class="stat-card"><div class="stat-icon purple">⚙️</div><div><div class="stat-value">${c.admins}</div><div class="stat-label">Admins</div></div></div>`;

    container.innerHTML = `
      <table class="admin-table">
        <thead><tr><th>#</th><th>Name</th><th>Email</th><th>Role</th><th>College</th><th>Joined</th><th>Actions</th></tr></thead>
        <tbody>${allUsers.map(u => `
          <tr>
            <td>${u.id}</td>
            <td><a href="profile.html?id=${u.id}">${esc(u.name)}</a></td>
            <td>${esc(u.email)}</td>
            <td><span class="role-badge ${u.role}">${capitalize(u.role)}</span></td>
            <td>${esc(u.college||'—')}</td>
            <td>${new Date(u.created_at).toLocaleDateString('en-GB')}</td>
            <td>${u.id!==currentUser.id?`<button class="btn btn-danger btn-sm" data-admin-del="${u.id}">Delete</button>`:'<em style="color:var(--text-muted);">You</em>'}</td>
          </tr>`).join('')}
        </tbody>
      </table>`;

    container.querySelectorAll('[data-admin-del]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Permanently delete this user and all their data?')) return;
        try {
          await users.deleteUser(parseInt(btn.dataset.adminDel));
          btn.closest('tr').remove();
          toast('User deleted.', 'success');
        } catch (err) { toast(err.message, 'error'); }
      });
    });
  } catch { toast('Failed to load admin panel.', 'error'); }
}

// ══════════════════════════════════════════════════════════
//  CHATBOT WIDGET
// ══════════════════════════════════════════════════════════
function setupChatbot() {
  const toggle   = document.getElementById('chatbot-toggle');
  const win      = document.getElementById('chatbot-window');
  const closeBtn = document.getElementById('chatbot-close');
  const input    = document.getElementById('chatbot-input');
  const sendBtn  = document.getElementById('chatbot-send');
  const msgs     = document.getElementById('chatbot-messages');

  toggle?.addEventListener('click', () => win?.classList.toggle('open'));
  closeBtn?.addEventListener('click', () => win?.classList.remove('open'));

  setTimeout(() => appendChat('👋 Hi! I\'m your AI career assistant.<br>Type <strong>help</strong> to see what I can do!', 'bot', msgs), 1000);

  const send = async () => {
    const text = input?.value.trim();
    if (!text) return;
    appendChat(esc(text), 'user', msgs);
    if (input) input.value = '';
    try {
      const res = await ai.chatbot(text);
      appendChat(res.reply.replace(/\n/g,'<br>').replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>'), 'bot', msgs);
      if (res.suggestions?.length) {
        appendChat(`<strong style="font-size:0.78rem;">Suggested alumni:</strong>${
          res.suggestions.map(u=>`<div class="chatbot-suggestion-user" style="margin-top:5px;">
            <span style="font-size:12px;font-weight:700;">${initials(u.name)}</span>
            <a href="profile.html?id=${u.id}" style="font-weight:600;font-size:0.8rem;">${esc(u.name)}</a>
          </div>`).join('')}`, 'bot', msgs);
      }
    } catch { appendChat('Sorry, I ran into an error. Please try again.', 'bot', msgs); }
  };

  sendBtn?.addEventListener('click', send);
  input?.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
}

function appendChat(html, type, container) {
  if (!container) return;
  const el = document.createElement('div');
  el.className = `chatbot-msg ${type}`;
  el.innerHTML = html;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

// ══════════════════════════════════════════════════════════
//  UTILS
// ══════════════════════════════════════════════════════════
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function capitalize(s) { return s ? s[0].toUpperCase()+s.slice(1) : ''; }
