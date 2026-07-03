"""
Web UI for the RAG chatbot (backend only).

- Upload a PDF  -> it is saved to docs/ and the index is rebuilt
- Ask a question -> the RAG answers, grounded in the uploaded documents

Front-end lives in:  templates/index.html + static/style.css + static/app.js
Needs: Ollama running.
Run:  python app.py    then open http://localhost:5000
"""

import json
from pathlib import Path

import numpy as np
from flask import Flask, request, jsonify, render_template

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
    return render_template("index.html")


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


if __name__ == "__main__":
    load_existing()
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="127.0.0.1", port=5000, debug=False)
