# 🏛️ Vault-ZeroBaran — Architecture Reference

## 1. الطبقات الأربع للنظام

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4 — Delivery & UI                                         │
│   • Telegram Bot API        (python-telegram-bot)               │
│   • Streamlit Dashboard     (لوحة ويب تفاعلية)                  │
│   • CLI                     (ingest_folder.py / query_cli.py)   │
└────────────────────────┬────────────────────────────────────────┘
                         │  HTTP / Telegram update
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3 — RAG Processing Core                                   │
│   • similarity_search()    (cosine top-K via pgvector HNSW)     │
│   • Prompt engineering     ("answer ONLY from context + cite")  │
│   • Gemini chat completion (fallback Groq llama-3.1-8b)         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2 — Vectorization & Storage                               │
│   • Gemini text-embedding-004  (768-dim, free)                  │
│   • Supabase pgvector          (HNSW cosine index)              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1 — Ingestion & Chunking                                  │
│   • PyMuPDF (PDF)  python-docx (DOCX)  openpyxl (XLSX)          │
│   • RecursiveCharacterTextSplitter (LangChain core)             │
│   • Hash-based stable chunk_id (deduplication)                  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. تكامل الطبقات (End-to-End RAG)

```
User: "ما هي سياسة الإرجاع؟"
  │
  ├──► embed_query(question)              [Gemini text-embedding-004]
  │         ↓ 768-dim vector
  ├──► similarity_search(vec, top_k=5)    [Supabase pgvector]
  │         ↓ 5 chunks: {file, page, content, score}
  ├──► build_prompt(question, context)    ["answer ONLY from context"]
  ├──► Gemini.generate_content(prompt)    [temperature=0.2]
  │         ↓ answer text
  └──► format_answer(answer + sources)    [chat-formatted output]
```

## 3. تصميم البيانات

### جدول `vault_chunks`
| العمود | النوع | الوصف |
|---|---|---|
| `id` | BIGSERIAL | مفتاح أساسي |
| `chunk_id` | TEXT UNIQUE | هاش SHA1 ثابت (dedup) |
| `source_file` | TEXT | اسم الملف الأصلي |
| `page` | INT | رقم الصفحة (1-indexed) |
| `section` | TEXT | عنوان القسم (اختياري) |
| `content` | TEXT | النص الكامل للجزء |
| `token_count` | INT | تقدير التوكنات |
| `metadata` | JSONB | مسار، حجم، صيغة، ... |
| `embedding` | vector(768) | متجه Gemini |
| `created_at` | TIMESTAMPTZ | تاريخ الإضافة |

### الفهارس (Indexes)
- `vault_chunks_embedding_idx` — HNSW على `embedding` للبحث الدلالي السريع.
- `vault_chunks_source_file_idx` — B-tree على `source_file` للحذف السريع.
- `vault_chunks_metadata_gin_idx` — GIN على `metadata` للاستعلامات.

## 4. التسامح مع الأخطاء (Resilience)
- **إعادة المحاولة** في `embed_texts()` عبر `tenacity` (5 محاولات مع backoff أُسّي).
- **Fallback بين Gemini و Groq** في `rag_engine.ask()` — إذا فشل Gemini، ينتقل النظام إلى Groq تلقائياً.
- **معرّفات ثابتة (hash-based chunk_id)** تمنع تكرار نفس الجزء عند إعادة الفهرسة.
- **ON CONFLICT DO UPDATE** في SQL يحدّث المتجه القديم بدلاً من الإدراج المتكرر.

## 5. حدود النطاق (Free Tier Limits)
| الخدمة | الحد المجاني |
|---|---|
| Gemini API | ~1500 طلب/يوم، 5M توكن/شهر |
| Supabase | 500MB تخزين، 50K صف شهرياً |
| GitHub Actions | 2000 دقيقة/شهر للمستودعات العامة |
| Groq | ~30 طلب/دقيقة، حد يومي مُتغيّر |
| Telegram Bot API | غير محدود عملياً (مجاني 100%) |
