(function () {
  'use strict';

  // ---- Read configuration from the script tag ----
  var currentScript =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName('script');
      for (var i = scripts.length - 1; i >= 0; i--) {
        if (scripts[i].src && scripts[i].src.indexOf('widget.js') !== -1) {
          return scripts[i];
        }
      }
      return scripts[scripts.length - 1];
    })();

  var COMPANY_NAME =
    (currentScript && currentScript.getAttribute('data-company-name')) ||
    'Chatbot';
  var API_URL =
    (currentScript && currentScript.getAttribute('data-api-url')) ||
    'http://localhost:8000';
  var COMPANY_ID =
    (currentScript && currentScript.getAttribute('data-company-id')) || 'demo';

  // ---- Inject styles ----
  var styles =
    '' +
    '.pcb-launcher{' +
    'position:fixed;bottom:24px;right:24px;width:60px;height:60px;' +
    'border-radius:50%;background:#e94560;border:none;cursor:pointer;' +
    'box-shadow:0 6px 20px rgba(0,0,0,0.25);display:flex;align-items:center;' +
    'justify-content:center;z-index:2147483646;transition:transform .2s ease;' +
    'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;' +
    '}' +
    '.pcb-launcher:hover{transform:scale(1.06);}' +
    '.pcb-launcher svg{width:28px;height:28px;fill:#fff;}' +
    '.pcb-window{' +
    'position:fixed;bottom:96px;right:24px;width:380px;height:550px;' +
    'background:#1a1a2e;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,0.35);' +
    'display:flex;flex-direction:column;overflow:hidden;z-index:2147483647;' +
    'opacity:0;transform:translateY(16px) scale(.98);pointer-events:none;' +
    'transition:opacity .22s ease, transform .22s ease;' +
    'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;' +
    'color:#fff;box-sizing:border-box;' +
    '}' +
    '.pcb-window.pcb-open{opacity:1;transform:translateY(0) scale(1);pointer-events:auto;}' +
    '.pcb-window *,.pcb-window *:before,.pcb-window *:after{box-sizing:border-box;}' +
    '.pcb-header{' +
    'background:#16213e;padding:14px 16px;display:flex;align-items:center;gap:12px;' +
    'border-bottom:1px solid rgba(255,255,255,0.05);' +
    '}' +
    '.pcb-avatar{' +
    'width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#e94560,#0f3460);' +
    'display:flex;align-items:center;justify-content:center;color:#fff;' +
    'font-weight:700;font-size:13px;letter-spacing:.5px;flex-shrink:0;' +
    '}' +
    '.pcb-header-info{display:flex;flex-direction:column;line-height:1.2;}' +
    '.pcb-title{font-size:15px;font-weight:600;color:#fff;}' +
    '.pcb-subtitle{font-size:12px;color:#9aa4c7;margin-top:2px;}' +
    '.pcb-close{' +
    'margin-left:auto;background:transparent;border:none;color:#9aa4c7;' +
    'font-size:22px;cursor:pointer;line-height:1;padding:4px 8px;border-radius:8px;' +
    '}' +
    '.pcb-close:hover{background:rgba(255,255,255,0.06);color:#fff;}' +
    '.pcb-messages{' +
    'flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;' +
    'background:#1a1a2e;' +
    '}' +
    '.pcb-messages::-webkit-scrollbar{width:6px;}' +
    '.pcb-messages::-webkit-scrollbar-thumb{background:#2a2a44;border-radius:3px;}' +
    '.pcb-msg{' +
    'max-width:78%;padding:10px 14px;border-radius:14px;font-size:14px;line-height:1.45;' +
    'word-wrap:break-word;white-space:pre-wrap;' +
    '}' +
    '.pcb-msg-bot{background:#0f3460;color:#fff;align-self:flex-start;border-bottom-left-radius:4px;}' +
    '.pcb-msg-user{background:#e94560;color:#fff;align-self:flex-end;border-bottom-right-radius:4px;}' +
    '.pcb-typing{' +
    'align-self:flex-start;background:#0f3460;padding:12px 14px;border-radius:14px;' +
    'border-bottom-left-radius:4px;display:flex;gap:4px;align-items:center;' +
    '}' +
    '.pcb-typing span{' +
    'width:7px;height:7px;border-radius:50%;background:#9aa4c7;display:inline-block;' +
    'animation:pcb-bounce 1.2s infinite ease-in-out;' +
    '}' +
    '.pcb-typing span:nth-child(2){animation-delay:.15s;}' +
    '.pcb-typing span:nth-child(3){animation-delay:.3s;}' +
    '@keyframes pcb-bounce{' +
    '0%,60%,100%{transform:translateY(0);opacity:.5;}' +
    '30%{transform:translateY(-6px);opacity:1;}' +
    '}' +
    '.pcb-input-area{' +
    'display:flex;gap:8px;padding:12px;background:#16213e;' +
    'border-top:1px solid rgba(255,255,255,0.05);' +
    '}' +
    '.pcb-input{' +
    'flex:1;background:#16213e;border:1px solid #2a3a5e;border-radius:12px;' +
    'padding:10px 12px;color:#f0f0f5;font-size:14px;outline:none;' +
    'font-family:inherit;' +
    '}' +
    '.pcb-input:focus{border-color:#e94560;}' +
    '.pcb-input::placeholder{color:#7a85a8;}' +
    '.pcb-send{' +
    'background:#e94560;border:none;color:#fff;border-radius:12px;padding:0 16px;' +
    'cursor:pointer;font-weight:600;font-size:14px;transition:background .2s;' +
    '}' +
    '.pcb-send:hover:not(:disabled){background:#ff5673;}' +
    '.pcb-send:disabled{background:#5a2330;cursor:not-allowed;opacity:.7;}' +
    '';

  var styleEl = document.createElement('style');
  styleEl.setAttribute('data-pcb-widget', 'true');
  styleEl.appendChild(document.createTextNode(styles));
  document.head.appendChild(styleEl);

  // ---- Build DOM ----
  var launcher = document.createElement('button');
  launcher.className = 'pcb-launcher';
  launcher.setAttribute('aria-label', 'Otwórz czat');
  launcher.innerHTML =
    '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">' +
    '<path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>' +
    '</svg>';

  var win = document.createElement('div');
  win.className = 'pcb-window';
  win.innerHTML =
    '<div class="pcb-header">' +
    '<div class="pcb-avatar">AI</div>' +
    '<div class="pcb-header-info">' +
    '<div class="pcb-title"></div>' +
    '<div class="pcb-subtitle">Online</div>' +
    '</div>' +
    '<button class="pcb-close" aria-label="Zamknij czat">&times;</button>' +
    '</div>' +
    '<div class="pcb-messages" role="log" aria-live="polite"></div>' +
    '<div class="pcb-input-area">' +
    '<input class="pcb-input" type="text" placeholder="Napisz wiadomość..." />' +
    '<button class="pcb-send">Wyślij</button>' +
    '</div>';

  // Set configurable title safely (avoid HTML injection from data-* attr)
  win.querySelector('.pcb-title').textContent = COMPANY_NAME;

  document.body.appendChild(launcher);
  document.body.appendChild(win);

  var messagesEl = win.querySelector('.pcb-messages');
  var inputEl = win.querySelector('.pcb-input');
  var sendBtn = win.querySelector('.pcb-send');
  var closeBtn = win.querySelector('.pcb-close');

  // ---- Behavior ----
  function toggleWindow() {
    win.classList.toggle('pcb-open');
    if (win.classList.contains('pcb-open')) {
      setTimeout(function () {
        inputEl.focus();
      }, 220);
    }
  }

  function addMessage(text, who) {
    var msg = document.createElement('div');
    msg.className = 'pcb-msg ' + (who === 'user' ? 'pcb-msg-user' : 'pcb-msg-bot');
    msg.textContent = text;
    messagesEl.appendChild(msg);
    scrollToBottom();
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function showTyping() {
    var t = document.createElement('div');
    t.className = 'pcb-typing';
    t.setAttribute('data-pcb-typing', 'true');
    t.innerHTML = '<span></span><span></span><span></span>';
    messagesEl.appendChild(t);
    scrollToBottom();
    return t;
  }

  function removeTyping(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function setSending(isSending) {
    sendBtn.disabled = isSending;
    inputEl.disabled = isSending;
  }

  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || sendBtn.disabled) return;

    addMessage(text, 'user');
    inputEl.value = '';
    setSending(true);
    var typingEl = showTyping();

    fetch(API_URL.replace(/\/$/, '') + '/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text, company_id: COMPANY_ID })
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        removeTyping(typingEl);
        var answer =
          data && typeof data.answer === 'string'
            ? data.answer
            : 'Przepraszam, wystąpił błąd. Spróbuj ponownie.';
        addMessage(answer, 'bot');
      })
      .catch(function () {
        removeTyping(typingEl);
        addMessage('Przepraszam, wystąpił błąd. Spróbuj ponownie.', 'bot');
      })
      .then(function () {
        setSending(false);
        inputEl.focus();
      });
  }

  // Greeting
  addMessage('Cześć! W czym mogę pomóc?', 'bot');

  // Events
  launcher.addEventListener('click', toggleWindow);
  closeBtn.addEventListener('click', toggleWindow);
  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
})();
