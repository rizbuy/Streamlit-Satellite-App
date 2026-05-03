# app/services/area_calculator.py
import numpy as np #untuk pengolahan array
import rasterio # untuk pengolahan data raster pada data geospasial
from rasterio.features import shapes # untuk mengubah raster menjadi vektor
from shapely.geometry import shape, mapping # untuk menangani geometri vektor
from shapely.ops import unary_union # untuk menggabungkan geometri yang saling bersinggungan
import geopandas as gpd # untuk mengelola data geospasial dalam format GeoDataFrame
from dataclasses import dataclass, field # untuk mempermudah pembuatan kelas data

@dataclass
class AreaClass:
    label: str
    threshold_range: tuple
    pixel_count: int
    area_m2: float
    area_ha: float
    area_km2: float
    percentage: float

@dataclass
class AreaAnalysisResult:
    index_name: str
    threshold_method: str
    threshold_value: float | None
    resolution_m: float
    total_valid_pixels: int
    total_area_ha: float
    classes: list[AreaClass]
    dominant_class: str
    geojson_path: str | None = None


def calculate_area_by_class(
    index_array: np.ndarray,
    class_thresholds: dict,
    resolution_m: float,
    index_name: str,
    threshold_result,
    transform=None,
    crs=None,
    output_geojson: str = None
) -> AreaAnalysisResult:
    """
    Hitung luasan setiap kelas berdasarkan threshold.

    Prinsip:
    - Setiap pixel = resolusi² meter persegi
    - Luasan = jumlah pixel per kelas × (resolusi × resolusi)
    """
    pixel_area_m2 = resolution_m ** 2
    pixel_area_ha = pixel_area_m2 / 10_000       # 1 ha = 10.000 m²
    pixel_area_km2 = pixel_area_m2 / 1_000_000  # 1 km² = 1.000.000 m²

    valid_mask = ~np.isnan(index_array)
    total_valid = int(np.sum(valid_mask))
    if total_valid == 0:
        raise ValueError("index_array tidak memiliki pixel valid untuk analisis area")
    total_area_ha = total_valid * pixel_area_ha

    # Jika threshold manual/otsu → override class jadi binary
    if threshold_result.value is not None:
        t = threshold_result.value
        class_thresholds = {
            f"below_{t:.3f}": (-1.0, t),
            f"above_{t:.3f}": (t, 1.0),
        }

    classes = []
    class_masks = {}   # simpan untuk GeoJSON export
    max_upper_bound = max(high for _, high in class_thresholds.values())

    for label, (low, high) in class_thresholds.items():
        # Mask pixel yang masuk kelas ini
        if high == max_upper_bound:
            upper_mask = index_array <= high
        else:
            upper_mask = index_array < high
        class_mask = (index_array >= low) & upper_mask & valid_mask
        count = int(np.sum(class_mask))
        class_masks[label] = class_mask

        classes.append(AreaClass(
            label=label,
            threshold_range=(low, high),
            pixel_count=count,
            area_m2=round(count * pixel_area_m2, 2),
            area_ha=round(count * pixel_area_ha, 4),
            area_km2=round(count * pixel_area_km2, 6),
            percentage=round(count / total_valid * 100, 2) if total_valid > 0 else 0,
        ))

    dominant = max(classes, key=lambda c: c.pixel_count).label

    # Export GeoJSON jika ada georeferencing info
    geojson_path = None
    if output_geojson and transform and crs:
        geojson_path = _export_geojson(
            class_masks, index_array, transform, crs, output_geojson
        )

    return AreaAnalysisResult(
        index_name=index_name,
        threshold_method=threshold_result.method,
        threshold_value=threshold_result.value,
        resolution_m=resolution_m,
        total_valid_pixels=total_valid,
        total_area_ha=round(total_area_ha, 4),
        classes=classes,
        dominant_class=dominant,
        geojson_path=geojson_path
    )


def _export_geojson(class_masks, index_array, transform, crs, output_path):
    """
    Konversi mask raster → polygon GeoJSON per kelas.
    Berguna untuk visualisasi di peta (Leaflet, QGIS, dll).
    """
    all_features = []

    for label, mask in class_masks.items():
        mask_uint8 = mask.astype(np.uint8)

        # rasterio.features.shapes: raster → vector polygons
        for geom, value in shapes(mask_uint8, transform=transform):
            if value == 1:
                all_features.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": {"class": label}
                })

    gdf = gpd.GeoDataFrame.from_features(all_features, crs=crs)
    # Dissolve polygon per kelas (merge yang bersentuhan)
    gdf = gdf.dissolve(by="class").reset_index()
    gdf.to_file(output_path, driver="GeoJSON")
    return output_path
