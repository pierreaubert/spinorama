# -*- coding: utf-8 -*-
# you can check the syntax with pylint or with ../scripts/check_meta.py
from typing import TypedDict, Literal


# extra speaker info
class Dispersion(TypedDict, total=False):
    horizontal: float
    vertical: float


class SPL(TypedDict, total=False):
    peak: float
    continuous: float
    max: float
    m_noise: float
    b_noise: float
    pink_noise: float


class Size(TypedDict):
    height: float
    width: float
    depth: float


class Specifications(TypedDict, total=False):
    dispersion: Dispersion
    sensitivity: float
    impedance: float
    SPL: SPL
    size: Size
    weight: float


class Extras(TypedDict, total=False):
    is_equed: bool
    score_penalty: float


MeasurementFormat = Literal[
    "klippel", "webplotdigitizer", "spl_hv_txt", "gll_hv_txt", "princeton", "rew_text_dump"
]


class MeasurementRequired(TypedDict):
    origin: str
    format: MeasurementFormat


class DataAcquisition(TypedDict, total=False):
    via: str
    distance: float
    signal: str
    air_absorbtion: bool
    resolution: float
    notes: str


class Parameters(TypedDict):
    mean_min: int
    mean_max: int


MeasurementQuality = Literal["low", "medium", "high", "unknown"]


Symmetry = Literal["coaxial", "vertical", "horizontal"]


class PrefRating(TypedDict, total=False):
    aad_on_axis: float
    nbd_on_axis: float
    nbd_listening_window: float
    nbd_sound_power: float
    nbd_pred_in_room: float
    sm_pred_in_room: float
    sm_sound_power: float
    pref_score: float
    pref_score_wsub: float
    lfx_hz: float
    lfq: float


class Measurement(MeasurementRequired, total=False):
    review: str
    reviews: dict[str, str]
    review_published: str
    specifications: Specifications
    quality: MeasurementQuality
    notes: str
    data_acquisition: DataAcquisition
    extras: Extras
    symmetry: Symmetry
    parameters: Parameters
    estimates: dict[str, float]
    estimates_eq: dict[str, float]
    pref_rating: PrefRating
    scaled_pref_rating: PrefRating
    pref_rating_eq: dict[str, float]
    sensitivity: float


class Peq(TypedDict, total=False):
    type: int
    freq: float
    srate: float
    Q: float
    dbGain: float


class EQ(TypedDict, total=False):
    display_name: str
    filename: str
    pream_gain: float
    type: str
    peq: list[Peq]


SpeakerType = Literal["passive", "active"]


SpeakerShape = Literal[
    "floorstanders",
    "bookshelves",
    "center",
    "surround",
    "omnidirectional",
    "columns",
    "cbt",
    "outdoor",
    "panel",
    "inwall",
    "soundbar",
    "liveportable",
    "toursound",
    "cinema",
]


class SpeakerRequired(TypedDict):
    brand: str
    model: str
    type: SpeakerType
    shape: SpeakerShape
    default_measurement: str
    measurements: dict[str, Measurement]


class Speaker(SpeakerRequired, total=False):
    price: str
    amount: str
    skip: bool
    sensitivity: float
    default_eq: str
    eqs: dict[str, EQ]
    nearest: list[tuple[float, str]]


SpeakerDatabase = dict[str, Speaker]

# common GLL extraction
gll_data_acquisition_std: DataAcquisition = {
    "via": "gll",
    "distance": 10,
    "signal": "aes 20Hz-20kHz",
    "air_absorbtion": False,
    "resolution": 2.5,
}
