(function () {
  var SEND_ICON =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"' +
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="22" y1="2" x2="11" y2="13"></line>' +
    '<polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
  var SPINNER = '<span class="spinner"></span>';

  var $ = function (id) { return document.getElementById(id); };

  // ---- Toast (floating notification, auto-dismiss with a 3s countdown) ----
  var TOAST_MS = 3000;
  var toastWrap = null;
  function showToast(type, text) {
    if (!toastWrap) {
      toastWrap = document.createElement('div');
      toastWrap.className = 'toast-wrap';
      document.body.appendChild(toastWrap);
    }
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;

    var body = document.createElement('div');
    body.className = 'toast-body';
    var icon = document.createElement('span');
    icon.textContent = type === 'ok' ? '✅' : type === 'err' ? '⚠️' : 'ℹ️';
    var msg = document.createElement('span');
    msg.textContent = text;
    body.appendChild(icon);
    body.appendChild(msg);

    var bar = document.createElement('div');
    bar.className = 'bar';
    bar.style.animationDuration = TOAST_MS + 'ms';  // countdown length

    toast.appendChild(body);
    toast.appendChild(bar);
    toastWrap.appendChild(toast);

    function dismiss() {
      toast.classList.add('out');
      setTimeout(function () { if (toast.parentNode) toast.remove(); }, 300);
    }
    var timer = setTimeout(dismiss, TOAST_MS);
    toast.addEventListener('click', function () { clearTimeout(timer); dismiss(); });  // tap to close early
  }

  // ---- Upload -------------------------------------------------------------
  var dropzone = $('dropzone'), fileInput = $('fileInput'), uploadBtn = $('uploadBtn');
  var dzIcon = $('dzIcon'), dzTitle = $('dzTitle'), dzSub = $('dzSub'), statusEl = $('status');
  var selectedFile = null, uploading = false;

  function setStatus(type, text) {
    if (!type) { statusEl.innerHTML = ''; return; }
    var icon = type === 'ok' ? '✅' : type === 'err' ? '⚠️' : '⏳';
    statusEl.innerHTML = '<div class="status ' + type + '"><span>' + icon + '</span><span></span></div>';
    statusEl.querySelector('span:last-child').textContent = text;
  }

  function pickFile(f) {
    if (!f) return;
    if (!/\.pdf$/i.test(f.name)) { showToast('err', 'Please choose a .pdf file.'); return; }
    selectedFile = f;
    dzIcon.textContent = '📄';
    dzTitle.textContent = f.name;
    dzSub.textContent = 'Ready to index';
    uploadBtn.disabled = false;
    setStatus(null);
  }

  // Return the upload box to its initial, empty state (called after success).
  function resetUploader() {
    selectedFile = null;
    fileInput.value = '';
    dzIcon.textContent = '⬆️';
    dzTitle.textContent = 'Drop a PDF here or click to browse';
    dzSub.textContent = 'Only .pdf files are supported';
    uploadBtn.disabled = true;
  }

  dropzone.addEventListener('click', function () { fileInput.click(); });
  fileInput.addEventListener('change', function (e) { pickFile(e.target.files[0]); });
  dropzone.addEventListener('dragover', function (e) { e.preventDefault(); dropzone.classList.add('drag'); });
  dropzone.addEventListener('dragleave', function () { dropzone.classList.remove('drag'); });
  dropzone.addEventListener('drop', function (e) {
    e.preventDefault();
    dropzone.classList.remove('drag');
    pickFile(e.dataTransfer.files[0]);
  });

  uploadBtn.addEventListener('click', function () {
    if (!selectedFile || uploading) return;
    uploading = true;
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = SPINNER + ' Indexing…';
    setStatus('info', 'Uploading & indexing… this can take a few seconds.');
    var fd = new FormData();
    fd.append('file', selectedFile);
    fetch('/upload', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        uploading = false;
        uploadBtn.textContent = 'Upload & Index';
        setStatus(null);                     // clear the inline "indexing…" hint
        if (data.ok) {
          resetUploader();                   // back to the initial empty state
          showToast('ok', data.message);     // success toast, auto-dismiss in 3s
        } else {
          uploadBtn.disabled = false;        // keep the file so the user can retry
          showToast('err', data.message);
        }
      })
      .catch(function () {
        uploading = false;
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload & Index';
        setStatus(null);
        showToast('err', 'Upload failed. Is the server running?');
      });
  });

  // ---- Chat ---------------------------------------------------------------
  var messages = $('messages'), qInput = $('q'), sendBtn = $('sendBtn');
  var emptyState = $('emptyState');
  var asking = false;
  sendBtn.innerHTML = SEND_ICON;

  function scrollDown() { messages.scrollTop = messages.scrollHeight; }

  function makeRow(role) {
    var row = document.createElement('div');
    row.className = 'row ' + role;
    var avatar = document.createElement('div');
    avatar.className = 'avatar ' + role;
    avatar.textContent = role === 'me' ? 'You' : '📚';
    var bubble = document.createElement('div');
    bubble.className = 'bubble ' + role;
    row.appendChild(avatar);
    row.appendChild(bubble);
    messages.appendChild(row);
    scrollDown();
    return { row: row, bubble: bubble };
  }

  function fillAnswer(bubble, text) {
    bubble.textContent = '';
    String(text).split(/\n{2,}/).forEach(function (para) {
      var p = document.createElement('p');
      para.split('\n').forEach(function (line, j) {
        if (j > 0) p.appendChild(document.createElement('br'));
        p.appendChild(document.createTextNode(line));
      });
      bubble.appendChild(p);
    });
  }

  function addSources(bubble, sources) {
    if (!sources || !sources.length) return;
    var wrap = document.createElement('div');
    wrap.className = 'sources';
    var btn = document.createElement('button');
    btn.className = 'src-toggle';
    var list = document.createElement('div');
    list.className = 'src-list';
    list.style.display = 'none';
    sources.forEach(function (s) {
      var item = document.createElement('div');
      item.className = 'src-item';
      item.textContent = s;
      list.appendChild(item);
    });
    var open = false;
    function label() { btn.textContent = (open ? '▾' : '▸') + ' 📎 Sources (' + sources.length + ')'; }
    label();
    btn.addEventListener('click', function () {
      open = !open;
      list.style.display = open ? 'flex' : 'none';
      label();
      scrollDown();
    });
    wrap.appendChild(btn);
    wrap.appendChild(list);
    bubble.appendChild(wrap);
  }

  function updateSendState() { sendBtn.disabled = asking || !qInput.value.trim(); }

  function send() {
    var question = qInput.value.trim();
    if (!question || asking) return;
    if (emptyState) { emptyState.remove(); emptyState = null; }

    asking = true;
    qInput.value = '';
    qInput.disabled = true;
    updateSendState();
    sendBtn.innerHTML = SPINNER;

    makeRow('me').bubble.textContent = question;
    var botBubble = makeRow('bot').bubble;
    botBubble.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';

    fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        fillAnswer(botBubble, data.answer);
        addSources(botBubble, data.sources);
      })
      .catch(function () {
        botBubble.textContent = 'Something went wrong reaching the server.';
      })
      .then(function () {
        asking = false;
        qInput.disabled = false;
        sendBtn.innerHTML = SEND_ICON;
        updateSendState();
        qInput.focus();
        scrollDown();
      });
  }

  qInput.addEventListener('input', updateSendState);
  qInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); send(); }
  });
  sendBtn.addEventListener('click', send);
})();
