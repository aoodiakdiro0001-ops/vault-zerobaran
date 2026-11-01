# 🚀 Vault-ZeroBaran — Deployment Guide

## 1. إعداد Supabase (PostgreSQL + pgvector)

1. أنشئ حساباً على https://supabase.com (مجاني تماماً).
2. أنشئ **Project** جديداً وانتظر تجهيزه (≈2 دقيقة).
3. من **Database → Extensions** فعّل الإضافة `vector`.
4. من **SQL Editor** الصق محتوى `scripts/setup_db.sql` واضغط **Run**.
5. من **Project Settings → Database** انسخ:
   - **Connection string** (يبدأ بـ `postgresql://postgres:...`) — ضعه في `SUPABASE_DB_URL`.
6. من **Project Settings → API** انسخ:
   - **Project URL** → `SUPABASE_URL`
   - **anon public key** → `SUPABASE_KEY`

## 2. الحصول على مفاتيح Gemini API (مجاني)

1. اذهب إلى https://aistudio.google.com/app/apikey
2. اضغط **Create API key**.
3. اختر project أو أنشئ واحداً (مجاني).
4. انسخ المفتاح وضعه في `GEMINI_API_KEY`.

> حدود الطبقة المجانية: 1500 طلب/يوم، 5M توكن/شهر — كافية لمؤسسة صغيرة.

## 3. (اختياري) إنشاء بوت تليجرام

1. على تليجرام، ابحث عن **@BotFather**.
2. أرسل `/newbot` واتبع التعليمات لإنشاء بوت.
3. انسخ **HTTP API Token** وضعه في `TELEGRAM_BOT_TOKEN`.
4. للحصول على `chat_id` الخاص بك:
   - أرسل رسالة لبوتك الجديد.
   - افتح `https://api.telegram.org/bot<TOKEN>/getUpdates`.
   - ابحث عن `"chat":{"id": <هذا هو>` وضعه في `TELEGRAM_ADMIN_CHAT_ID`.

## 4. (اختياري) الحصول على مفاتيح Groq

1. https://console.groq.com → **API Keys** → **Create**.
2. انسخ المفتاح وضعه في `GROQ_API_KEY`.

> يُستخدم Groq كاحتياطي (fallback) عند فشل Gemini.

## 5. النشر عبر Docker (الأسهل)

```bash
# داخل مجلد المشروع
docker compose up -d --build

# متابعة السجل
docker compose logs -f
```

النتيجة:
- Streamlit UI على `http://localhost:8501`
- بوت تليجرام يعمل في الخلفية.

## 6. النشر على استضافة سحابية مجانية

### خيار: Render / Railway / Fly.io
1. اربط مستودع GitHub.
2. اختر **Docker** كنوع خدمة.
3. أضف جميع متغيرات `.env` في **Environment**.
4. المنفذ: `8501`.
5. بعد النشر، استخدم العنوان العام للوصول للوحة.

### خيار: GitHub Codespaces
1. افتح المشروع في Codespace.
2. في Terminal: `./start.sh`.
3. Codespace يعرض تلقائياً منفذ 8501.

## 7. تفعيل الجدولة عبر GitHub Actions

1. ادفع المشروع إلى GitHub.
2. في إعدادات المستودع → **Secrets and variables → Actions**.
3. أضف كل مفتاح من `.env` كـ Secret:
   `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`,
   `SUPABASE_DB_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`,
   `GROQ_API_KEY`.
4. سيعمل الـ workflow كل 6 ساعات تلقائياً، أو شغّله يدوياً من تبويب **Actions**.

## 8. مراقبة الأداء

- **Supabase Dashboard → Table Editor → `vault_chunks`**: مراجعة الأجزاء.
- **Supabase → SQL Editor**: استعلام مخصص مثل:
  ```sql
  SELECT source_file, COUNT(*), SUM(token_count)
  FROM vault_chunks GROUP BY source_file ORDER BY 2 DESC;
  ```
- **GitHub Actions tab**: سجل كل تشغيل مجدول.
- **Streamlit Dashboard**: إحصائيات لحظية + بطاقات التطابق.

## 9. النسخ الاحتياطي

```bash
# تصدير كل المتجهات (pg_dump)
pg_dump "$SUPABASE_DB_URL" -t vault_chunks > backup_$(date +%F).sql

# استعادة
psql "$SUPABASE_DB_URL" < backup_YYYY-MM-DD.sql
```
