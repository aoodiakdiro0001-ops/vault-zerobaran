# 🧠 Vault-ZeroBaran

> **العقل المعرفي الذاتي واللامركزي للشركات والمستندات**
> _محرك بحث واستخراج معرفي ذكي يعمل كـ Second Brain — بـ 100% موارد مجانية._

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-Proprietary-red">
  <img alt="Stack" src="https://img.shields.io/badge/stack-100%25%20free-success">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11+-blue">
  <img alt="UI" src="https://img.shields.io/badge/UI-Streamlit%20%2B%20Telegram-orange">
</p>

---

## 📖 ما هو Vault-ZeroBaran؟

هو **"محرك بحث واستخراج معرفي ذكي جداً يعمل كـ (Second Brain) للمؤسسات والأفراد"**.
يقوم بقراءة جميع ملفاتك ووثائقك (PDFs، وورد، إكسل، نصوص، أو أكواد برمجية)،
أرشفة بياناتها دلالياً (Semantic Indexing)، والإجابة الفورية على أي سؤال معقد
بناءً على مستنداتك الخاصة مع ذكر اسم الملف والصفحة الدقيقة كمصدر —
**دون دفع دولار واحد لأي أداة إدارة معرفة مدفوعة، وبموارد مجانية بالكامل.**

### لماذا تتمنى كل شركة وكل فرد الحصول عليه؟

| الميزة | الوصف |
|---|---|
| 💰 **توفير مال فلكي** | أدوات إدارة المعرفة المتقدمة تكلف الشركات ثروات سنوياً؛ هذا النظام يؤدي نفس الغرض باحترافية وبتكلفة صفر. |
| ⚡ **وصول لحظي للمعلومة (Zero Search Time)** | بدلاً من ساعات في البحث بين مئات الملفات، اسأل النظام فيجيبك بالإجابة الدقيقة خلال ثوانٍ. |
| 🔐 **السيادة والسرية المطلقة** | ملفاتك لا تُدرب عليها أي نماذج خارجية، بل تُحفظ في بيئة مشفرة خاصة بك. |

---

## 🛠️ الموارد المجانية المستخدمة (The Free Tech Stack)

| المكون | التقنية المجانية | الدور |
|---|---|---|
| محرك التشغيل المجدول | **GitHub Actions** | خادم مجاني لتنفيذ عمليات مسح الملفات الجديدة دورياً. |
| محرك استخراج النصوص | **Python + PyMuPDF / LangChain** | استخراج النصوص وتقطيعها إلى أجزاء دلالية متناسقة. |
| قاعدة بيانات التضمين | **Supabase (PostgreSQL + pgvector)** | تخزين المتجهات الرياضية للبحث السريع جداً. |
| محرك الذكاء الاستدلالي | **Google Gemini API / Groq API** | صياغة الإجابة الدقيقة بناءً على المصادر. |
| قناة الواجهة | **Telegram Bot + Streamlit Dashboard** | رفع الملفات وطرح الأسئلة واستلام الإجابات. |

---

## 🏗️ بنية المشروع

```
Vault-ZeroBaran/
├── config/
│   └── settings.py          # محمّل الإعدادات (Pydantic)
├── core/                    # العقل المعرفي
│   ├── ingestion.py         # استخراج النصوص + التقطيع الدلالي
│   ├── embeddings.py        # Gemini text-embedding-004
│   ├── vector_db.py         # Supabase pgvector (CRUD + cosine search)
│   ├── rag_engine.py        # محرك الاسترجاع + توليد الإجابة
│   └── utils.py             # مساعدات عامة
├── ui/
│   └── streamlit_app.py     # واجهة الويب التفاعلية
├── bot/
│   └── telegram_bot.py      # بوت تليجرام
├── scripts/
│   ├── ingest_folder.py     # CLI: فهرسة ملف/مجلد + init-db
│   ├── query_cli.py         # CLI: طرح سؤال
│   └── setup_db.sql         # SQL: مخطط Supabase + pgvector
├── .github/workflows/
│   └── scheduled_ingest.yml # GitHub Actions — كل 6 ساعات
├── data/uploads/            # ملفاتك المرفوعة
├── Dockerfile               # صورة حاوية موحدة
├── docker-compose.yml       # تشغيل UI + Bot معاً
├── start.sh                 # سكربت بدء سريع
├── requirements.txt
├── .env.example
├── LICENSE                  # حقوق ملكية محفوظة للمؤلف
└── README.md                # هذا الملف
```

