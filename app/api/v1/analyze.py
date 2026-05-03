# app/api/v1/analyze.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Annotated
import rasterio
import numpy as np
import tempfile, os, uuid
from pathlib import Path
from app.core.index_registry import INDEX_REGISTRY
from app.services.threshold import compute_threshold
from app.services.area_calculator import calculate_area_by_class
from app.schemas.request import IndexName, ThresholdMethod

router = APIRouter(prefix="/analyze", tags=["Band Analysis"])
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_band(file: UploadFile) -> tuple[np.ndarray, dict]:
    """
    Load single band dari UploadFile → numpy array + metadata.
    Simpan sementara ke tempfile lalu baca dengan rasterio.
    """
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    with rasterio.open(tmp_path) as src:
        data = src.read(1).astype(np.float32)   # ambil band pertama
        meta = {
            "crs":       src.crs,
            "transform": src.transform,
            "resolution": src.res,               # (pixel_width, pixel_height) in CRS units
            "bounds":    tuple(src.bounds),
            "shape":     (src.height, src.width),
            "nodata":    src.nodata,
        }

    os.unlink(tmp_path)   # hapus tempfile

    # Replace nodata dengan NaN
    if meta["nodata"] is not None:
        data = np.where(data == meta["nodata"], np.nan, data)

    return data, meta


def validate_bands_compatible(metas: list[dict]) -> float:
    """
    Pastikan semua band yang diupload:
    - Shape sama (resolusi dan dimensi harus identik)
    - CRS sama
    Return: resolusi dalam meter
    """
    shapes = [m["shape"] for m in metas]
    if len(set(shapes)) > 1:
        raise HTTPException(
            400,
            f"Shape band tidak sama: {shapes}. "
            "Semua band harus memiliki resolusi dan dimensi yang identik."
        )

    crs_list = [str(m["crs"]) if m["crs"] else None for m in metas]
    if len(set(crs_list)) > 1:
        raise HTTPException(
            400,
            f"CRS band tidak konsisten: {set(crs_list)}. "
            "Reproject semua band ke CRS yang sama terlebih dahulu."
        )

    resolutions = [tuple(float(v) for v in m["resolution"]) for m in metas]
    if not all(np.allclose(resolutions[0], res, rtol=0, atol=1e-9) for res in resolutions[1:]):
        raise HTTPException(
            400,
            f"Resolusi band tidak konsisten: {resolutions}. "
            "Resample semua band ke resolusi pixel yang sama terlebih dahulu."
        )

    transforms = [tuple(float(v) for v in m["transform"]) for m in metas]
    if not all(np.allclose(transforms[0], tr, rtol=0, atol=1e-9) for tr in transforms[1:]):
        raise HTTPException(
            400,
            "Transform/georeferencing band tidak sama. "
            "Semua band harus berada pada grid pixel, origin, dan rotasi yang identik."
        )

    bounds = [tuple(float(v) for v in m["bounds"]) for m in metas]
    if not all(np.allclose(bounds[0], b, rtol=0, atol=1e-6) for b in bounds[1:]):
        raise HTTPException(
            400,
            f"Extent/bounds band tidak sama: {bounds}. "
            "Crop atau align semua band ke extent yang sama terlebih dahulu."
        )

    # Estimasi resolusi dalam meter
    res = metas[0]["resolution"]
    crs = metas[0]["crs"]
    if crs and crs.is_projected:
        resolution_m = float(res[0])   # sudah dalam meter
    else:
        # Geographic CRS (derajat) → konversi ke meter (approx)
        resolution_m = float(res[0]) * 111_000

    return resolution_m


