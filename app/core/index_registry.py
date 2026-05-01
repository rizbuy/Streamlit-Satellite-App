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
            "water_barren":      (-1.0, 0.0),
            "sparse_vegetation": (0.0,  0.2),
            "moderate_vegetation":(0.2, 0.4),
            "dense_vegetation":  (0.4,  1.0),
        }
    ),

    "NDWI": IndexDefinition(
        name="NDWI",
        required_bands=["green", "nir"],
        formula=lambda b: (b["green"] - b["nir"]) / (b["green"] + b["nir"] + 1e-10),
        description="Normalized Difference Water Index",
        value_range=(-1, 1),
        class_thresholds={
            "land":  (-1.0, 0.0),
            "water": (0.0,  1.0),
        }
    ),

    "MNDWI": IndexDefinition(
        name="MNDWI",
        required_bands=["green", "swir"],
        formula=lambda b: (b["green"] - b["swir"]) / (b["green"] + b["swir"] + 1e-10),
        description="Modified NDWI — lebih akurat untuk urban area",
        value_range=(-1, 1),
        class_thresholds={
            "land":  (-1.0, 0.3),
            "water": (0.3,  1.0),
        }
    ),

    "NDBI": IndexDefinition(
        name="NDBI",
        required_bands=["swir", "nir"],
        formula=lambda b: (b["swir"] - b["nir"]) / (b["swir"] + b["nir"] + 1e-10),
        description="Normalized Difference Built-up Index",
        value_range=(-1, 1),
        class_thresholds={
            "non_urban": (-1.0, 0.0),
            "urban":     (0.0,  1.0),
        }
    ),

    "EVI": IndexDefinition(
        name="EVI",
        required_bands=["nir", "red", "blue"],
        formula=lambda b: 2.5 * (
            (b["nir"] - b["red"]) /
            (b["nir"] + 6*b["red"] - 7.5*b["blue"] + 1 + 1e-10)
        ),
        description="Enhanced Vegetation Index — robust di area tropis",
        value_range=(-1, 1),
        class_thresholds={
            "non_vegetation":    (-1.0, 0.1),
            "sparse_vegetation": (0.1,  0.3),
            "dense_vegetation":  (0.3,  1.0),
        }
    ),
}