"""
Simple web UI for the RAG chatbot.

- Upload a PDF  -> it is saved to docs/ and the index is rebuilt
- Ask a question -> the RAG answers, grounded in the uploaded documents

Needs: Ollama running.
Run:  python app.py    then open http://localhost:5000
"""

import json
from pathlib import Path

import numpy as np
from flask import Flask, request, jsonify, render_template_string

# Reuse the RAG building blocks we already wrote
from uploadAndChunk import read_pdf, chunk_text
from embed import embed_text
from step5_search import cosine_similarity
from rag import ask_llm, build_prompt

DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# In-memory index (loaded once, rebuilt after each upload)
CHUNKS = []
VECTORS = np.zeros((0, 768), dtype=np.float32)


# ---------------------------------------------------------------------------
# Rebuild the index from every PDF in docs/ (same logic as embed.py)
# ---------------------------------------------------------------------------
def rebuild_index():
    global CHUNKS, VECTORS
    chunks = []
    for pdf_file in DOCS_DIR.glob("*.pdf"):
        chunks.extend(chunk_text(read_pdf(pdf_file)))

    vectors = [embed_text("search_document: " + c) for c in chunks]
    CHUNKS = chunks
    VECTORS = np.array(vectors, dtype=np.float32) if vectors else np.zeros((0, 768), np.float32)

    # also persist to disk so rag.py / step5_search.py keep working
    np.save("vectors.npy", VECTORS)
    with open("chunks.json", "w", encoding="utf-8") as f:
        json.dump(CHUNKS, f, ensure_ascii=False, indent=2)
    return len(CHUNKS)


# ---------------------------------------------------------------------------
# Load any existing index on startup (so we don't lose previous uploads)
# ---------------------------------------------------------------------------
def load_existing():
    global CHUNKS, VECTORS
    if Path("vectors.npy").exists() and Path("chunks.json").exists():
        VECTORS = np.load("vectors.npy")
        with open("chunks.json", encoding="utf-8") as f:
            CHUNKS = json.load(f)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template_string(PAGE)


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".pdf"):
        return jsonify({"ok": False, "message": "Please choose a .pdf file."}), 400
    # save into docs/ then rebuild the index
    save_path = DOCS_DIR / file.filename
    file.save(save_path)
    n = rebuild_index()
    return jsonify({"ok": True, "message": f"Uploaded '{file.filename}'. Index now has {n} chunks."})


@app.route("/ask", methods=["POST"])
def ask():
    question = (request.json or {}).get("question", "").strip()
    if not question:
        return jsonify({"answer": "Please type a question.", "sources": []})
    if len(CHUNKS) == 0:
        return jsonify({"answer": "No documents yet — upload a PDF first.", "sources": []})

    # Retrieve top-3 chunks (same as step5_search.search, but using in-memory index)
    query_vec = np.array(embed_text("search_query: " + question), dtype=np.float32)
    scores = cosine_similarity(query_vec, VECTORS)
    order = np.argsort(scores)[::-1][:3]
    relevant = [(CHUNKS[i], float(scores[i])) for i in order]

    answer = ask_llm(build_prompt(question, relevant))
    sources = [c[:160] + "..." for c, _ in relevant]
    return jsonify({"answer": answer, "sources": sources})


# ---------------------------------------------------------------------------
# The whole front-end in one HTML string (upload box + chat box)
# ---------------------------------------------------------------------------
PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RAG Chatbot</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 24px auto; padding: 0 16px; }
    h1 { font-size: 20px; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
    #chat { min-height: 200px; max-height: 420px; overflow-y: auto; }
    .msg { padding: 8px 12px; border-radius: 10px; margin: 6px 0; white-space: pre-wrap; }
    .me  { background: #e7f0ff; text-align: right; }
    .bot { background: #f2f2f2; }
    .src { font-size: 12px; color: #666; margin-top: 4px; }
    input[type=text] { width: 100%; padding: 10px; box-sizing: border-box; }
    button { padding: 10px 16px; cursor: pointer; }
    #status { font-size: 13px; color: #555; }
    .row { display: flex; gap: 8px; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>📚 RAG Chatbot</h1>

  <div class="card">
    <b>1) Upload a PDF</b>
    <div class="row">
      <input type="file" id="file" accept="application/pdf">
      <button onclick="upload()">Upload</button>
    </div>
    <div id="status"></div>
  </div>

  <div class="card">
    <b>2) Ask a question</b>
    <div id="chat"></div>
    <div class="row">
      <input type="text" id="q" placeholder="Type your question..." onkeydown="if(event.key==='Enter' && !event.isComposing)askQ()">
      <button onclick="askQ()">Send</button>
    </div>
  </div>

<script>
function add(text, cls, sources) {
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'msg ' + cls;
  div.textContent = text;
  if (sources && sources.length) {
    const s = document.createElement('div');
    s.className = 'src';
    s.textContent = 'Sources: ' + sources.join(' | ');
    div.appendChild(s);
  }
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function upload() {
  const f = document.getElementById('file').files[0];
  const status = document.getElementById('status');
  if (!f) { status.textContent = 'Choose a file first.'; return; }
  status.textContent = 'Uploading & indexing... (this can take a few seconds)';
  const fd = new FormData(); fd.append('file', f);
  const res = await fetch('/upload', { method: 'POST', body: fd });
  const data = await res.json();
  status.textContent = data.message;
}

async function askQ() {
  const input = document.getElementById('q');
  const q = input.value.trim();
  if (!q) return;
  add(q, 'me');
  input.value = '';
  add('...thinking', 'bot');
  const chat = document.getElementById('chat');
  const thinking = chat.lastChild;
  const res = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q })
  });
  const data = await res.json();
  chat.removeChild(thinking);
  add(data.answer, 'bot', data.sources);
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    load_existing()
    print("Open http://127.0.0.1:5055 in your browser")
    app.run(host="127.0.0.1", port=5055, debug=False)
