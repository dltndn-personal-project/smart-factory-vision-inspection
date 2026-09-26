FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src \
    IMAGE_ROOT=/data HEALTH_FILE=/tmp/vision-inspection.connected
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
HEALTHCHECK --interval=3s --timeout=2s --start-period=10s --retries=3 \
  CMD test -f "$HEALTH_FILE"
ENTRYPOINT ["python", "-m", "vision_inspection"]