---

## 🚀 التشغيل السريع (Quick Start)

### المتطلبات
- Python 3.11 أو أحدث.
- حساب GitHub (مجاني) لتفعيل الجدولة.
- حساب Supabase (مجاني) + تفعيل إضافة `pgvector`.
- مفتاح Gemini API (مجاني): https://aistudio.google.com/app/apikey
- (اختياري) بوت تليجرام عبر @BotFather.

### خطوات البدء

```bash
# 1) استنسخ المشروع
git clone <your-repo-url> Vault-ZeroBaran
cd Vault-ZeroBaran

# 2) شغّل سكربت البدء السريع (ينشئ venv، يثبت الحزم، ينسخ .env)
./start.sh

# 3) املأ مفاتيح الـ API في ملف .env
#    GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY, SUPABASE_DB_URL, TELEGRAM_BOT_TOKEN

# 4) أنشئ المخطط في Supabase
python scripts/ingest_folder.py --init-db
# أو افتح Supabase SQL Editor ونفّذ scripts/setup_db.sql

# 5) (اختياري) فهرس ملفاتك الأولى
python scripts/ingest_folder.py --folder ./data/uploads

# 6) شغّل الواجهة التي تريدها:
streamlit run ui/streamlit_app.py              # لوحة الويب
python -m bot.telegram_bot                     # بوت تليجرام
```

---

## ⚙️ سير العمل خطوة بخطوة (End-to-End Workflow)

```
┌─────────────────────────────────────────────────────────────┐
│  1) رفع مستند جديد (PDF / DOCX / XLSX / TXT)               │
│      عبر تليجرام أو واجهة Streamlit                         │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2) Python + PyMuPDF                                        │
│      استخراج النصوص وتقطيعها إلى فقرات دلالية (Chunks)      │
│      مع حفظ: اسم الملف + رقم الصفحة + معرف فريد             │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3) Google Gemini text-embedding-004                        │
│      تحويل الفقرات النصية إلى متجهات (768-dim)              │
│      ورصفها في Supabase pgvector (مع HNSW index)            │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4) طرح سؤال ──► embed_query() ──► cosine search (top-K)    │
│      ──► Gemini chat completion                             │
│      ──► "أجب عن السؤال بناءً على المصادر فقط وذكر المصدر"  │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  5) رد فوري منسق:                                           │
│      💡 الإجابة: بناءً على شروط العقد المبرم مع الشريك (س)،  │
│         فإن نسبة الأرباح المقررة هي 25%.                    │
│      📌 المصدر: Partnership_Contract_2025.pdf                │
│         — الصفحة 4 — البند 2 (تطابق 92%)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📡 الواجهات المدعومة

### 1) Streamlit Dashboard — `http://localhost:8501`
- إحصائيات لحظية (عدد الملفات، الأجزاء، التوكنات).
- رفع ملفات مباشرة مع شريط تقدم.
- حقل سؤال مع عرض المصادر وبطاقات تطابق.
- جدول المستندات المفهرسة + حذف بأزرار.

### 2) Telegram Bot
| الأمر | الوظيفة |
|---|---|
| `/start` | ترحيب + شرح الاستخدام |
| `/stats` | إحصائيات الخزينة |
| `/list` | قائمة المستندات المفهرسة |
| `/delete <name>` | حذف مستند |
| إرسال ملف | فهرسة فورية |
| إرسال نص | يُعامل كـ سؤال → رد فوري مع المصادر |

