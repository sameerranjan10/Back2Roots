// ══════════════════════════════════════════════════════════
//  auth.js  —  Login & Registration logic (standalone module)
//  Imported by login.html and signup.html
// ══════════════════════════════════════════════════════════
import { auth, setToken, setUser, redirectIfAuth, toast } from './api.js';

// ── Page detector ─────────────────────────────────────────
const page = document.body.dataset.page;
if (page === 'login')    initLoginPage();
if (page === 'register') initRegisterPage();

// ══════════════════════════════════════════════════════════
//  LOGIN
// ══════════════════════════════════════════════════════════
function initLoginPage() {
  redirectIfAuth();

  const form     = document.getElementById('login-form');
  const errEl    = document.getElementById('login-error');
  const btn      = document.getElementById('login-btn');
  const pwInput  = document.getElementById('password');

  // Toggle password visibility
  document.getElementById('toggle-pw')?.addEventListener('click', () => {
    pwInput.type = pwInput.type === 'password' ? 'text' : 'password';
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError(errEl);

    const email    = document.getElementById('email').value.trim();
    const password = pwInput.value;

    if (!email || !password) { showError(errEl, 'Please fill in all fields.'); return; }

    setLoading(btn, 'Signing in…');

    try {
      const data = await auth.login({ email, password });
      setToken(data.access_token);
      setUser(data.user);
      toast('Welcome back, ' + data.user.name + '! 👋', 'success');
      setTimeout(() => window.location.href = 'dashboard.html', 600);
    } catch (err) {
      showError(errEl, err.message || 'Login failed. Check your credentials.');
      resetBtn(btn, 'Sign In');
    }
  });
}

// ══════════════════════════════════════════════════════════
//  REGISTER
// ══════════════════════════════════════════════════════════
function initRegisterPage() {
  redirectIfAuth();

  const form    = document.getElementById('register-form');
  const errEl   = document.getElementById('register-error');
  const btn     = document.getElementById('register-btn');
  const pwInput = document.getElementById('password');

  // Live password strength meter
  const bar   = document.getElementById('pw-strength-bar');
  const fill  = document.getElementById('pw-strength-fill');
  const label = document.getElementById('pw-strength-label');

  pwInput?.addEventListener('input', () => {
    const v = pwInput.value;
    if (!v) { bar && (bar.style.display = 'none'); return; }
    if (bar) bar.style.display = 'block';
    let score = 0;
    if (v.length >= 6)           score++;
    if (v.length >= 10)          score++;
    if (/[A-Z]/.test(v))         score++;
    if (/[0-9]/.test(v))         score++;
    if (/[^A-Za-z0-9]/.test(v))  score++;
    const levels = [
      { pct:'20%', color:'#ef4444', text:'Very weak' },
      { pct:'40%', color:'#f97316', text:'Weak' },
      { pct:'60%', color:'#eab308', text:'Fair' },
      { pct:'80%', color:'#22c55e', text:'Strong' },
      { pct:'100%',color:'#16a34a', text:'Very strong' },
    ];
    const lvl = levels[Math.min(score - 1, 4)] || levels[0];
    if (fill)  { fill.style.width = lvl.pct; fill.style.background = lvl.color; }
    if (label) label.textContent = `Strength: ${lvl.text}`;
  });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError(errEl);

    const name      = document.getElementById('name').value.trim();
    const email     = document.getElementById('email').value.trim();
    const password  = pwInput.value;
    const confirmPw = document.getElementById('confirm-password').value;
    const role      = document.getElementById('role').value;
    const college   = document.getElementById('college')?.value.trim() || '';
    const skills    = document.getElementById('skills')?.value.trim()  || '';
    const bio       = document.getElementById('bio')?.value.trim()     || '';

    if (!name || !email || !password || !confirmPw || !role) {
      showError(errEl, 'Please fill in all required fields.'); return;
    }
    if (password !== confirmPw) { showError(errEl, 'Passwords do not match.'); return; }
    if (password.length < 6)   { showError(errEl, 'Password must be at least 6 characters.'); return; }

    setLoading(btn, 'Creating account…');

    try {
      const data = await auth.register({ name, email, password, role, college, skills, bio });
      setToken(data.access_token);
      setUser(data.user);
      toast('Account created! Welcome to Back2Roots 🎉', 'success');
      setTimeout(() => window.location.href = 'dashboard.html', 700);
    } catch (err) {
      showError(errEl, err.message || 'Registration failed. Please try again.');
      resetBtn(btn, 'Create Account');
    }
  });
}

// ══════════════════════════════════════════════════════════
//  FORGOT PASSWORD  (standalone page support)
// ══════════════════════════════════════════════════════════
export async function initForgotPassword() {
  const form  = document.getElementById('forgot-form');
  const errEl = document.getElementById('forgot-error');
  const okEl  = document.getElementById('forgot-success');
  const btn   = document.getElementById('forgot-btn');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError(errEl);
    const email = document.getElementById('forgot-email').value.trim();
    if (!email) { showError(errEl, 'Enter your email address.'); return; }

    setLoading(btn, 'Sending…');
    try {
      const { API_BASE } = await import('./api.js');
      const res  = await fetch(`${API_BASE}/auth/forgot-password`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email }),
      });
      const data = await res.json();
      if (okEl) {
        okEl.textContent = data.message;
        okEl.classList.add('show');
      }
      // In DEBUG mode, the token is returned — display it for dev convenience
      if (data.reset_token) {
        const tokenEl = document.getElementById('reset-token-debug');
        if (tokenEl) tokenEl.textContent = data.reset_token;
        document.getElementById('debug-box')?.style.setProperty('display', 'block');
      }
    } catch (err) {
      showError(errEl, err.message);
    } finally {
      resetBtn(btn, 'Send Reset Link');
    }
  });
}

// ══════════════════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════════════════
function showError(el, msg) {
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
}
function hideError(el) {
  if (!el) return;
  el.textContent = '';
  el.classList.remove('show');
}
function setLoading(btn, text) {
  if (!btn) return;
  btn.disabled    = true;
  btn.textContent = text;
}
function resetBtn(btn, text) {
  if (!btn) return;
  btn.disabled    = false;
  btn.textContent = text;
}
