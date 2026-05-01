"""
🛰️ Satellite Band Analysis — Streamlit Frontend
Terhubung ke FastAPI backend untuk analisis NDVI, NDWI, dll.

Jalankan:
    streamlit run streamlit_app.py

Pastikan FastAPI backend sudah berjalan di http://localhost:8000
"""

import streamlit as st
import requests
import numpy as np
import json
import io
import tempfile
import os
from pathlib import Path

# ─── Opsional: import untuk visualisasi ──────────────────────────────────────
# Install: pip install folium streamlit-folium rasterio matplotlib
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import rasterio
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.patches import Patch
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

# ─── Konfigurasi ─────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ─── Definisi index (mirror dari backend registry) ───────────────────────────
INDEX_CONFIG = {
    "NDVI": {
        "full_name":    "Normalized Difference Vegetation Index",
        "required":     ["nir", "red"],
        "optional":     [],
        "description":  "Mengukur kerapatan dan kesehatan vegetasi. Ideal untuk deteksi mangrove, hutan, dan lahan pertanian.",
        "icon":         "🌿",
        "color_map":    "RdYlGn",
        "classes": {
            "water_barren":           {"range": (-1.0, 0.0),  "color": "#2166ac", "label": "Air / Lahan Gundul"},
            "sparse_vegetation":      {"range": (0.0,  0.2),  "color": "#d9ef8b", "label": "Vegetasi Jarang"},
            "moderate_vegetation":    {"range": (0.2,  0.4),  "color": "#66bd63", "label": "Vegetasi Sedang"},
            "dense_vegetation":       {"range": (0.4,  1.0),  "color": "#1a7837", "label": "Vegetasi Lebat"},
        },
    },
    "NDWI": {
        "full_name":    "Normalized Difference Water Index",
        "required":     ["green", "nir"],
        "optional":     [],
        "description":  "Mendeteksi badan air dan kandungan air dalam vegetasi.",
        "icon":         "💧",
        "color_map":    "RdBu",
        "classes": {
            "land":  {"range": (-1.0, 0.0), "color": "#d6604d", "label": "Daratan"},
            "water": {"range": (0.0,  1.0), "color": "#4393c3", "label": "Badan Air"},
        },
    },
    "MNDWI": {
        "full_name":    "Modified Normalized Difference Water Index",
        "required":     ["green", "swir"],
        "optional":     [],
        "description":  "Versi NDWI yang lebih akurat untuk area perkotaan dan pesisir.",
        "icon":         "🌊",
        "color_map":    "RdBu",
        "classes": {
            "land":  {"range": (-1.0, 0.3), "color": "#bf812d", "label": "Daratan"},
            "water": {"range": (0.3,  1.0), "color": "#35978f", "label": "Badan Air"},
        },
    },
    "NDBI": {
        "full_name":    "Normalized Difference Built-up Index",
        "required":     ["swir", "nir"],
        "optional":     [],
        "description":  "Mendeteksi area terbangun dan permukiman.",
        "icon":         "🏙️",
        "color_map":    "OrRd",
        "classes": {
            "non_urban": {"range": (-1.0, 0.0), "color": "#74c476", "label": "Non-Urban"},
            "urban":     {"range": (0.0,  1.0), "color": "#e6550d", "label": "Area Terbangun"},
        },
    },
    "EVI": {
        "full_name":    "Enhanced Vegetation Index",
        "required":     ["nir", "red", "blue"],
        "optional":     [],
        "description":  "Versi NDVI yang lebih robust, koreksi efek atmosfer. Cocok untuk hutan tropis lebat.",
        "icon":         "🌳",
        "color_map":    "RdYlGn",
        "classes": {
            "non_vegetation":    {"range": (-1.0, 0.1), "color": "#d73027", "label": "Non-Vegetasi"},
            "sparse_vegetation": {"range": (0.1,  0.3), "color": "#fee08b", "label": "Vegetasi Jarang"},
            "dense_vegetation":  {"range": (0.3,  1.0), "color": "#1a9850", "label": "Vegetasi Lebat"},
        },
    },
}

