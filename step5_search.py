"""
Step 5: Find the chunks most relevant to a question (Retrieval).

Needs: embed.py already run, so vectors.npy + chunks.json exist.
Run:  python step5_search.py
"""

import json
import numpy as np

# Reuse the embedding function written in Step 4 (embed.py)
from embed import embed_text


# ---------------------------------------------------------------------------
# Load the vector store saved in Step 4
# ---------------------------------------------------------------------------
def load_store():
    vectors = np.load("vectors.npy")                 # matrix (5 x 768)
    with open("chunks.json", encoding="utf-8") as f:
        chunks = json.load(f)                        # list of 5 chunk texts
    return chunks, vectors


# ---------------------------------------------------------------------------
# Cosine similarity between one question vector and ALL chunk vectors at once
# ---------------------------------------------------------------------------
def cosine_similarity(query_vec, chunk_matrix):
    # Normalize vectors to length 1, then a dot product = cosine
    query_vec = query_vec / np.linalg.norm(query_vec)
    chunk_matrix = chunk_matrix / np.linalg.norm(chunk_matrix, axis=1, keepdims=True)
    return chunk_matrix @ query_vec        # returns an array of scores, one per chunk


# ---------------------------------------------------------------------------
# Find the 'top_k' chunks most relevant to the question
# ---------------------------------------------------------------------------
def search(question, chunks, vectors, top_k=3):
    # nomic-embed-text requires the "search_query: " prefix for questions
    query_vec = np.array(embed_text("search_query: " + question), dtype=np.float32)
    scores = cosine_similarity(query_vec, vectors)    # a score for each chunk
    # argsort: indices sorted ascending -> reverse -> take the top_k highest
    order = np.argsort(scores)[::-1][:top_k]
    return [(chunks[i], float(scores[i])) for i in order]


if __name__ == "__main__":
    chunks, vectors = load_store()

    question = "What is a translation memory?"
    print(f"❓ Question: {question}\n")

    results = search(question, chunks, vectors)
    for rank, (chunk, score) in enumerate(results, start=1):
        print(f"#{rank}  (similarity: {score:.3f})")
        print(chunk[:200], "...\n")
