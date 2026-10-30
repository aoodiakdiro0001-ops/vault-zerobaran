"""
Vault-ZeroBaran — RAG (Retrieval-Augmented Generation) Core.

Pipeline:
    User question
        └─► vector_db.similarity_search()  → top-K chunks
            └─► Build a strict prompt: "answer ONLY from the context,
                cite the source file + page number"
                └─► Gemini chat completion → final answer
                    └─► Formatted response with citations

Falls back to Groq (llama-3.1-8b-instant) if Gemini is unreachable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from config.settings import settings
from core.vector_db import similarity_search

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq as GroqClient
except ImportError:
    GroqClient = None


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------
@dataclass
class AnswerResult:
    answer: str
    sources: list[dict]            # list of {source_file, page, section, score, snippet}
    raw_chunks: list[dict]
    backend: str                   # "gemini" | "groq" | "none"


# ---------------------------------------------------------------------------
# Prompt engineering
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT_AR = """\
أنت مساعد ذكي يعمل ضمن نظام "Vault-ZeroBaran".
مهمتك: الإجابة عن سؤال المستخدم بناءً على المستندات المرفقة فقط.

قواعد صارمة:
1. استخدم فقط المعلومات الموجودة في "السياق" أدناه. لا تخترع أي معلومة.
2. إذا لم تكن الإجابة موجودة في السياق، قل صراحة: "لا توجد معلومة كافية في المستندات."
3. في نهاية إجابتك، اذكر المصدر بصيغة: "المصدر: <اسم الملف> — صفحة <رقم>".
4. اجعل إجابتك دقيقة وموجزة ومباشرة. تجنب الحشو.
5. حافظ على لغة سؤال المستخدم (عربي/إنجليزي).
"""

_SYSTEM_PROMPT_EN = """\
You are an assistant inside the "Vault-ZeroBaran" system.
Your job: answer the user's question using ONLY the attached context.

Strict rules:
1. Use only information present in the "Context" below. Never invent facts.
2. If the answer is not in the context, say: "Insufficient information in the documents."
3. Always cite the source as: "Source: <filename> — page <number>".
4. Be precise, concise, and direct. No filler.
5. Match the user's language.
"""


def _build_context(chunks: list[dict]) -> str:
    """Render retrieved chunks into a numbered context block."""
    blocks = []
    for i, c in enumerate(chunks, start=1):
        snippet = c["content"][:1200].replace("\n", " ").strip()
        blocks.append(
            f"[{i}] الملف: {c['source_file']} | الصفحة: {c['page']}\n"
            f"    المحتوى: {snippet}"
        )
    return "\n\n".join(blocks)


def _build_prompt(question: str, context: str) -> str:
    lang = settings.vault_language
    sys_prompt = _SYSTEM_PROMPT_AR if lang == "ar" else _SYSTEM_PROMPT_EN
    return (
        f"{sys_prompt}\n\n"
        f"=== السياق / Context ===\n{context}\n"
        f"=== نهاية السياق ===\n\n"
        f"سؤال المستخدم: {question}\n"
        f"الإجابة:"
    )


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------
def _genai_chat(prompt: str) -> Optional[str]:
    if genai is None or not settings.has_gemini:
        return None
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_chat_model)
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": settings.vault_temperature,
                "max_output_tokens": settings.vault_max_tokens,
            },
        )
        return resp.text.strip()
    except Exception as e:
        logger.warning(f"Gemini chat failed: {e}")
        return None


def _groq_chat(prompt: str) -> Optional[str]:
    if GroqClient is None or not settings.has_groq:
        return None
    try:
        client = GroqClient(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model=settings.groq_chat_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.vault_temperature,
            max_tokens=settings.vault_max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq chat failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ask(question: str, top_k: int | None = None) -> AnswerResult:
    """
    End-to-end RAG pipeline.

    1) Retrieve top-K chunks via pgvector cosine search.
    2) Build a strict prompt with citations.
    3) Generate the answer via Gemini (fallback Groq).
    4) Return structured AnswerResult with sources.
    """
    logger.info(f"RAG ask: '{question[:80]}...'")

    # 1) Retrieve
    chunks = similarity_search(question, top_k=top_k)
    if not chunks:
        return AnswerResult(
            answer="⚠️ لا توجد مستندات مفهرسة بعد. ارفع ملفاتك أولاً عبر تليجرام أو واجهة Streamlit.",
            sources=[],
            raw_chunks=[],
            backend="none",
        )

    # 2) Build prompt
    context = _build_context(chunks)
    prompt = _build_prompt(question, context)

    # 3) Generate
    answer_text = _genai_chat(prompt)
    backend = "gemini"
    if not answer_text:
        answer_text = _groq_chat(prompt)
        backend = "groq"
    if not answer_text:
        answer_text = (
            "⚠️ تعذّر توليد الإجابة من Gemini و Groq. تحقق من مفاتيح الـ API في ملف .env"
        )
        backend = "none"

    # 4) Build sources list
    sources = [
        {
            "source_file": c["source_file"],
            "page": c["page"],
            "section": c["section"],
            "score": round(c["score"], 4),
            "snippet": c["content"][:280].replace("\n", " ").strip(),
        }
        for c in chunks
    ]

    return AnswerResult(
        answer=answer_text,
        sources=sources,
        raw_chunks=chunks,
        backend=backend,
    )


def format_answer_for_chat(result: AnswerResult) -> str:
    """Render an AnswerResult as a Telegram / chat-friendly string."""
    out = [f"💡 <b>الإجابة:</b>\n{result.answer}"]
    if result.sources:
        out.append("\n📌 <b>المصادر:</b>")
        for i, s in enumerate(result.sources, start=1):
            score_pct = int(round(s["score"] * 100))
            out.append(
                f"  {i}. 📄 <i>{s['source_file']}</i> — صفحة {s['page']} "
                f"(تطابق: {score_pct}%)"
            )
    out.append(f"\n— <i>powered by Vault-ZeroBaran ({result.backend})</i>")
    return "\n".join(out)
