# 📚 AI-RAG — Chatbot hỏi đáp tài liệu (RAG)

Một dự án RAG (Retrieval-Augmented Generation) đơn giản để học: nạp file PDF, tách thành các đoạn nhỏ (chunk), tạo embedding, tìm đoạn liên quan nhất với câu hỏi, rồi để LLM trả lời **chỉ dựa trên tài liệu đó**.

Mọi thứ chạy **hoàn toàn local** bằng [Ollama](https://ollama.com) — không cần API key, không gửi dữ liệu ra ngoài.

---

## 🧱 Kiến trúc

```
PDF trong docs/
   │  read_pdf + chunk_text        (uploadAndChunk.py)
   ▼
Các đoạn text (chunks)
   │  embed_text -> nomic-embed-text   (embed.py)
   ▼
vectors.npy  +  chunks.json        (kho vector lưu trên đĩa)
   │  cosine_similarity            (step5_search.py)
   ▼
Top-3 đoạn liên quan nhất
   │  build_prompt + ask_llm -> qwen2.5:3b   (rag.py)
   ▼
Câu trả lời
```

| File                 | Vai trò |
|----------------------|---------|
| `uploadAndChunk.py`  | Đọc PDF và cắt thành chunk |
| `embed.py`           | Tạo embedding cho mỗi chunk, lưu `vectors.npy` + `chunks.json` |
| `step5_search.py`    | Tìm các chunk liên quan nhất (cosine similarity) |
| `rag.py`             | RAG dạng dòng lệnh (hỏi đáp trong terminal) |
| `app.py`             | Giao diện web (upload PDF + chat) bằng Flask |

---

## ✅ Yêu cầu trước khi chạy

1. **Python 3.10+** (dự án đang dùng 3.14).
2. **Ollama** đã cài và đang chạy — tải tại <https://ollama.com>.
3. Đã tải 2 model về máy:

```bash
ollama pull nomic-embed-text   # model tạo embedding (768 chiều)
ollama pull qwen2.5:3b         # model sinh câu trả lời
```

> Ollama mặc định chạy tại `http://localhost:11434`. Mở app Ollama (hoặc chạy `ollama serve`) trước khi chạy dự án.

---

## 🚀 Cài đặt

```bash
# 1) Tạo môi trường ảo
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2) Cài thư viện
pip install -r requirements.txt
```

---

## ▶️ Cách chạy

### Cách 1 — Giao diện web (khuyên dùng)

```bash
python app.py
venv/bin/python app.py
```

Mở trình duyệt tại <http://127.0.0.1:5000>, sau đó:
1. **Upload một file PDF** → hệ thống tự lưu vào `docs/` và dựng lại index.
2. **Gõ câu hỏi** → chatbot trả lời kèm trích dẫn nguồn.

### Cách 2 — Chạy trong terminal (theo từng bước)

```bash
# Đặt file PDF của bạn vào thư mục docs/ trước, rồi:

python embed.py          # tạo embedding -> sinh vectors.npy + chunks.json
python step5_search.py   # (tùy chọn) thử tìm chunk liên quan
python rag.py            # hỏi đáp trong terminal, gõ 'quit' để thoát
```

> Lưu ý: `step5_search.py` và `rag.py` cần `vectors.npy` + `chunks.json` đã tồn tại,
> nên **phải chạy `embed.py` trước** (hoặc upload ít nhất 1 PDF qua giao diện web).

---

## 🔧 Tùy chỉnh

| Muốn đổi | Sửa ở đâu |
|----------|-----------|
| Kích thước chunk / độ chồng lấn | `chunk_text(..., words_per_chunk=120, overlap_words=20)` trong `uploadAndChunk.py` |
| Số đoạn lấy ra để trả lời | `top_k=3` trong `step5_search.py` (và `[:3]` trong `app.py`) |
| Model embedding | `EMBED_MODEL` trong `embed.py` |
| Model trả lời | `CHAT_MODEL` trong `rag.py` |
| Cổng web | `port=5055` trong `app.py` |

---

## ❓ Lỗi thường gặp

- **`requests.exceptions.ConnectionError` / báo lỗi khi embed hoặc hỏi** → Ollama chưa chạy. Mở app Ollama hoặc chạy `ollama serve`.
- **`model not found`** → chưa `ollama pull` model tương ứng (`nomic-embed-text`, `qwen2.5:3b`).
- **`FileNotFoundError: vectors.npy`** → chưa chạy `embed.py` (hoặc chưa upload PDF nào qua web).