### 3) CLI
```bash
# فهرسة
python scripts/ingest_folder.py --file  /path/contract.pdf
python scripts/ingest_folder.py --folder /path/docs

# استعلام
python scripts/query_cli.py "ما هي سياسة الإرجاع؟"
python scripts/query_cli.py --raw --top-k 8 "البند المالي"   # JSON
```

---

## 🔐 الخصوصية والسيادة

- ملفاتك لا تغادر بيئتك إلا للمتجهات (Embeddings) التي تُحسب عبر Gemini API
  ثم تُخزَّن في **Supabase الخاص بك** (مشروعك أنت).
- لا يوجد أي نموذج يُدرَّب على بياناتك. كل عملية هي retrieval + generation آنية.
- يمكنك تفعيل Row Level Security في Supabase لحماية إضافية.

---

## 🐳 النشر عبر Docker

```bash
# تشغيل UI + Bot معاً
docker compose up -d --build

# أو تشغيل واجهة فقط
docker build -t vault-zerobaran .
docker run -p 8501:8501 --env-file .env -v $(pwd)/data:/app/data vault-zerobaran
```

---

## ⏰ الجدولة المجدولة (GitHub Actions)

الملف `.github/workflows/scheduled_ingest.yml` يعمل كل 6 ساعات (مجاناً):
1. يفحص مجلد `data/uploads` في المستودع.
2. يفهرس أي ملف جديد ويخزّنه في Supabase.
3. يطبع إحصائيات الخزينة.

> **لتفعيله:** أضف نفس مفاتيح الـ `.env` كـ Secrets في إعدادات المستودع على GitHub.

---

## 📊 الأداء والتكلفة

| البند | القيمة |
|---|---|
| تكلفة شهرية | **0 دولار** (كل الطبقات مجانية) |
| حجم الفهرسة المجاني | ~5M توكن/شهر (Gemini) |
| قاعدة البيانات المجانية | 500MB Supabase + pgvector |
| زمن الإجابة النموذجي | 2-4 ثوانٍ للسؤال الواحد |
| زمن الفهرسة النموذجي | ~3 ثوانٍ لكل صفحة PDF |
| دقة الاسترجاع | cosine similarity عبر HNSW index |

---

## 📜 الترخيص وحقوق الملكية

هذا المشروع **"Vault-ZeroBaran"** عمل فكري أصلي محمي بموجب ترخيص proprietary
يحفظ جميع الحقوق لمؤلفه. يُسمح بالاستخدام الشخصي والداخلي فقط؛ يُمنع إعادة
البيع أو الترخيص التجاري أو إزالة اسم المؤلف دون إذن كتابي صريح.

تفاصيل كاملة في ملف [LICENSE](LICENSE).

### الدعم وحقوق الملكية
- **المؤلف:** Baran Avisat
- **البريد:** Baranavisat@gmail.com
- **واتساب:** +90 531 326 37 22

---

## 🤝 المساهمة والدعم

للحصول على دعم تقني، طلب ميزات جديدة، أو طلب ترخيص تجاري، تواصل مع المؤلف
عبر القنوات المذكورة أعلاه.

---

<p align="center">
  <sub>Vault-ZeroBaran © 2026 — Self-Knowledge Brain • 100% Free Tech Stack</sub>
</p>

---

## 🧾 بيانات المالك وحقوق الملكية (Owner & Copyright)

| الحقل | القيمة |
|---|---|
| **المؤلف / Owner** | **Baran Avisat** |
| **البريد / Email** | [baranavisat@gmail.com](mailto:baranavisat@gmail.com) |
| **واتساب / WhatsApp** | +90 531 326 37 22 |
| **الحساب البنكي / IBAN** | `TR10 0001 0090 1008 4013 0050 01` |
| **GitHub** | [github.com/aoodiakdiro0001-ops](https://github.com/aoodiakdiro0001-ops) |
| **المتجر / Store** | [baranavi.gumroad.com](https://baranavi.gumroad.com/) |
| **الترخيص / License** | Proprietary — All Rights Reserved |

**© 2026 Baran Avisat — جميع الحقوق محفوظة / All Rights Reserved.**
