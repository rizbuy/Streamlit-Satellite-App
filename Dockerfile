# Gunakan versi Python 3.12.12 yang ringan
FROM python:3.12.12-slim

# Install uv dari official image agar tidak perlu pip install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Set folder kerja di dalam container
WORKDIR /app

# Install dependensi sistem operasi (penting untuk library geospasial seperti rasterio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy file lock lebih dulu agar layer dependensi bisa di-cache.
COPY pyproject.toml uv.lock ./

# Install library Python dari uv.lock.
RUN uv sync --frozen --no-cache --no-install-project

# Copy seluruh file proyek ke dalam container
COPY . .

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
