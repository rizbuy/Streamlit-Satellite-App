# app/services/threshold.py
import numpy as np
from skimage.filters import threshold_otsu
from dataclasses import dataclass

@dataclass
class ThresholdResult:
    method: str
    value: float
    description: str


def compute_threshold(
    index_array: np.ndarray,
    method: str,
    manual_value: float = None,
    quantile: float = 0.5
) -> ThresholdResult:
    """
    Tentukan threshold optimal dari index array.

    Methods:
    - otsu     : Otsu's binarization — optimal untuk bimodal distribution
    - quantile : Berdasarkan percentile distribusi data
    - manual   : User-defined
    - default  : Gunakan nilai default dari registry
    """
    # Flatten dan filter nodata
    valid = index_array[~np.isnan(index_array)].flatten()

    if method == "otsu":
        # Otsu: cari threshold yang memaksimalkan variance antar kelas
        # Sangat cocok untuk data NDVI yang biasanya bimodal
        # (vegetasi vs non-vegetasi)
        value = float(threshold_otsu(valid))
        return ThresholdResult(
            method="otsu",
            value=round(value, 4),
            description=f"Otsu optimal threshold — memisahkan 2 distribusi data"
        )

    elif method == "quantile":
        # Gunakan median sebagai threshold (robust terhadap outlier)
        value = float(np.quantile(valid, quantile))
        return ThresholdResult(
            method="quantile",
            value=round(value, 4),
            description=f"Quantile-{quantile*100:.0f}% threshold = {value:.4f}"
        )

    elif method == "manual":
        return ThresholdResult(
            method="manual",
            value=manual_value,
            description=f"User-defined threshold = {manual_value}"
        )

    else:  # default
        # Return None → caller gunakan class_thresholds dari registry
        return ThresholdResult(
            method="default",
            value=None,
            description="Menggunakan threshold default dari index definition"
        )