BAND_LABELS = {
    "nir":   ("NIR (Near-Infrared)",  "Band inframerah dekat — paling sensitif terhadap vegetasi"),
    "red":   ("Red (Merah)",          "Band merah — diserap klorofil"),
    "green": ("Green (Hijau)",        "Band hijau — dipantulkan vegetasi sehat"),
    "blue":  ("Blue (Biru)",          "Band biru — sensitif terhadap kedalaman air"),
    "swir":  ("SWIR (Short-Wave IR)", "Band inframerah gelombang pendek — deteksi kelembaban tanah"),
}

THRESHOLD_INFO = {
    "default":  "Gunakan threshold bawaan berdasarkan literatur ilmiah",
    "otsu":     "Threshold otomatis — optimal untuk data bimodal (vegetasi vs non-vegetasi)",
    "quantile": "Threshold di median distribusi data — robust terhadap outlier",
    "manual":   "Tentukan sendiri nilai threshold (untuk peneliti berpengalaman)",
}


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="SatAnalyze — Satellite Band Analyzer",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Font & base */
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* Header */
    .main-header {
        background: linear-gradient(135deg, #0a1628 0%, #0d2137 50%, #0a2820 100%);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #1a3a4a;
        position: relative;
        overflow: hidden;
    }
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(0,200,150,0.06) 0%, transparent 70%);
        pointer-events: none;
    }
    .main-header h1 {
        font-family: 'Space Mono', monospace;
        color: #e8f5e9;
        font-size: 1.8rem;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #78a89a;
        margin: 0.4rem 0 0;
        font-size: 0.95rem;
        font-weight: 300;
    }
    .sat-badge {
        display: inline-block;
        background: rgba(0,200,120,0.12);
        border: 1px solid rgba(0,200,120,0.25);
        color: #00c878;
        font-family: 'Space Mono', monospace;
        font-size: 0.7rem;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        letter-spacing: 1px;
        margin-bottom: 0.7rem;
    }

    /* Index cards */
    .index-card {
        background: #0d1f2d;
        border: 1px solid #1e3a4a;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .index-card:hover { border-color: #00c878; }
    .index-card.selected { border-color: #00c878; background: #0a2a1f; }

    /* Step labels */
    .step-label {
        font-family: 'Space Mono', monospace;
        font-size: 0.68rem;
        color: #00c878;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
    }

    /* Stat card */
    .stat-card {
        background: #0d1f2d;
        border: 1px solid #1e3a4a;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .stat-value {
        font-family: 'Space Mono', monospace;
        font-size: 1.6rem;
        color: #00c878;
        font-weight: 700;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #78a89a;
        margin-top: 0.2rem;
    }

    /* Class bar */
    .class-row {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 0.7rem;
    }
    .class-dot {
        width: 12px; height: 12px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .class-name { font-size: 0.88rem; color: #c9d8d0; flex: 1; }
    .class-pct {
        font-family: 'Space Mono', monospace;
        font-size: 0.88rem;
        color: #00c878;
        font-weight: 700;
        min-width: 50px;
        text-align: right;
    }
    .class-ha { font-size: 0.78rem; color: #78a89a; min-width: 80px; text-align: right; }

    /* Upload zone */
    .upload-hint {
        background: #0a1628;
        border: 1px dashed #2a4a5a;
        border-radius: 10px;
        padding: 0.9rem;
        margin-bottom: 0.8rem;
        font-size: 0.85rem;
        color: #78a89a;
        line-height: 1.5;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #070f1a;
        border-right: 1px solid #1a2d3d;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00a86b, #00c878);
        color: #001a0f;
        font-family: 'Space Mono', monospace;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 1px;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(0,200,120,0.3);
    }

    /* Alerts */
    .info-box {
        background: rgba(0,136,200,0.08);
        border-left: 3px solid #0088c8;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        font-size: 0.88rem;
        color: #90c8e8;
        margin: 0.5rem 0;
    }
    .success-box {
        background: rgba(0,200,120,0.08);
        border-left: 3px solid #00c878;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        font-size: 0.88rem;
        color: #78e8b8;
        margin: 0.5rem 0;
    }
    .warning-box {
        background: rgba(255,180,0,0.08);
        border-left: 3px solid #ffb400;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        font-size: 0.88rem;
        color: #f0c848;
        margin: 0.5rem 0;
    }

    /* Divider */
    hr { border-color: #1e3a4a !important; }
    
    /* Hide streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def check_api_health() -> bool:
    """Cek apakah FastAPI backend aktif."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def call_analysis_api(
    index_name: str,
    band_files: dict,
    threshold_method: str,
    manual_threshold: float | None
) -> dict:
    """
    Kirim request multipart/form-data ke FastAPI endpoint.
    Return: response JSON atau raise exception.
    """
    files = {}
    for band_name, file_obj in band_files.items():
        if file_obj is not None:
            files[band_name] = (
                file_obj.name,
                file_obj.getvalue(),
                "image/tiff"
            )

    data = {
        "index_name": index_name,
        "threshold_method": threshold_method,
    }
    if manual_threshold is not None:
        data["manual_threshold"] = str(manual_threshold)

    response = requests.post(
        f"{API_BASE}/analyze/upload-bands",
        files=files,
        data=data,
        timeout=3600
    )

    if response.status_code != 200:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise Exception(f"API Error {response.status_code}: {detail}")

    return response.json()


def render_index_map_preview(index_array: np.ndarray, colormap: str, title: str):
    """
    Render index array sebagai gambar berwarna dengan matplotlib.
    Return: matplotlib figure.
    """
    fig, ax = plt.subplots(figsize=(7, 5), facecolor="#0d1f2d")
    ax.set_facecolor("#0d1f2d")

    im = ax.imshow(index_array, cmap=colormap, vmin=-1, vmax=1)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.ax.yaxis.set_tick_params(color="#78a89a")
    cbar.outline.set_edgecolor("#1e3a4a")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#78a89a", fontsize=8)

    ax.set_title(title, color="#e8f5e9", fontsize=11, pad=10,
                 fontfamily="monospace")
    ax.tick_params(colors="#78a89a", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1e3a4a")

    plt.tight_layout()
    return fig


def render_area_chart(classes_data: list, index_config: dict):
    """
    Horizontal bar chart luasan per kelas.
    """
    labels = []
    values = []
    colors = []

    for cls in classes_data:
        label_key = cls["label"]
        cfg = index_config["classes"].get(label_key, {})
        labels.append(cfg.get("label", label_key))
        values.append(cls["percentage"])
        colors.append(cfg.get("color", "#78a89a"))

    fig, ax = plt.subplots(figsize=(6, max(2, len(labels) * 0.8)),
                           facecolor="#0d1f2d")
    ax.set_facecolor("#0d1f2d")

    bars = ax.barh(labels, values, color=colors, height=0.5, edgecolor="#1e3a4a")

    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}%",
            va="center", ha="left",
            color="#00c878", fontsize=9, fontfamily="monospace"
        )

    ax.set_xlabel("Coverage (%)", color="#78a89a", fontsize=9)
    ax.set_xlim(0, max(values) * 1.2 if values else 100)
    ax.tick_params(colors="#78a89a", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for spine in ["bottom", "left"]:
        ax.spines[spine].set_edgecolor("#1e3a4a")

    plt.tight_layout()
    return fig


def simulate_analysis(index_name: str, threshold_method: str,
                      manual_threshold: float | None) -> dict:
    """
    Simulasi response API untuk demo tanpa backend aktif.
    Digunakan saat API tidak tersedia.
    """
    np.random.seed(42)
    idx_cfg = INDEX_CONFIG[index_name]

    classes_out = []
    remaining = 100.0
    class_items = list(idx_cfg["classes"].items())

    for i, (key, cfg) in enumerate(class_items):
        if i == len(class_items) - 1:
            pct = remaining
        else:
            pct = round(np.random.uniform(5, remaining - 5 * (len(class_items) - i - 1)), 2)
            remaining -= pct

        area_ha = round(pct / 100 * 7854.32, 2)
        classes_out.append({
            "label": key,
            "range": list(cfg["range"]),
            "area_ha": area_ha,
            "area_km2": round(area_ha / 100, 4),
            "percentage": pct,
            "pixel_count": int(pct / 100 * 785432),
        })

    dominant = max(classes_out, key=lambda x: x["percentage"])["label"]
    threshold_val = manual_threshold if threshold_method == "manual" else round(
        np.random.uniform(0.15, 0.35), 4
    )

    return {
        "job_id": "demo_" + index_name.lower(),
        "index": index_name,
        "description": idx_cfg["full_name"],
        "threshold": {
            "method": threshold_method,
            "value": threshold_val if threshold_method != "default" else None,
            "description": THRESHOLD_INFO[threshold_method],
        },
        "spatial_info": {
            "resolution_m": 10.0,
            "total_area_ha": 7854.32,
            "total_pixels": 785432,
        },
        "analysis": {
            "dominant_class": dominant,
            "classes": classes_out,
        },
        "downloads": {
            "geotiff": f"/analyze/download/demo/{index_name}/tif",
            "geojson": f"/analyze/download/demo/{index_name}/geojson",
        },
        "_demo_mode": True,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 0.5rem;'>
        <div style='font-size:2rem;'>🛰️</div>
        <div style='font-family: Space Mono, monospace; color: #00c878;
                    font-size: 0.9rem; letter-spacing: 2px;'>SAT·ANALYZE</div>
        <div style='color: #78a89a; font-size: 0.75rem; margin-top: 0.3rem;'>
            v1.0 · Satellite Band Analyzer
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # API status
    api_ok = check_api_health()
    if api_ok:
        st.markdown('<div class="success-box">✅ Backend API aktif</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">⚠️ Backend offline — mode demo aktif</div>',
                    unsafe_allow_html=True)

    st.divider()

    # ── STEP 1: Pilih Index ──────────────────────────────────────────────────
    st.markdown('<div class="step-label">STEP 01 — PILIH INDEX</div>',
                unsafe_allow_html=True)

    selected_index = st.selectbox(
        "Spectral Index",
        options=list(INDEX_CONFIG.keys()),
        format_func=lambda x: f"{INDEX_CONFIG[x]['icon']}  {x} — {INDEX_CONFIG[x]['full_name']}",
        label_visibility="collapsed"
    )

    idx = INDEX_CONFIG[selected_index]
    st.markdown(f'<div class="info-box">{idx["icon"]} {idx["description"]}</div>',
                unsafe_allow_html=True)

    required_bands = idx["required"]
    st.markdown(
        f"**Band yang dibutuhkan:** `{'` + `'.join(required_bands)}`",
        help="Upload file GeoTIFF untuk setiap band di bawah"
    )

    st.divider()

    # ── STEP 2: Threshold ────────────────────────────────────────────────────
    st.markdown('<div class="step-label">STEP 02 — THRESHOLD</div>',
                unsafe_allow_html=True)

    threshold_method = st.radio(
        "Metode threshold",
        options=["default", "otsu", "quantile", "manual"],
        format_func=lambda x: {
            "default":  "📚 Default (literatur)",
            "otsu":     "⚡ Otsu (otomatis)",
            "quantile": "📊 Quantile (median)",
            "manual":   "✏️ Manual",
        }[x],
        label_visibility="collapsed"
    )

    st.caption(THRESHOLD_INFO[threshold_method])

    manual_threshold = None
    if threshold_method == "manual":
        manual_threshold = st.slider(
            "Nilai threshold", min_value=-1.0, max_value=1.0,
            value=0.3, step=0.01,
            help="Pixel di atas nilai ini = kelas atas"
        )
        st.markdown(
            f'<div class="info-box">Threshold: <strong style="color:#00c878">{manual_threshold:.2f}</strong></div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── Info ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style='font-size:0.78rem; color:#4a7a6a; line-height:1.7;'>
        <strong style='color:#78a89a;'>Format yang diterima</strong><br>
        GeoTIFF (.tif / .tiff)<br><br>
        <strong style='color:#78a89a;'>Sensor yang kompatibel</strong><br>
        Sentinel-2 · Landsat 8/9 · MODIS · Drone imagery<br><br>
        <strong style='color:#78a89a;'>Persyaratan</strong><br>
        Semua band harus memiliki CRS dan dimensi yang sama
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

# Header
st.markdown(f"""
<div class="main-header">
    <div class="sat-badge">🛰️ SATELLITE ANALYSIS PLATFORM</div>
    <h1>Band → Index → Luasan</h1>
    <p>Upload band satelit · Hitung spectral index · Analisis luasan per kelas tutupan lahan</p>
</div>
""", unsafe_allow_html=True)


# ── STEP 3: Upload Band Files ─────────────────────────────────────────────────
st.markdown('<div class="step-label">STEP 03 — UPLOAD BAND FILES</div>',
            unsafe_allow_html=True)

idx = INDEX_CONFIG[selected_index]
required_bands = idx["required"]

# Hint box
bands_str = " + ".join([f"`{b.upper()}.tif`" for b in required_bands])
st.markdown(
    f'<div class="upload-hint">'
    f'<strong style="color:#c9d8d0;">{selected_index}</strong> membutuhkan '
    f'{len(required_bands)} band: {bands_str}<br>'
    f'<span style="font-size:0.8rem;">Pastikan semua band sudah dalam CRS dan resolusi yang sama '
    f'sebelum diupload.</span>'
    f'</div>',
    unsafe_allow_html=True
)

# Buat kolom dinamis sesuai jumlah band
n_bands = len(required_bands)
cols = st.columns(n_bands)

uploaded_files = {}
all_uploaded = True

for i, band_name in enumerate(required_bands):
    with cols[i]:
        label, hint = BAND_LABELS.get(band_name, (band_name.upper(), ""))
        st.markdown(f"**{label}**")
        st.caption(hint)

        file = st.file_uploader(
            f"Upload {band_name.upper()} band",
            type=["tif", "tiff"],
            key=f"upload_{selected_index}_{band_name}",
            label_visibility="collapsed"
        )

        if file:
            st.success(f"✓ {file.name}")
            # Preview sederhana: tampilkan ukuran file
            size_kb = len(file.getvalue()) / 1024
            st.caption(f"📦 {size_kb:.1f} KB")
            uploaded_files[band_name] = file
        else:
            st.markdown(
                f'<div style="color:#78a89a; font-size:0.8rem; '
                f'padding:0.5rem; border:1px dashed #2a4a5a; '
                f'border-radius:8px; text-align:center;">'
                f'Drop {band_name.upper()}.tif di sini</div>',
                unsafe_allow_html=True
            )
            all_uploaded = False

st.divider()


# ── STEP 4: Analisis ──────────────────────────────────────────────────────────
st.markdown('<div class="step-label">STEP 04 — JALANKAN ANALISIS</div>',
            unsafe_allow_html=True)

col_btn, col_info = st.columns([2, 5])

with col_btn:
    # Mode: real API atau demo
    if all_uploaded:
        btn_label = f"🔍 Analisis {selected_index}"
        btn_help = "Kirim band ke API dan hitung index"
    else:
        btn_label = "🎯 Coba Demo Mode"
        btn_help = f"Jalankan simulasi {selected_index} tanpa upload file"

    run_btn = st.button(btn_label, use_container_width=True, help=btn_help)

with col_info:
    if not all_uploaded:
        st.markdown(
            '<div class="warning-box">Upload semua band untuk analisis nyata, '
            'atau klik Demo Mode untuk lihat contoh output.</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="success-box">Semua {n_bands} band siap dianalisis.</div>',
            unsafe_allow_html=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HASIL ANALISIS
# ═══════════════════════════════════════════════════════════════════════════════

if run_btn:
    with st.spinner(f"⚙️ Menghitung {selected_index}..."):
        try:
            if all_uploaded and api_ok:
                # ── Real API call ────────────────────────────────────────────
                result = call_analysis_api(
                    index_name=selected_index,
                    band_files=uploaded_files,
                    threshold_method=threshold_method,
                    manual_threshold=manual_threshold
                )
                demo_mode = False
            else:
                # ── Demo / simulasi ──────────────────────────────────────────
                import time; time.sleep(1.5)   # simulasi loading
                result = simulate_analysis(
                    selected_index, threshold_method, manual_threshold
                )
                demo_mode = True

            st.session_state["last_result"] = result
            st.session_state["last_index"] = selected_index

        except Exception as e:
            st.error(f"❌ Analisis gagal: {str(e)}")
            result = None

    if result:
        # Demo badge
        if demo_mode:
            st.markdown(
                '<div class="warning-box">🎯 <strong>DEMO MODE</strong> — '
                'Data simulasi. Upload band GeoTIFF asli untuk hasil nyata.</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="success-box">✅ Analisis selesai · Job ID: '
                f'<code>{result.get("job_id")}</code></div>',
                unsafe_allow_html=True
            )

        st.divider()

        # ── Layout Hasil ──────────────────────────────────────────────────────
        col_left, col_right = st.columns([1.2, 1], gap="large")

        with col_left:
            # ── Statistik Spasial ─────────────────────────────────────────────
            st.markdown("#### 📐 Informasi Spasial")
            spatial = result["spatial_info"]
            threshold_info = result["threshold"]

            m1, m2, m3 = st.columns(3)
            metrics = [
                (m1, f"{spatial['total_area_ha']:,.1f}", "Total Area (ha)"),
                (m2, f"{spatial['resolution_m']:.0f} m", "Resolusi Pixel"),
                (m3, f"{spatial['total_pixels']:,}", "Total Pixel Valid"),
            ]
            for col, val, lbl in metrics:
                with col:
                    st.markdown(
                        f'<div class="stat-card">'
                        f'<div class="stat-value">{val}</div>'
                        f'<div class="stat-label">{lbl}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            st.markdown("#### 🎯 Threshold yang Digunakan")
            t = result["threshold"]
            t_val_str = f"`{t['value']:.4f}`" if t["value"] is not None else "`default`"
            st.markdown(
                f'<div class="info-box">'
                f'<strong>Metode:</strong> {t["method"].upper()} &nbsp;|&nbsp; '
                f'<strong>Nilai:</strong> {t_val_str}<br>'
                f'<span style="font-size:0.82rem;">{t["description"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            # ── Distribusi Kelas ──────────────────────────────────────────────
            st.markdown("#### 🗂️ Distribusi Kelas Tutupan Lahan")
            classes = result["analysis"]["classes"]
            dominant = result["analysis"]["dominant_class"]

            for cls in sorted(classes, key=lambda x: x["percentage"], reverse=True):
                key = cls["label"]
                cfg = INDEX_CONFIG[selected_index]["classes"].get(key, {})
                color = cfg.get("color", "#78a89a")
                label = cfg.get("label", key)
                is_dominant = key == dominant

                st.markdown(
                    f'<div class="class-row">'
                    f'<div class="class-dot" style="background:{color};'
                    f'{"box-shadow:0 0 6px " + color if is_dominant else ""}"></div>'
                    f'<div class="class-name">{label}'
                    f'{"  <span style=\'font-size:0.7rem;color:#00c878;\'>▲ DOMINAN</span>" if is_dominant else ""}'
                    f'</div>'
                    f'<div class="class-ha">{cls["area_ha"]:,.1f} ha</div>'
                    f'<div class="class-pct">{cls["percentage"]:.1f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # Progress bar
                st.progress(cls["percentage"] / 100)

        with col_right:
            # ── Visualisasi ───────────────────────────────────────────────────
            st.markdown("#### 📊 Grafik Distribusi")

            if RASTERIO_AVAILABLE:
                fig = render_area_chart(classes, INDEX_CONFIG[selected_index])
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            else:
                # Fallback: Streamlit native bar chart
                import pandas as pd
                df = pd.DataFrame([{
                    "Kelas": INDEX_CONFIG[selected_index]["classes"].get(
                        c["label"], {}).get("label", c["label"]),
                    "Coverage (%)": c["percentage"],
                    "Luas (ha)": c["area_ha"],
                } for c in classes])
                st.bar_chart(df.set_index("Kelas")["Coverage (%)"])

            # ── Detail Tabel ──────────────────────────────────────────────────
            st.markdown("#### 📋 Tabel Detail")

            import pandas as pd
            df = pd.DataFrame([{
                "Kelas": INDEX_CONFIG[selected_index]["classes"].get(
                    c["label"], {}).get("label", c["label"]),
                "Range":       f"{c['range'][0]:.1f} ~ {c['range'][1]:.1f}",
                "Luas (ha)":  f"{c['area_ha']:,.2f}",
                "Luas (km²)": f"{c['area_km2']:.4f}",
                "Coverage":   f"{c['percentage']:.2f}%",
                "Pixel":      f"{c['pixel_count']:,}",
            } for c in sorted(classes, key=lambda x: x["percentage"], reverse=True)])

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )

        # ── Download Section ──────────────────────────────────────────────────
        st.divider()
        st.markdown("#### 💾 Download Hasil")

        dl_col1, dl_col2, dl_col3 = st.columns(3)

        # JSON Result
        with dl_col1:
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"{selected_index}_result_{result.get('job_id','demo')}.json",
                mime="application/json",
                use_container_width=True,
                help="Download hasil analisis lengkap dalam format JSON"
            )

        # CSV summary
        with dl_col2:
            csv_rows = []
            for c in classes:
                cfg = INDEX_CONFIG[selected_index]["classes"].get(c["label"], {})
                csv_rows.append({
                    "index": selected_index,
                    "class_key": c["label"],
                    "class_label": cfg.get("label", c["label"]),
                    "range_min": c["range"][0],
                    "range_max": c["range"][1],
                    "area_ha": c["area_ha"],
                    "area_km2": c["area_km2"],
                    "percentage": c["percentage"],
                    "pixel_count": c["pixel_count"],
                })
            import pandas as pd
            csv_str = pd.DataFrame(csv_rows).to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv_str,
                file_name=f"{selected_index}_area_{result.get('job_id','demo')}.csv",
                mime="text/csv",
                use_container_width=True,
                help="Download ringkasan luasan dalam format CSV"
            )

        # GeoTIFF / GeoJSON link (hanya jika dari API nyata)
        with dl_col3:
            if not demo_mode:
                tif_url = f"{API_BASE}{result['downloads']['geotiff']}"
                st.link_button(
                    "🗺️ Download GeoTIFF",
                    url=tif_url,
                    use_container_width=True,
                )
            else:
                st.button(
                    "🗺️ Download GeoTIFF",
                    disabled=True,
                    use_container_width=True,
                    help="Tersedia setelah upload band GeoTIFF nyata"
                )

        # ── Interpretasi Otomatis ─────────────────────────────────────────────
        st.divider()
        st.markdown("#### 🔬 Interpretasi Otomatis")

        dominant_cfg = INDEX_CONFIG[selected_index]["classes"].get(dominant, {})
        dominant_label = dominant_cfg.get("label", dominant)
        dominant_pct = next(
            (c["percentage"] for c in classes if c["label"] == dominant), 0
        )
        dominant_ha = next(
            (c["area_ha"] for c in classes if c["label"] == dominant), 0
        )

        interp_map = {
            "NDVI": {
                "dense_vegetation": f"Area ini memiliki **tutupan vegetasi lebat yang dominan** ({dominant_pct:.1f}% / {dominant_ha:,.1f} ha). Kondisi ini menunjukkan ekosistem yang sehat dan produktif.",
                "water_barren": f"Sebagian besar area ({dominant_pct:.1f}%) teridentifikasi sebagai **air atau lahan gundul**. Perlu investigasi lebih lanjut untuk membedakan badan air dari lahan terdegradasi.",
                "sparse_vegetation": f"Vegetasi jarang mendominasi ({dominant_pct:.1f}%). Indikasi kemungkinan **degradasi lahan atau masa awal revegetasi**.",
                "moderate_vegetation": f"Vegetasi sedang mendominasi ({dominant_pct:.1f}%). Area dalam kondisi **cukup sehat** namun berpotensi ditingkatkan.",
            },
            "NDWI": {
                "water": f"**{dominant_pct:.1f}% area** teridentifikasi sebagai badan air ({dominant_ha:,.1f} ha). Area ini memiliki kandungan air yang signifikan.",
                "land":  f"**{dominant_pct:.1f}% area** adalah daratan. Kandungan air dalam vegetasi relatif rendah.",
            },
        }

        default_interp = (
            f"Kelas dominan adalah **{dominant_label}** dengan coverage "
            f"**{dominant_pct:.1f}%** ({dominant_ha:,.1f} ha dari total "
            f"{spatial['total_area_ha']:,.1f} ha)."
        )

        interpretation = (
            interp_map
            .get(selected_index, {})
            .get(dominant, default_interp)
        )

        st.info(interpretation)

        # Rekomendasi
        if selected_index == "NDVI" and dominant == "dense_vegetation" and dominant_pct > 50:
            st.success("🌿 **Rekomendasi:** Pertimbangkan area ini sebagai zona konservasi prioritas.")
        elif selected_index == "NDVI" and dominant in ("water_barren", "sparse_vegetation") and dominant_pct > 40:
            st.warning("⚠️ **Rekomendasi:** Perlu program rehabilitasi atau revegetasi untuk area ini.")


# ═══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style='text-align:center; color:#4a7a6a; font-size:0.78rem; padding:0.5rem;'>
    🛰️ SatAnalyze · Satellite Band Analyzer &nbsp;|&nbsp;
    Built with FastAPI + Streamlit &nbsp;|&nbsp;
    Supports Sentinel-2 · Landsat · MODIS · UAV Imagery
</div>
""", unsafe_allow_html=True)