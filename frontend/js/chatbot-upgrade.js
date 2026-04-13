/**
 * Back2Roots — AI Chatbot Premium Upgrade JS
 * Paste before </body> — preserves existing IDs & FastAPI logic
 */
(function () {
  'use strict';

  const popup    = document.getElementById('chatbot-popup');
  const messages = document.querySelector('.chatbot-messages');
  const inputEl  = document.querySelector('.chatbot-input');
  const sendBtn  = document.querySelector('.chatbot-send');

  if (!popup || !messages) return;

  let isFullscreen = false;

  /* ── Button wiring ───────────────────────────────────── */
  document.getElementById('cb-expand-btn')?.addEventListener('click', toggleFullscreen);

  document.getElementById('cb-close-btn')?.addEventListener('click', () => {
    popup.classList.remove('open');
    if (isFullscreen) exitFullscreen();
  });

  document.querySelectorAll('.cb-quick-action').forEach((btn) => {
    btn.addEventListener('click', () => {
      if (inputEl) {
        inputEl.value = btn.dataset.prompt || '';
        inputEl.focus();
        scrollToBottom();
      }
    });
  });

  /* ── Auto-scroll observer ────────────────────────────── */
  new MutationObserver(scrollToBottom)
    .observe(messages, { childList: true, subtree: true, characterData: true });

  /* ── Intercept send ──────────────────────────────────── */
  if (sendBtn && inputEl) {
    const fresh = sendBtn.cloneNode(true);
    sendBtn.parentNode.replaceChild(fresh, sendBtn);
    fresh.addEventListener('click', handleSend);
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    });
  }

  /* ── Fullscreen ──────────────────────────────────────── */
  function toggleFullscreen() { isFullscreen ? exitFullscreen() : enterFullscreen(); }

  function enterFullscreen() {
    isFullscreen = true;
    popup.classList.add('cb-fullscreen');
    const btn = document.getElementById('cb-expand-btn');
    if (btn) { btn.textContent = '🗗'; btn.title = 'Exit fullscreen'; }
    setTimeout(scrollToBottom, 380);
  }

  function exitFullscreen() {
    isFullscreen = false;
    popup.classList.remove('cb-fullscreen');
    const btn = document.getElementById('cb-expand-btn');
    if (btn) { btn.textContent = '⛶'; btn.title = 'Expand to fullscreen'; }
    setTimeout(scrollToBottom, 380);
  }

  /* ── Helpers ─────────────────────────────────────────── */
  function scrollToBottom() {
    requestAnimationFrame(() => { messages.scrollTop = messages.scrollHeight; });
  }

  function showTyping() {
    document.getElementById('cb-typing')?.classList.add('show');
    scrollToBottom();
  }

  function hideTyping() {
    document.getElementById('cb-typing')?.classList.remove('show');
  }

  function typeText(element, text, speed = 15) {
    return new Promise((resolve) => {
      let i = 0;
      element.textContent = '';
      const timer = setInterval(() => {
        element.textContent += text.charAt(i++);
        if (i % 5 === 0) scrollToBottom();
        if (i >= text.length) { clearInterval(timer); scrollToBottom(); resolve(); }
      }, speed);
    });
  }

  function addBubble(text, type) {
    const wrap   = document.createElement('div');
    wrap.className = `message-bubble ${type}`;
    const bubble = document.createElement('div');
    bubble.className = 'message-text';
    bubble.textContent = text;
    const time   = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    wrap.append(bubble, time);
    // Insert before typing indicator
    const typingEl = document.getElementById('cb-typing');
    messages.insertBefore(wrap, typingEl);
    scrollToBottom();
    return wrap;
  }

  /* ── Main send handler ───────────────────────────────── */
  async function handleSend() {
    const text = inputEl?.value.trim();
    if (!text) return;

    addBubble(text, 'sent');
    if (inputEl) inputEl.value = '';
    showTyping();

    try {
      /*
       * ⚠️  REPLACE '/api/chat' with your actual FastAPI endpoint URL.
       * Keep the same request/response shape you already use.
       */
      const res  = await fetch('https://back2roots-uews.onrender.com/docs/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      hideTyping();
      const reply = data.reply || data.response || data.message
                  || 'Sorry, I could not process that.';
      const botWrap = addBubble('', 'received');
      await typeText(botWrap.querySelector('.message-text'), reply, 14);
    } catch {
      hideTyping();
      const botWrap = addBubble('', 'received');
      await typeText(
        botWrap.querySelector('.message-text'),
        '⚠️ Connection issue. Please check your network and try again.', 14
      );
    }
  }

  /* Expose API for your existing code if needed */
  window.cb = { showTyping, hideTyping, typeText, scrollToBottom, addBubble };

})();