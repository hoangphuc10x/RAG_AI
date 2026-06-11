"""
Step 3: Read PDF documents and split them into chunks (small pieces).

Run:  python uploadAndChunk.py
"""

from pathlib import Path
from pypdf import PdfReader


# ---------------------------------------------------------------------------
# Function 1: Read one PDF file -> return all its text as a single string
# ---------------------------------------------------------------------------
def read_pdf(file_path):
    reader = PdfReader(file_path)               # open the PDF file
    pages = []
    for page in reader.pages:                   # loop over each page
        pages.append(page.extract_text())       # extract text from the page
    return "\n".join(pages)                      # join all pages together


# ---------------------------------------------------------------------------
# Function 2: Split a long text into chunks with overlap
#   - words_per_chunk: how many words each chunk holds
#   - overlap_words  : how many trailing words each chunk repeats from the previous one
# ---------------------------------------------------------------------------
def chunk_text(text, words_per_chunk=120, overlap_words=20):
    words = text.split()                        # split the string into a list of words
    chunks = []
    pos = 0
    while pos < len(words):
        # take a slice of 'words_per_chunk' words from the current position
        slice_words = words[pos : pos + words_per_chunk]
        chunks.append(" ".join(slice_words))    # join them back into one piece of text
        # advance, stepping back 'overlap_words' to create the overlap
        pos += words_per_chunk - overlap_words
    return chunks


# ---------------------------------------------------------------------------
# Quick test: read every PDF in docs/ and split into chunks
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    docs_dir = Path("docs")
    all_chunks = []

    for pdf_file in docs_dir.glob("*.pdf"):     # find every .pdf file
        print(f"Reading: {pdf_file.name}")
        content = read_pdf(pdf_file)
        chunks = chunk_text(content)
        print(f"  -> got {len(chunks)} chunks")
        all_chunks.extend(chunks)

    print(f"\nTOTAL: {len(all_chunks)} chunks")
    print("\n--- First chunk ---")
    print(all_chunks[0])
    print("\n--- Second chunk (notice the repeated overlap) ---")
    print(all_chunks[1])
