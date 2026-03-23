// ══════════════════════════════════════════════════════════
//  profile.js — Profile page logic
//  Imported by profile.html via <script type="module" src="js/profile.js">
// ══════════════════════════════════════════════════════════
import {
  requireAuth, getUser, setUser, removeToken,
  users, posts, mentorship, upload,
  toast, timeAgo, initials
} from './api.js';

if (!requireAuth()) throw new Error('Not authenticated');

const currentUser = getUser();
const params      = new URLSearchParams(window.location.search);
const targetId    = params.get('id') ? parseInt(params.get('id')) : currentUser.id;
const isOwn       = targetId === currentUser.id;

// ── Boot ──────────────────────────────────────────────────
setupNavbar();
const profileUser = await loadProfile();
if (profileUser) {
  renderActionButtons(profileUser);
  await loadUserPosts(profileUser);
}

// ══════════════════════════════════════════════════════════
//  NAVBAR
// ══════════════════════════════════════════════════════════
function setupNavbar() {
  const avatarEl = document.getElementById('nav-user-avatar');
  if (avatarEl) avatarEl.innerHTML = currentUser.profile_picture
    ? `<img src="${esc(currentUser.profile_picture)}" alt="" style="width:32px;height:32px;border-radius:50%;object-fit:cover;">`
    : initials(currentUser.name);

  document.getElementById('logout-btn')?.addEventListener('click', () => {
    removeToken(); window.location.href = 'login.html';
  });
}

// ══════════════════════════════════════════════════════════
//  LOAD PROFILE DATA
// ══════════════════════════════════════════════════════════
async function loadProfile() {
  try {
    const u = isOwn ? currentUser : await users.getById(targetId);
    document.title = `${u.name} — Back2Roots`;

    const roleColors = { student:'#15803d', alumni:'#0369a1', admin:'#d97706' };
    const banner = document.getElementById('profile-banner');
    if (banner) banner.style.background =
      `linear-gradient(135deg, ${roleColors[u.role]||'#0a66c2'} 0%, #1e3a8a 100%)`;

    // Avatar
    const avatarEl = document.getElementById('profile-avatar');
    if (avatarEl) {
      avatarEl.innerHTML = u.profile_picture
        ? `<img src="${esc(u.profile_picture)}" alt="">`
        : initials(u.name);
    }

    document.getElementById('profile-name').textContent    = u.name;
    document.getElementById('profile-role').innerHTML      = `<span class="role-badge ${u.role}">${capitalize(u.role)}</span>`;
    document.getElementById('profile-college').textContent = u.college || 'College not set';
    document.getElementById('profile-bio').textContent     = u.bio || 'No bio provided.';

    const skillsEl = document.getElementById('profile-skills-list');
    if (skillsEl) {
      const skills = (u.skills || '').split(',').filter(s => s.trim());
      skillsEl.innerHTML = skills.length
        ? skills.map(s => `<span class="skill-tag">${esc(s.trim())}</span>`).join('')
        : '<span style="color:var(--text-muted);font-size:0.875rem;">No skills listed.</span>';
    }

    return u;
  } catch (err) {
    document.querySelector('main').innerHTML = `
      <div class="empty-state" style="margin-top:40px;">
        <div class="empty-icon">😕</div>
        <h3>User not found</h3>
        <p><a href="dashboard.html">← Back to feed</a></p>
      </div>`;
    return null;
  }
}

// ══════════════════════════════════════════════════════════
//  ACTION BUTTONS
// ══════════════════════════════════════════════════════════
function renderActionButtons(u) {
  const actionsEl = document.getElementById('profile-actions');
  if (!actionsEl) return;

  if (isOwn) {
    actionsEl.innerHTML = `
      <button class="btn btn-outline" id="edit-profile-btn">✏️ Edit Profile</button>
      <button class="btn btn-ghost" id="change-pw-btn">🔒 Change Password</button>`;

    document.getElementById('edit-profile-btn').addEventListener('click', () => {
      // Pre-fill fields
      document.getElementById('edit-name').value    = u.name    || '';
      document.getElementById('edit-bio').value     = u.bio     || '';
      document.getElementById('edit-skills').value  = u.skills  || '';
      document.getElementById('edit-college').value = u.college || '';
      document.getElementById('edit-pic').value     = u.profile_picture || '';
      document.getElementById('edit-profile-modal').classList.add('open');
    });

    document.getElementById('change-pw-btn').addEventListener('click', () => {
      window.location.href = 'settings.html';
    });

    setupEditModal();
    setupAvatarUpload();
  } else {
    let html = `<button class="btn btn-primary" onclick="window.location.href='chat.html?user=${u.id}'">✉️ Message</button>`;
    if (u.role === 'alumni' && currentUser.role === 'student') {
      html += `<button class="btn btn-outline" id="req-mentorship-btn">🎓 Request Mentorship</button>`;
    }
    actionsEl.innerHTML = html;
    document.getElementById('req-mentorship-btn')?.addEventListener('click', () => {
      document.getElementById('mentorship-alumni-id').value        = u.id;
      document.getElementById('mentorship-alumni-name').textContent = u.name;
      document.getElementById('mentorship-modal').classList.add('open');
    });
    setupMentorshipModal();
  }
}

