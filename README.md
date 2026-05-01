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
├─ frontend.py                  # Dashboard interaktif Streamlit
├─ main.py                      # FastAPI entry point (CORS, router)
└─ requirements.txt             # Dependensi proyek
```
---

## ⚡ Quick Start

```bash
git clone https://github.com/your-username/bands-analysis.git
cd bands-analysis

python -m venv .venv
source .venv/bin/activate  # atau Windows

pip install -r requirements.txt
```

Run:

```bash
uvicorn main:app --reload
streamlit run frontend.py
```

* Dashboard: http://localhost:8501
* API Docs: http://localhost:8000/docs

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

```bash
docker compose up --build
```

---

## 📦 Dependencies

```
fastapi
uvicorn
streamlit
rasterio
numpy
geopandas
scikit-image
```

---

