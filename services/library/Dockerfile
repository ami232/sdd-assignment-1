# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PORT=8000 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# only what the app needs to run
COPY app.py config.py database.py ./
COPY library/ ./library/
COPY migrations/ ./migrations/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['PORT'] + '/health', timeout=4)"

CMD ["python", "app.py"]