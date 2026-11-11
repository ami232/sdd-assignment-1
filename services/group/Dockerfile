# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PORT=8000 \
    DATA_DIR=/data
WORKDIR /app

RUN useradd --create-home --uid 10001 appuser \
 && mkdir -p /data \
 && chown -R appuser:appuser /data /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# only what the app needs to run
COPY app.py config.py database.py ./
COPY group/ ./group/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/${PORT}' || exit 1

CMD ["python", "app.py"]