// ══════════════════════════════════════════════════════════
//  LOAD USER'S POSTS
// ══════════════════════════════════════════════════════════
async function loadUserPosts(u) {
  const feedEl = document.getElementById('user-posts-feed');
  if (!feedEl) return;
  try {
    const userPosts = await posts.getUserPosts(u.id);
    if (!userPosts.length) {
      feedEl.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><p>No posts yet.</p></div>';
      return;
    }
    feedEl.innerHTML = userPosts.map(p => renderPost(p)).join('');
    bindDeleteButtons();
  } catch {
    feedEl.innerHTML = '<div class="empty-state"><p style="color:var(--accent-red);">Could not load posts.</p></div>';
  }
}

function renderPost(p) {
  const canDelete = p.user_id === currentUser.id || currentUser.role === 'admin';
  return `
    <div class="post-card" data-post-id="${p.id}"
         style="margin:0;border-radius:0;border-left:none;border-right:none;border-top:none;">
      <div class="post-content" style="padding:14px 20px;">${esc(p.content)}</div>
      ${p.image_url ? `<img class="post-image" src="${esc(p.image_url)}" alt="" onerror="this.style.display='none'">` : ''}
      <div style="padding:8px 20px 12px;display:flex;align-items:center;justify-content:space-between;">
        <span style="font-size:0.78rem;color:var(--text-muted);">
          ${timeAgo(p.created_at)} · 👍 ${p.likes_count} · 💬 ${p.comments?.length||0}
        </span>
        ${canDelete ? `<button class="btn btn-danger btn-sm" data-del="${p.id}">Delete</button>` : ''}
      </div>
    </div>`;
}

function bindDeleteButtons() {
  document.querySelectorAll('[data-del]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Delete this post?')) return;
      try {
        await posts.delete(parseInt(btn.dataset.del));
        btn.closest('[data-post-id]')?.remove();
        toast('Post deleted.', 'success');
      } catch (err) { toast(err.message, 'error'); }
    });
  });
}

// ══════════════════════════════════════════════════════════
//  EDIT PROFILE MODAL
// ══════════════════════════════════════════════════════════
function setupEditModal() {
  const modal     = document.getElementById('edit-profile-modal');
  const closeBtn  = document.getElementById('edit-profile-close');
  const cancelBtn = document.getElementById('edit-cancel-btn');
  const saveBtn   = document.getElementById('save-profile-btn');

  const close = () => modal?.classList.remove('open');
  closeBtn?.addEventListener('click', close);
  cancelBtn?.addEventListener('click', close);
  modal?.addEventListener('click', e => { if (e.target === modal) close(); });

  saveBtn?.addEventListener('click', async () => {
    saveBtn.disabled = true; saveBtn.textContent = 'Saving…';
    try {
      const payload = {
        name:            document.getElementById('edit-name').value.trim()    || undefined,
        bio:             document.getElementById('edit-bio').value.trim()     || undefined,
        skills:          document.getElementById('edit-skills').value.trim()  || undefined,
        college:         document.getElementById('edit-college').value.trim() || undefined,
        profile_picture: document.getElementById('edit-pic').value.trim()    || null,
      };
      const updated = await users.update(payload);
      setUser(updated);
      toast('Profile updated! ✅', 'success');
      setTimeout(() => location.reload(), 600);
    } catch (err) {
      toast(err.message, 'error');
      saveBtn.disabled = false; saveBtn.textContent = 'Save Changes';
    }
  });
}

// ══════════════════════════════════════════════════════════
//  AVATAR UPLOAD (file input in edit modal)
// ══════════════════════════════════════════════════════════
function setupAvatarUpload() {
  const fileInput = document.getElementById('avatar-file-input');
  fileInput?.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;
    const label = document.getElementById('avatar-upload-label');
    if (label) label.textContent = 'Uploading…';
    try {
      const res = await upload.avatar(file);
      document.getElementById('edit-pic').value = res.url;
      toast('Avatar uploaded! Save profile to apply.', 'success');
    } catch (err) {
      toast('Upload failed: ' + err.message, 'error');
    } finally {
      if (label) label.textContent = '📁 Upload Photo';
      fileInput.value = '';
    }
  });
}

// ══════════════════════════════════════════════════════════
//  MENTORSHIP MODAL (for viewing other profiles)
// ══════════════════════════════════════════════════════════
function setupMentorshipModal() {
  const modal     = document.getElementById('mentorship-modal');
  const closeBtn  = document.getElementById('mentorship-modal-close');
  const cancelBtn = document.getElementById('mentorship-cancel-btn');
  const submitBtn = document.getElementById('mentorship-submit');
  const msgInput  = document.getElementById('mentorship-message');

  const close = () => { modal?.classList.remove('open'); if (msgInput) msgInput.value = ''; };
  closeBtn?.addEventListener('click', close);
  cancelBtn?.addEventListener('click', close);
  modal?.addEventListener('click', e => { if (e.target === modal) close(); });

  submitBtn?.addEventListener('click', async () => {
    const alumniId = parseInt(document.getElementById('mentorship-alumni-id').value);
    const message  = msgInput?.value.trim() || null;
    submitBtn.disabled = true; submitBtn.textContent = 'Sending…';
    try {
      await mentorship.send({ alumni_id: alumniId, message });
      toast('Mentorship request sent! 🎓', 'success');
      close();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      submitBtn.disabled = false; submitBtn.textContent = 'Send Request';
    }
  });
}

// ══════════════════════════════════════════════════════════
//  UTILS
// ══════════════════════════════════════════════════════════
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function capitalize(s) { return s ? s[0].toUpperCase()+s.slice(1) : ''; }
