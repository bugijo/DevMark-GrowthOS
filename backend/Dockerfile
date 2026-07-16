FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system growthos \
    && useradd --system --gid growthos --create-home growthos

COPY pyproject.toml ./
COPY growthos ./growthos
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --upgrade pip && pip install .

USER growthos

EXPOSE 8000

CMD ["uvicorn", "growthos.main:app", "--host", "0.0.0.0", "--port", "8000"]
