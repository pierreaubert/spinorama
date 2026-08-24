"""Shared smoothness calculations."""

import numpy as np
import numpy.typing as npt


REFERENCE_SLOPE_DB_PER_DECADE = -np.log(10.0)


def compute_smoothness_regression(
    freq: npt.ArrayLike, spl: npt.ArrayLike
) -> tuple[float, float, float]:
    """Return fitted slope, intercept, and normalized smoothness.

    Smoothness is measured after normalizing the response to the reference
    slope of -1 against ln(f), as in VituixCAD. Since the regression uses
    log10(f), the equivalent reference slope is -ln(10) dB/decade. The
    returned slope and intercept describe the original, unnormalized response.
    """
    x = np.log10(np.asarray(freq, dtype=float))
    y = np.asarray(spl, dtype=float)

    if x.size != y.size:
        raise ValueError

    x_mean = np.mean(x)
    y_mean = np.mean(y)
    ss_xx = np.sum((x - x_mean) ** 2)
    ss_yy = np.sum((y - y_mean) ** 2)

    if ss_xx == 0 or ss_yy == 0:
        # Degenerate case: perfectly flat or single-point response.
        return 0.0, float(y_mean), 1.0

    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    slope = float(ss_xy / ss_xx)
    intercept = float(y_mean - slope * x_mean)

    # Preserve the VituixCAD -1 slope against ln(f) on this log10(f) axis.
    normalized_y = y + x * (REFERENCE_SLOPE_DB_PER_DECADE - slope)
    normalized_y_mean = np.mean(normalized_y)
    normalized_ss_yy = np.sum((normalized_y - normalized_y_mean) ** 2)
    normalized_ss_xy = np.sum((x - x_mean) * (normalized_y - normalized_y_mean))
    normalized_slope = normalized_ss_xy / ss_xx
    normalized_intercept = normalized_y_mean - normalized_slope * x_mean
    normalized_y_pred = normalized_intercept + normalized_slope * x

    ss_res = np.sum((normalized_y - normalized_y_pred) ** 2)
    smoothness = 1.0 - ss_res / normalized_ss_yy
    return slope, intercept, float(max(0.0, min(1.0, smoothness)))
