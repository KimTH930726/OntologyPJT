# ---------- stage 1: build admin SPA ----------
FROM node:22-alpine AS admin-build
WORKDIR /admin
COPY admin/package.json admin/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY admin/ ./
RUN npm run build

# ---------- stage 2: python app ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# admin SPA build output (vite outDir = ../app/static/admin) → /code/app/static/admin
COPY --from=admin-build /app/static/admin ./app/static/admin

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
