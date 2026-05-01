 # app/schemas/request.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from enum import Enum

class IndexName(str, Enum):
    NDVI  = "NDVI"
    NDWI  = "NDWI"
    MNDWI = "MNDWI"
    NDBI  = "NDBI"
    EVI   = "EVI"

class ThresholdMethod(str, Enum):
    otsu     = "otsu"
    quantile = "quantile"
    manual   = "manual"
    default  = "default"

class AnalysisParams(BaseModel):
    index_name: IndexName = Field(
        ...,
        description="Index yang dihitung. Menentukan band apa yang harus diupload."
    )
    threshold_method: ThresholdMethod = Field(
        default=ThresholdMethod.default,
        description="Metode threshold untuk klasifikasi"
    )
    manual_threshold: Optional[float] = Field(
        default=None,
        ge=-1.0, le=1.0,
        description="Nilai threshold manual (hanya jika method=manual)"
    )
    pixel_resolution_m: Optional[float] = Field(
        default=None,
        gt=0,
        description="Resolusi spasial dalam meter/pixel. Jika None, dibaca dari GeoTIFF metadata."
    )

    # ── Pydantic V2: gunakan @model_validator untuk validasi lintas field ──
    @model_validator(mode="after")
    def check_manual_threshold(self) -> "AnalysisParams":
        if self.threshold_method == ThresholdMethod.manual and self.manual_threshold is None:
            raise ValueError("manual_threshold wajib diisi jika threshold_method=manual")
        return self