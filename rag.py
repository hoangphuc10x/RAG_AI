"""
Step 6: Full RAG — question answering grounded in the documents under docs/.

Needs: Ollama running + embed.py already run (vectors.npy, chunks.json exist).
Run:  python rag.py
"""

import requests
from step5_search import load_store, search


OLLAMA_CHAT_URL = "http://localhost:11434/api/generate"
CHAT_MODEL = "qwen2.5:3b"


# ---------------------------------------------------------------------------
# Send a prompt to the model and get the answer (generation model, not the embedder)
# ---------------------------------------------------------------------------
def ask_llm(prompt):
    res = requests.post(OLLAMA_CHAT_URL, json={
        "model": CHAT_MODEL,
        "prompt": prompt,
        "stream": False,          # get the whole answer in one shot for simplicity
    })
    res.raise_for_status()
    return res.json()["response"]


# ---------------------------------------------------------------------------
# Combine the relevant chunks + the question into one prompt for the LLM
# ---------------------------------------------------------------------------
def build_prompt(question, relevant_chunks):
    context = "\n\n".join(f"- {chunk}" for chunk, _score in relevant_chunks)
    return f"""You are an assistant that answers based only on the provided documents.
Use only the information in the DOCUMENTS section below to answer.
If the documents do not contain the answer, say "I could not find that in the documents."

DOCUMENTS:
{context}

QUESTION: {question}

ANSWER (in English, concise):"""


if __name__ == "__main__":
    # Load the store once at startup
    chunks, vectors = load_store()
    print("RAG ready! Type a question (type 'quit' to stop).\n")

    while True:
        question = input("❓ You: ").strip()
        if question.lower() in ("quit", "exit", ""):
            print("Bye!")
            break

        # 1) Find relevant chunks (Step 5)
        relevant_chunks = search(question, chunks, vectors, top_k=3)
        # 2) Build the prompt + 3) Ask the LLM
        prompt = build_prompt(question, relevant_chunks)
        answer = ask_llm(prompt)

        print(f"\n💬 Answer: {answer}\n")
