# app/core/index_registry.py

from dataclasses import dataclass
from typing import Callable
import numpy as np

@dataclass
class IndexDefinition:
    """
    Definisi satu spectral index — self-documenting.
    """
    name: str
    required_bands: list[str]        # band apa saja yang dibutuhkan
    formula: Callable                # fungsi hitung index
    description: str
    value_range: tuple               # (min, max) valid range
    class_thresholds: dict           # default threshold interpretasi


# ── Registry semua index yang didukung ──────────────────────
INDEX_REGISTRY: dict[str, IndexDefinition] = {
    "NDVI": IndexDefinition(
        name="NDVI",
        required_bands=["nir", "red"],
        formula=lambda b: (b["nir"] - b["red"]) / (b["nir"] + b["red"] + 1e-10),
        description="Normalized Difference Vegetation Index",
        value_range=(-1, 1),
        class_thresholds={
            "barren / non_veg":       (-1.0, 0.00),   # tanah, batuan, awan, salju
            "very_sparse":            (0.00, 0.10),   # sangat minim hijau
            "low_vegetation":         (0.10, 0.20),   # ladang, semak muda
            "sparse_vegetation":      (0.20, 0.30),   # vegetasi jarang
            "moderate_vegetation":    (0.30, 0.50),   # pertanian, hutan sekunder
            "dense_vegetation":       (0.50, 0.80),   # hutan lebat, mangrove (Sentinel‑2 tropis) [web:14][web:7]
            "very_dense":             (0.80, 1.0),    # canopy sangat rapat
        }
    ),
    "NDWI": IndexDefinition(
        name="NDWI",
        required_bands=["green", "nir"],
        formula=lambda b: (b["green"] - b["nir"]) / (b["green"] + b["nir"] + 1e-10),
        description="Normalized Difference Water Index",
        value_range=(-1, 1),
        class_thresholds={
            "built_up / shadow":      (-1.0, -0.1),   # atap, bayangan awan
            "very_low_water":         (-0.1, 0.0),    # tanah sangat lembab
            "land":                   (0.0,  0.2),     # daratan kering
            "wet_soil":               (0.2,  0.3),     # transisi tanah–air
            "water":                  (0.3,  1.0),     # badan air jelas (Sentinel‑2) [web:18][web:17]
        }
    ),
    "MNDWI": IndexDefinition(
        name="MNDWI",
        required_bands=["green", "swir"],
        formula=lambda b: (b["green"] - b["swir"]) / (b["green"] + b["swir"] + 1e-10),
        description="Modified NDWI — lebih akurat untuk urban area",
        value_range=(-1, 1),
        class_thresholds={
            "built_up":               (-1.0, 0.1),    # area bangunan dan jalan
            "dry_soil":               (0.1,  0.2),     # tanah kering
            "wet_soil":               (0.2,  0.3),     # tanah basah
            "non_urban_water":        (0.3,  0.4),     # air di luar kawasan padat bangunan
            "urban_water":            (0.4,  1.0),     # air dalam kawasan perkotaan (Sentinel‑2) [web:18]
        }
    ),
    "NDBI": IndexDefinition(
        name="NDBI",
        required_bands=["swir", "nir"],
        formula=lambda b: (b["swir"] - b["nir"]) / (b["swir"] + b["nir"] + 1e-10),
        description="Normalized Difference Built-up Index",
        value_range=(-1, 1),
        class_thresholds={
            "non_urban":              (-1.0, 0.0),    # vegetasi, tanah, air
            "semi_urban":             (0.0,  0.15),    # area campuran
            "urban_low":              (0.15, 0.25),   # permukiman menengah
            "urban_high":             (0.25, 0.50),   # kawasan perkotaan padat [web:12]
            "extreme_built":          (0.50, 1.0),    # pusat kota sangat padat
        }
    ),
    "EVI": IndexDefinition(
        name="EVI",
        required_bands=["nir", "red", "blue"],
        formula=lambda b: 2.5 * (
            (b["nir"] - b["red"])
            / (b["nir"] + 6*b["red"] - 7.5*b["blue"] + 1 + 1e-10)
        ),
        description="Enhanced Vegetation Index — robust di area tropis",
        value_range=(-1, 1),
        class_thresholds={
            "non_vegetation":         (-1.0, 0.05),   # tanah, air, bangunan
            "very_sparse":            (0.05, 0.15),   # vegetasi sangat jarang
            "sparse_vegetation":      (0.15, 0.25),   # ladang, semak remaja
            "moderate_vegetation":    (0.25, 0.40),   # pertanian, hutan muda
            "dense_vegetation":       (0.40, 0.70),   # hutan lebat (Sentinel‑2 tropis) [web:11][web:14]
            "very_dense":             (0.70, 1.0),    # hutan sangat rapat / konservasi
        }
    ),
}