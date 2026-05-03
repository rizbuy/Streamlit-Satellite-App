# 🛰️ Satellite Analysis Streamlit App

**Upload band → Hitung spectral index → Analisis area tutupan lahan**

---

## 📌 Overview

REST API + dashboard interaktif untuk analisis citra satelit.
Mendukung berbagai sensor (Sentinel, Landsat, MODIS, UAV) untuk menghitung spectral index dan klasifikasi tutupan lahan secara otomatis.

**Output:** statistik area + GeoTIFF + GeoJSON

---

## ✨ Core Features

* Multi-index: NDVI, NDWI, MNDWI, NDBI, EVI
* Sensor-agnostic (Sentinel, Landsat, dll)
* Thresholding: default, Otsu, quantile, manual
* Statistik area (px, ha, km², %)
* Export: GeoTIFF & GeoJSON
* Dashboard interaktif (Streamlit)

---

## 🏗️ Architecture

```
Client (Streamlit / API)
        │
        ▼
   FastAPI Backend
        │
 ┌──────┴──────┐
 │ Index Calc  │
 │ Threshold   │
 │ Area Stats  │
 └─────────────┘
```
```
Bands Analysis
├─ app
│  ├─ main.py                  # FastAPI entry point (CORS, router)
│  ├─ api
│  │  ├─ v1
│  │  │  ├─ analyze.py          # Route handlers: /analyze/upload-bands, /health
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ core
│  │  ├─ index_registry.py      # IndexDefinition dataclass + INDEX_REGISTRY dict
│  │  └─ __init__.py
│  ├─ schemas
│  │  ├─ request.py             # Pydantic V2 models: IndexName, ThresholdMethod
│  │  └─ __init__.py
│  ├─ services
│  │  ├─ area_calculator.py     # Statistik area (px → ha → km²) + GeoJSON
│  │  ├─ threshold.py           # Strategi ambang batas: Otsu, quantile, manual
│  │  └─ __init__.py
│  └─ __init__.py
├─ web
│  └─ frontend.py               # Dashboard interaktif Streamlit
├─ pyproject.toml               # Definisi dependensi proyek
└─ uv.lock                      # Lockfile dependensi uv
```
---

## ⚡ Quick Start

Clone repository:

```bash
git clone https://github.com/your-username/bands-analysis.git
cd bands-analysis
```

### Opsi 1 — Menjalankan dengan Docker

Jika repository sudah memiliki file Docker / Docker Compose, cara paling praktis untuk menjalankan project adalah:

```bash
docker compose up --build
```

Setelah container berjalan, akses aplikasi melalui:

* Backend API: http://localhost:8000
* API Docs: http://localhost:8000/docs
* Dashboard Frontend: http://localhost:8501

Untuk menghentikan container:

```bash
docker compose down
```

Gunakan opsi manual di bawah jika tidak memakai Docker atau ingin menjalankan backend dan frontend secara terpisah saat development.

### Opsi 2 — Menjalankan Manual Tanpa Docker

Sinkronkan dependency dengan lockfile:

```bash
uv sync
```

Jalankan backend FastAPI:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Backend akan tersedia di:

* API: http://localhost:8000
* API Docs: http://localhost:8000/docs

Buka terminal kedua, lalu jalankan frontend Streamlit:

```bash
uv run streamlit run web/frontend.py
```

Frontend akan tersedia di:

* Dashboard: http://localhost:8501

Pastikan backend tetap berjalan saat memakai frontend, karena dashboard akan mengirim request ke API di `http://localhost:8000`.

Jika ingin menambahkan library baru, gunakan:

```bash
uv add nama-package
```

Setelah menarik perubahan dari GitHub, cukup jalankan ulang:

```bash
uv sync
```

---

## 🌿 Supported Indices

| Index | Bands          |
| ----- | -------------- |
| NDVI  | NIR, Red       |
| NDWI  | Green, NIR     |
| MNDWI | Green, SWIR    |
| NDBI  | SWIR, NIR      |
| EVI   | NIR, Red, Blue |

---

## 📡 API

### `POST /analyze/upload-bands`

Upload band & hitung index

```bash
curl -X POST http://localhost:8000/analyze/upload-bands \
  -F "index_name=NDVI" \
  -F "nir=@nir.tif" \
  -F "red=@red.tif"
```

---

### `GET /health`

```json
{"status": "ok"}
```

---

## 🗺️ Threshold Methods

* `default` → nilai literatur
* `otsu` → otomatis
* `quantile` → robust
* `manual` → custom

---

## 🖥️ Dashboard

Fitur utama:

* Upload band
* Pilih index
* Visualisasi hasil
* Download output

---

## 🐳 Docker

Project ini dapat dijalankan menggunakan Docker Compose:

```bash
docker compose up --build
```

Endpoint yang digunakan:

* Backend API: http://localhost:8000
* API Docs: http://localhost:8000/docs
* Dashboard Frontend: http://localhost:8501

---

## 📦 Dependencies

Dependensi dikelola lewat `pyproject.toml` dan dikunci di `uv.lock`.
Gunakan `uv sync` untuk menyiapkan environment yang konsisten.

---


```
Bands Analysis
├─ .dockerignore
├─ .python-version
├─ app
│  ├─ main.py
│  ├─ api
│  │  ├─ v1
│  │  │  ├─ analyze.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ core
│  │  ├─ index_registry.py
│  │  └─ __init__.py
│  ├─ schemas
│  │  ├─ request.py
│  │  └─ __init__.py
│  ├─ services
│  │  ├─ area_calculator.py
│  │  ├─ threshold.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ docker-compose.yml
├─ Dockerfile
├─ pyproject.toml
├─ README.md
├─ docs
│  └─ Ringkasan.md
├─ tests
│  └─ test_analyze.py
├─ web
│  └─ frontend.py
└─ uv.lock

```
