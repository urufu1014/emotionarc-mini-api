# ベースイメージ
FROM python:3.11-slim

# 依存インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体
COPY main.py .

# Cloud Run が読むポート
ENV PORT=8080

# 起動コマンド
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 main:app
