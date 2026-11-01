# ============================================================
#  Vault-ZeroBaran — Container Image
#  Builds a single image that can run either the Streamlit UI,
#  the Telegram bot, or the CLI ingest tool.
# ============================================================
FROM python:3.11-slim

# System deps required by PyMuPDF, psycopg2, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the project
COPY . .

# Default env (overridden at runtime)
ENV VAULT_DATA_DIR=/app/data/uploads \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create the data directory
RUN mkdir -p /app/data/uploads

# Expose Streamlit port
EXPOSE 8501

# Default command — overridden by docker-compose or `docker run`
CMD ["streamlit", "run", "ui/streamlit_app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--browser.gatherUsageStats=false"]
