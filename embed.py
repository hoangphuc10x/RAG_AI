"""
Step 4: Create an embedding for each chunk and save them to disk.

Needs: Ollama running (open the Ollama app) + nomic-embed-text pulled.
Run:  python embed.py
"""

import json
import requests
import numpy as np

# Reuse the two functions written in Step 3 to get the list of chunks
from uploadAndChunk import read_pdf, chunk_text
from pathlib import Path


# Ollama's embedding API endpoint (runs locally on your machine)
OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


# ---------------------------------------------------------------------------
# Send one piece of text to Ollama, get back an embedding vector (a list of numbers)
# ---------------------------------------------------------------------------
def embed_text(text):
    res = requests.post(OLLAMA_EMBED_URL, json={
        "model": EMBED_MODEL,
        "prompt": text,
    })
    res.raise_for_status()              # raise immediately if something is wrong (e.g. Ollama not running)
    return res.json()["embedding"]      # pull the "embedding" field from the response


if __name__ == "__main__":
    # 1) Collect chunks from every PDF in docs/
    all_chunks = []
    for pdf_file in Path("docs").glob("*.pdf"):
        content = read_pdf(pdf_file)
        all_chunks.extend(chunk_text(content))
    print(f"Got {len(all_chunks)} chunks, creating embeddings...")

    # 2) Create an embedding for each chunk
    vectors = []
    for i, chunk in enumerate(all_chunks):
        # nomic-embed-text requires the "search_document: " prefix for documents
        vector = embed_text("search_document: " + chunk)
        vectors.append(vector)
        print(f"  chunk {i+1}/{len(all_chunks)}  ->  {len(vector)}-dim vector")

    # 3) Save:
    #    - vectors.npy : numeric matrix (one vector per row) -> numpy saves it fast
    #    - chunks.json : list of chunk texts (so we know which vector maps to which text)
    np.save("vectors.npy", np.array(vectors, dtype=np.float32))
    with open("chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print("\nSaved: vectors.npy + chunks.json")
