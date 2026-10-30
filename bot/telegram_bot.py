"""
Vault-ZeroBaran — Telegram Bot.

Features:
  • /start        — Welcome + usage.
  • /stats        — Vault statistics.
  • /list         — List indexed documents.
  • /delete <name>— Delete a document from the vault.
  • /help         — Show commands.
  • Send a file   — Bot ingests it, embeds it, stores it in Supabase.
  • Send a text   — Bot treats it as a question, returns the answer
                    + citations.

Run:
    python -m bot.telegram_bot
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.settings import settings
from core.utils import banner, save_upload, ingest_summary
from core.ingestion import ingest_file, _EXTRACTORS as SUPPORTED_EXTS_MAP
from core.vector_db import (
    ensure_schema,
    store_chunks,
    list_documents,
    delete_document,
    total_chunks,
)
from core.rag_engine import ask, format_answer_for_chat

SUPPORTED_EXTS = sorted(SUPPORTED_EXTS_MAP.keys())
ALLOWED_EXTS = [e.lstrip(".") for e in SUPPORTED_EXTS]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧠 <b>Vault-ZeroBaran</b>\n"
        "العقل المعرفي الذاتي واللامركزي لمستنداتك.\n\n"
        "<b>كيف يعمل؟</b>\n"
        "1️⃣ أرسل أي ملف (PDF / DOCX / XLSX / TXT / CSV) — سيفهرسه البوت فوراً.\n"
        "2️⃣ اكتب سؤالك نصياً — سيعيد البوت الإجابة الدقيقة مع اسم الملف ورقم الصفحة.\n\n"
        f"<b>الأوامر:</b>\n"
        "/stats — إحصائيات الخزينة\n"
        "/list — قائمة المستندات المفهرسة\n"
        "/delete &lt;اسم_الملف&gt; — حذف مستند\n"
        "/help — المساعدة\n\n"
        f"<i>{settings.ownership_block()}</i>",
        parse_mode=ParseMode.HTML,
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, ctx)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        n_chunks = total_chunks()
        docs = list_documents()
        n_files = len(docs)
        n_tokens = sum(d["tokens"] for d in docs)
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ في قراءة الإحصائيات: {e}")
        return

    msg = (
        "📊 <b>إحصائيات الخزينة</b>\n\n"
        f"📄 الملفات المفهرسة: <b>{n_files}</b>\n"
        f"🧩 الأجزاء الدلالية: <b>{n_chunks:,}</b>\n"
        f"🔤 التوكنات التقريبية: <b>{n_tokens:,}</b>\n\n"
        f"<i>{settings.ownership_block()}</i>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        docs = list_documents()
    except Exception as e:
        await update.message.reply_text(f"⚠️ خطأ: {e}")
        return
    if not docs:
        await update.message.reply_text("📭 لا توجد مستندات مفهرسة بعد. أرسل ملفاً للبدء.")
        return

    lines = ["📚 <b>المستندات المفهرسة:</b>\n"]
    for d in docs:
        lines.append(
            f"📄 <i>{d['source_file']}</i>\n"
            f"   • الأجزاء: {d['chunks']}  |  التوكنات: {d['tokens']:,}\n"
            f"   • الصفحات: {d['first_page']} → {d['last_page']}\n"
        )
    lines.append(f"\n<i>{settings.ownership_block()}</i>")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args:
        await update.message.reply_text("الاستخدام: /delete <اسم_الملف>")
        return
    name = " ".join(ctx.args).strip()
    try:
        deleted = delete_document(name)
        if deleted == 0:
            await update.message.reply_text(f"لم يتم العثور على مستند باسم '{name}'.")
        else:
            await update.message.reply_text(
                f"✅ تم حذف {deleted} جزءاً من '{name}'."
            )
    except Exception as e:
        await update.message.reply_text(f"⚠️ فشل الحذف: {e}")


# ---------------------------------------------------------------------------
# File handler — ingest uploaded documents
# ---------------------------------------------------------------------------
async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document or update.message.effective_attachment
    if not doc:
        await update.message.reply_text("⚠️ تعذّر قراءة الملف.")
        return

    file_name = doc.file_name or "uploaded_file"
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in SUPPORTED_EXTS:
        await update.message.reply_text(
            f"⚠️ الصيغة '{ext}' غير مدعومة.\nالصيغ المدعومة: {', '.join(SUPPORTED_EXTS)}"
        )
        return

    # Restrict to admin if configured
    if (settings.telegram_admin_chat_id
            and "ضع" not in settings.telegram_admin_chat_id
            and str(update.effective_chat.id) != settings.telegram_admin_chat_id):
        await update.message.reply_text("⛔ غير مصرح لك باستخدام هذا البوت.")
        return

    status = await update.message.reply_text(
        f"⬇️ جاري تنزيل '{file_name}'..."
    )
    try:
        tg_file = await doc.get_file()
        tmp_path = settings.data_dir / file_name
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        await tg_file.download_to_drive(str(tmp_path))
    except Exception as e:
        await status.edit_text(f"⚠️ فشل التنزيل: {e}")
        return

    await status.edit_text("📄 جارٍ استخراج النص وتقطيعه دلالياً...")
    chunks = ingest_file(tmp_path)
    if not chunks:
        await status.edit_text("⚠️ تعذّر استخراج أي نص من الملف.")
        return

    await status.edit_text(f"🧠 توليد المتجهات وتخزين {len(chunks)} جزءاً في Supabase...")
    try:
        stored = store_chunks(chunks)
    except Exception as e:
        await status.edit_text(f"⚠️ فشل التخزين: {e}")
        return

    summary = ingest_summary(chunks)
    await status.edit_text(
        f"✅ <b>تمت الفهرسة بنجاح</b>\n\n"
        f"📄 الملف: <i>{file_name}</i>\n"
        f"🧩 الأجزاء: <b>{stored}</b>\n"
        f"🔤 التوكنات: ~{summary['total_tokens']:,}\n\n"
        "يمكنك الآن طرح أسئلتك نصياً.\n"
        f"<i>{settings.ownership_block()}</i>",
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# Text handler — treat as a question
# ---------------------------------------------------------------------------
async def handle_question(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    question = update.message.text.strip()
    if not question or question.startswith("/"):
        return

    # Restrict
    if (settings.telegram_admin_chat_id
            and "ضع" not in settings.telegram_admin_chat_id
            and str(update.effective_chat.id) != settings.telegram_admin_chat_id):
        await update.message.reply_text("⛔ غير مصرح لك باستخدام هذا البوت.")
        return

    status = await update.message.reply_text("🔍 جارٍ البحث في خزينتك المعرفية...")
    try:
        result = ask(question)
    except Exception as e:
        await status.edit_text(f"⚠️ فشل الاستعلام: {e}")
        return

    await status.edit_text(
        format_answer_for_chat(result),
        parse_mode=ParseMode.HTML,
    )


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def main() -> None:
    print(banner())
    if not settings.has_telegram:
        logger.error("TELEGRAM_BOT_TOKEN is not configured. Edit .env first.")
        return

    # Ensure DB schema exists
    try:
        ensure_schema()
        logger.success("DB schema ensured.")
    except Exception as e:
        logger.warning(f"Could not ensure schema automatically: {e}")
        logger.warning("Run `python scripts/ingest_folder.py --init-db` manually.")

    app = Application.builder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("stats",  cmd_stats))
    app.add_handler(CommandHandler("list",   cmd_list))
    app.add_handler(CommandHandler("delete", cmd_delete))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    logger.success("Vault-ZeroBaran Telegram bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
