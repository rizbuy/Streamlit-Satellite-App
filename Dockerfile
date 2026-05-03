# Gunakan versi Python 3.12.12 yang ringan
FROM python:3.12.12-slim

# Set folder kerja di dalam container
WORKDIR /app

# Install dependensi sistem operasi (penting untuk library geospasial seperti rasterio)
RUN apt-get update && apt-get install -y \
    g++ \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv (sangat cepat dan ringan)
RUN pip install --no-cache-dir uv

# Copy file requirements terlebih dahulu
COPY requirements.txt .

# Install library Python menggunakan uv
# Gunakan flag --system karena kita menginstal di global environment container, bukan di venv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy seluruh file proyek ke dalam container
COPY . .