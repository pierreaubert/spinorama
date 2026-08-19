import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from export_sm_normalization import _sm_pair, build_rows
from spinorama.measurements import Measurements


def test_sm_pair_reports_raw_and_reference_slope_normalized_values() -> None:
    freq = np.geomspace(100.0, 16000.0, 200)
    values = 80.0 + 4.0 * np.log10(freq) + np.sin(np.linspace(0.0, 12.0 * np.pi, freq.size))
    frame = pd.DataFrame({"Freq": freq, "Sound Power": values})

    raw_r2, normalized_r2 = _sm_pair(frame, "Sound Power")

    assert raw_r2 is not None
    assert normalized_r2 is not None
    assert normalized_r2 < raw_r2


def test_build_rows_exports_default_score_curves() -> None:
    freq = np.geomspace(100.0, 16000.0, 20)
    cea2034 = pd.DataFrame(
        {
            "Freq": freq,
            "Sound Power": 80.0 + 4.0 * np.log10(freq),
        }
    )
    eir = pd.DataFrame(
        {
            "Freq": freq,
            "Estimated In-Room Response": 80.0 + 3.0 * np.log10(freq),
        }
    )
    cached = {"Test Speaker": {"ASR": {"asr": Measurements(cea2034=cea2034, eir=eir)}}}
    metadata = {
        "Test Speaker": {
            "brand": "Test",
            "model": "Speaker",
            "default_measurement": "asr",
            "measurements": {"asr": {"origin": "ASR"}},
        }
    }

    rows = build_rows(cached, metadata)

    assert len(rows) == 1
    assert rows[0]["status"] == "ok"
    assert rows[0]["sm_sound_power_raw_r2"] == 1.0
    assert rows[0]["sm_sound_power_normalized_r2"] == 1.0
    assert rows[0]["sm_pred_in_room_raw_r2"] == 1.0
    assert rows[0]["sm_pred_in_room_normalized_r2"] == 1.0
