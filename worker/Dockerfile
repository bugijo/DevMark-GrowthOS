FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN groupadd --system growthos \
    && useradd --system --gid growthos --create-home growthos

COPY backend /workspace/backend
COPY worker /workspace/worker
COPY shared /workspace/shared

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e /workspace/backend -e /workspace/worker

USER growthos

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
  CMD ["python", "-m", "growthos_worker.healthcheck"]

CMD ["python", "-m", "growthos_worker"]
