FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/data/modelos
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 app && mkdir -p /data/sqlite /data/chroma /data/modelos && chown -R app:app /data
COPY app ./app
USER app
