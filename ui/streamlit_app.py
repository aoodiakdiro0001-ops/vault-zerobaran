"""
Vault-ZeroBaran — Streamlit Dashboard.

A self-contained web UI that lets you:
  • Upload documents (PDF / DOCX / XLSX / CSV / TXT / MD / code).
  • Watch live ingestion progress.
  • Ask questions in natural language.
  • See the precise answer with file + page citations.
  • Browse indexed documents and delete obsolete ones.

Run with:
    streamlit run ui/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make project root importable when running `streamlit run ui/streamlit_app.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from loguru import logger

from config.settings import settings
from core.utils import banner, save_upload, ingest_summary
from core.ingestion import ingest_file, _EXTRACTORS as SUPPORTED_EXTS_MAP
SUPPORTED_EXTS = sorted(SUPPORTED_EXTS_MAP.keys())

from core.vector_db import (
    ensure_schema,
    store_chunks,
    similarity_search,
    list_documents,
    delete_document,
    total_chunks,
)
from core.rag_engine import ask, format_answer_for_chat


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Vault-ZeroBaran — العقل المعرفي الذاتي",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — dark, modern, "vault" feel
st.markdown("""
<style>
    .stApp { background: #0e1117; color: #e6e6e6; }
    h1, h2, h3, h4 { color: #7dd3fc !important; }
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9, #2563eb);
        color: white; border: none; font-weight: 600;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #2563eb, #1e40af); }
    .source-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 8px; padding: 12px; margin-bottom: 8px;
    }
    .stat-card {
        background: #161b22; border-radius: 10px; padding: 16px;
        text-align: center;
    }
    .stat-card .num { font-size: 28px; color: #7dd3fc; font-weight: 700; }
    .stat-card .lbl { font-size: 12px; color: #9ca3af; }
    .footer { text-align: center; color: #6b7280; font-size: 11px;
              margin-top: 24px; border-top: 1px solid #30363d; padding-top: 12px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Init schema (cache so we only run once per session)
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _init_db():
    try:
        ensure_schema()
        return True, None
    except Exception as e:
        return False, str(e)


def _health_checks() -> dict:
    return {
        "Gemini API":   "✅" if settings.has_gemini   else "❌",
        "Groq API":     "✅" if settings.has_groq     else "—",
        "Supabase":     "✅" if settings.has_supabase else "❌",
        "Telegram Bot": "✅" if settings.has_telegram else "—",
    }


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🧠 Vault-ZeroBaran")
    st.caption("العقل المعرفي الذاتي واللامركزي")
    st.markdown("---")

    st.markdown("### 🔌 حالة الخدمات")
    for k, v in _health_checks().items():
        st.markdown(f"- {v}  **{k}**")

    st.markdown("---")
    st.markdown("### ⚙️ إعدادات")
    st.caption(f"**حجم الجزء:** {settings.vault_chunk_size} حرف")
    st.caption(f"**التداخل:** {settings.vault_chunk_overlap}")
    st.caption(f"**عدد القطع المسترجعة (K):** {settings.vault_top_k}")
    st.caption(f"**اللغة الافتراضية:** {settings.vault_language}")

    st.markdown("---")
    st.markdown("### 📤 رفع مستند")
    uploaded = st.file_uploader(
        "اختر ملفاً:",
        type=[e.lstrip(".") for e in SUPPORTED_EXTS],
        accept_multiple_files=False,
    )
    if uploaded and st.button("🚀 فهرسة الملف", use_container_width=True):
        with st.spinner("جاري الحفظ والتفريغ..."):
            tmp_path = settings.data_dir / uploaded.name
            with open(tmp_path, "wb") as f:
                f.write(uploaded.getbuffer())
            chunks = ingest_file(tmp_path)
            if not chunks:
                st.error("تعذّر استخراج أي نص من الملف. تأكد من صحة الملف.")
            else:
                with st.spinner("توليد المتجهات والتخزين في Supabase..."):
                    try:
                        stored = store_chunks(chunks)
                        st.success(f"✅ تمت فهرسة {stored} جزءاً من '{uploaded.name}'.")
                        st.session_state["last_summary"] = ingest_summary(chunks)
                    except Exception as e:
                        st.error(f"فشل التخزين: {e}")

    st.markdown("---")
    st.markdown(f"""
    <div class='footer'>
      {settings.ownership_block()}<br>
      Free Tech Stack · 2025
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.markdown(f"""
<pre style='color:#7dd3fc;font-size:11px;line-height:1.2;margin:0'>
{banner()}
</pre>
""", unsafe_allow_html=True)

st.markdown("## 🌐 مرحباً بك في عقلك المعرفي اللامركزي")
st.markdown(
    "اسأل أي سؤال عن مستنداتك — سيعيد النظام الإجابة الدقيقة مع ذكر اسم الملف ورقم الصفحة كمصدر."
)

# DB init
db_ok, db_err = _init_db()
if not db_ok:
    st.error(f"⚠️ تعذّر الاتصال بقاعدة بيانات Supabase. تحقق من `.env`.\n\n`{db_err}`")
    st.stop()

# Stats row
try:
    n_chunks = total_chunks()
    docs = list_documents()
    n_files = len(docs)
    n_tokens = sum(d["tokens"] for d in docs)
except Exception:
    n_chunks = n_files = n_tokens = 0
    docs = []

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"<div class='stat-card'><div class='num'>{n_files}</div>"
                f"<div class='lbl'>ملف مفهرس</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='stat-card'><div class='num'>{n_chunks:,}</div>"
                f"<div class='lbl'>جزء دلالي</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='stat-card'><div class='num'>{n_tokens:,}</div>"
                f"<div class='lbl'>توكن تقريبي</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ----- Ask box -----
st.markdown("## ❓ اطرح سؤالك")
question = st.text_input(
    "سؤالك:",
    placeholder="مثال: ما هي سياسة الإرجاع؟ أو: ما البند المالي في عقد الشراكة 2025؟",
)
col_q1, col_q2 = st.columns([1, 5])
with col_q1:
    ask_btn = st.button("🔍 اسأل Vault-ZeroBaran", use_container_width=True)
with col_q2:
    top_k = st.slider("عدد المصادر المرجعية (K)", min_value=1, max_value=20,
                      value=settings.vault_top_k)

if ask_btn and question.strip():
    with st.spinner("جارٍ البحث الدلالي وصياغة الإجابة..."):
        try:
            result = ask(question, top_k=top_k)
        except Exception as e:
            st.error(f"فشل الاستعلام: {e}")
            st.stop()

    # Answer
    st.markdown("### 💡 الإجابة")
    st.markdown(result.answer)

    # Sources
    if result.sources:
        st.markdown("### 📌 المصادر")
        for i, s in enumerate(result.sources, start=1):
            score_pct = int(s["score"] * 100)
            st.markdown(
                f"""
                <div class='source-card'>
                  <b>#{i}</b> 📄 <i>{s['source_file']}</i>
                  &nbsp;— صفحة <b>{s['page']}</b>
                  &nbsp;<span style='color:#9ca3af'>(تطابق دلالي: {score_pct}%)</span>
                  <br><small>{s['snippet']}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.caption(f"Backend: `{result.backend}` — {settings.ownership_block()}")

# ----- Documents table -----
st.markdown("---")
st.markdown("## 📚 المستندات المفهرسة")
if not docs:
    st.info("لا توجد مستندات بعد. ارفع أول ملف من الشريط الجانبي ←")
else:
    for d in docs:
        with st.expander(f"📄 {d['source_file']}  —  {d['chunks']} جزءاً  —  {d['tokens']:,} توكن"):
            st.markdown(f"- **الأجزاء:** {d['chunks']}")
            st.markdown(f"- **التوكنات:** {d['tokens']:,}")
            st.markdown(f"- **نطاق الصفحات:** {d['first_page']} → {d['last_page']}")
            st.markdown(f"- **آخر فهرسة:** `{d['last_indexed']}`")
            if st.button(f"🗑️ حذف '{d['source_file']}'", key=f"del_{d['source_file']}"):
                try:
                    deleted = delete_document(d["source_file"])
                    st.success(f"تم حذف {deleted} جزءاً.")
                    st.rerun()
                except Exception as e:
                    st.error(f"فشل الحذف: {e}")