@router.post("/upload-bands")
async def analyze_from_bands(
    index_name: Annotated[IndexName, Form()],
    threshold_method: Annotated[ThresholdMethod, Form()] = ThresholdMethod.default,
    manual_threshold: Annotated[float | None, Form()] = None,
    # Band files — semua optional, validasi manual sesuai index
    nir:   UploadFile | None = File(default=None, description="Near-Infrared band"),
    red:   UploadFile | None = File(default=None, description="Red band"),
    green: UploadFile | None = File(default=None, description="Green band"),
    blue:  UploadFile | None = File(default=None, description="Blue band"),
    swir:  UploadFile | None = File(default=None, description="SWIR band"),
):
    """
    Upload band satelit → hitung index → analisis luasan vegetasi.

    **Contoh penggunaan:**
    - NDVI: upload `nir` + `red`
    - NDWI: upload `green` + `nir`
    - EVI : upload `nir` + `red` + `blue`

    Format file yang diterima: GeoTIFF (.tif, .tiff)
    """
    # ── 1. Ambil definisi index dari registry ──────────────
    if index_name.value not in INDEX_REGISTRY:
        raise HTTPException(400, f"Index {index_name} tidak dikenal")

    idx_def = INDEX_REGISTRY[index_name.value]
    required = idx_def.required_bands

    # ── 2. Map upload files ke band name ───────────────────
    uploaded = {
        "nir": nir, "red": red, "green": green,
        "blue": blue, "swir": swir
    }

    # Validasi: semua band yang dibutuhkan harus ada
    missing = [b for b in required if uploaded.get(b) is None]
    if missing:
        raise HTTPException(
            422,
            f"Index {index_name.value} membutuhkan band: {required}. "
            f"Band yang belum diupload: {missing}"
        )

    if threshold_method == ThresholdMethod.manual:
        if manual_threshold is None:
            raise HTTPException(
                422,
                "manual_threshold wajib diisi jika threshold_method=manual"
            )
        if not -1.0 <= manual_threshold <= 1.0:
            raise HTTPException(
                422,
                "manual_threshold harus berada dalam rentang -1.0 sampai 1.0"
            )

    # ── 3. Load semua band yang dibutuhkan ─────────────────
    bands = {}
    metas = []
    for band_name in required:
        data, meta = load_band(uploaded[band_name])
        bands[band_name] = data
        metas.append(meta)

    # ── 4. Validasi kompatibilitas antar band ──────────────
    resolution_m = validate_bands_compatible(metas)
    primary_meta = metas[0]

    # ── 5. Hitung index ────────────────────────────────────
    index_array = idx_def.formula(bands)
    index_array = np.clip(index_array, *idx_def.value_range)
    if not np.any(~np.isnan(index_array)):
        raise HTTPException(
            422,
            "Tidak ada pixel valid setelah nodata difilter. "
            "Periksa nilai nodata dan isi band yang diupload."
        )

    # ── 6. Threshold ───────────────────────────────────────
    threshold = compute_threshold(
        index_array=index_array,
        method=threshold_method.value,
        manual_value=manual_threshold,
    )

    # ── 7. Hitung luasan per kelas ─────────────────────────
    job_id = str(uuid.uuid4())[:8]
    geojson_path = str(OUTPUT_DIR / f"{job_id}_{index_name.value}.geojson")

    result = calculate_area_by_class(
        index_array=index_array,
        class_thresholds=idx_def.class_thresholds,
        resolution_m=resolution_m,
        index_name=index_name.value,
        threshold_result=threshold,
        transform=primary_meta["transform"],
        crs=primary_meta["crs"],
        output_geojson=geojson_path
    )

    # ── 8. Simpan GeoTIFF index ────────────────────────────
    tif_path = OUTPUT_DIR / f"{job_id}_{index_name.value}.tif"
    with rasterio.open(
        tif_path, "w", driver="GTiff",
        height=index_array.shape[0], width=index_array.shape[1],
        count=1, dtype="float32",
        crs=primary_meta["crs"],
        transform=primary_meta["transform"]
    ) as dst:
        dst.write(index_array, 1)

    # ── 9. Format response ─────────────────────────────────
    return {
        "job_id": job_id,
        "index": index_name.value,
        "description": idx_def.description,
        "threshold": {
            "method": threshold.method,
            "value": threshold.value,
            "description": threshold.description,
        },
        "spatial_info": {
            "resolution_m": resolution_m,
            "total_area_ha": result.total_area_ha,
            "total_pixels": result.total_valid_pixels,
        },
        "analysis": {
            "dominant_class": result.dominant_class,
            "classes": [
                {
                    "label": c.label,
                    "range": c.threshold_range,
                    "area_ha": c.area_ha,
                    "area_km2": c.area_km2,
                    "percentage": c.percentage,
                    "pixel_count": c.pixel_count,
                }
                for c in result.classes
            ]
        },
        "downloads": {
            "geotiff": f"/analyze/download/{job_id}/{index_name.value}/tif",
            "geojson": f"/analyze/download/{job_id}/{index_name.value}/geojson",
        }
    }
@router.get("/download/{job_id}/{index_name}/{file_type}")
async def download_result(job_id: str, index_name: str, file_type: str):
    if file_type == "tif":
        path = OUTPUT_DIR / f"{job_id}_{index_name}.tif"
        media = "image/tiff"
    elif file_type == "geojson":
        path = OUTPUT_DIR / f"{job_id}_{index_name}.geojson"
        media = "application/geo+json"
    else:
        raise HTTPException(400, "file_type harus 'tif' atau 'geojson'")
    
    if not path.exists():
        raise HTTPException(404, f"File tidak ditemukan: {path.name}")
    
    return FileResponse(path, media_type=media, filename=path.name)
