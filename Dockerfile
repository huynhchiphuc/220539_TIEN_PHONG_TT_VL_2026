FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY backend/api_base_public/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && python -c "import matplotlib; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"

COPY backend/api_base_public /app/backend/api_base_public

WORKDIR /app/backend/api_base_public

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]