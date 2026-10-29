FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY api /app/
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY packs /packs
ENV EMPU_PACKS_DIR=/packs PYTHONPATH=/app
CMD ["uv", "run", "uvicorn", "empu.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]