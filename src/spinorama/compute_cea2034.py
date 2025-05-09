# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Compute Harman/Olive score for speaker"""

import math

import numpy as np
import pandas as pd

from spinorama import logger


def compute_area_q(alpha_d: float, beta_d: float) -> float:
    """Compute the area of the sphere between 4 lines at alpha and beta angles"""
    alpha = alpha_d * 2 * math.pi / 360
    beta = beta_d * 2 * math.pi / 360
    gamma = math.acos(math.cos(alpha) * math.cos(beta))
    a = math.atan(math.sin(beta) / math.tan(alpha))
    b = math.atan(math.sin(alpha) / math.tan(beta))
    c = math.acos(-math.cos(a) * math.cos(b) + math.sin(a) * math.sin(b) * math.cos(gamma))
    s = 4 * c - 2 * math.pi
    # print('gamma {} A {} B {} C {} S {}'.format(
    #    gamma*360/2/math.pi, A*360/2/math.pi, B*360/2/math.pi, C*360/2/math.pi, S))
    return s


def compute_weigths() -> list[float]:
    """Compute the weigths from the CEA2034 standards"""
    angles = [i * 10 + 5 for i in range(0, 9)] + [90]
    weigth_angles = [compute_area_q(i, i) for i in angles]
    # weigths are the delta between 2 consecutive areas
    weigths = [weigth_angles[0]] + [
        weigth_angles[i] - weigth_angles[i - 1] for i in range(1, len(weigth_angles))
    ]
    weigths[9] *= 2.0
    return weigths


def compute_weigths_hv(weigths: dict[str, float]) -> dict[str, float]:
    """copy weigths to both horizontal and vertical"""
    return (
        dict(weigths)
        | {f"{k}_v": v for k, v in weigths.items()}
        | {f"{k}_h": v for k, v in weigths.items()}
    )


std_weigths = compute_weigths()

sp_weigths = {
    "On Axis": std_weigths[0],
    "180°": std_weigths[0],
    "-180°": std_weigths[0],
    #
    "10°": std_weigths[1],
    "170°": std_weigths[1],
    "-170°": std_weigths[1],
    "-10°": std_weigths[1],
    #
    "20°": std_weigths[2],
    "160°": std_weigths[2],
    "-160°": std_weigths[2],
    "-20°": std_weigths[2],
    #
    "30°": std_weigths[3],
    "150°": std_weigths[3],
    "-150°": std_weigths[3],
    "-30°": std_weigths[3],
    #
    "40°": std_weigths[4],
    "140°": std_weigths[4],
    "-140°": std_weigths[4],
    "-40°": std_weigths[4],
    #
    "50°": std_weigths[5],
    "130°": std_weigths[5],
    "-130°": std_weigths[5],
    "-50°": std_weigths[5],
    #
    "60°": std_weigths[6],
    "120°": std_weigths[6],
    "-120°": std_weigths[6],
    "-60°": std_weigths[6],
    #
    "70°": std_weigths[7],
    "110°": std_weigths[7],
    "-110°": std_weigths[7],
    "-70°": std_weigths[7],
    #
    "80°": std_weigths[8],
    "100°": std_weigths[8],
    "-100°": std_weigths[8],
    "-80°": std_weigths[8],
    #
    "90°": std_weigths[9],
    "-90°": std_weigths[9],
}

# same weigths with multiples keys, this helps when merging dataframes
sp_weigths_hv = compute_weigths_hv(sp_weigths)


def spl2pressure(spl: float) -> float:
    """Convert SPL to pressure"""
    try:
        pressure = pow(10, (spl - 105.0) / 20.0)
    except TypeError:
        logger.exception("spl2pressure spl=%f", spl)
        return 0.0
    return pressure


def pressure2spl(pressure: float) -> float:
    """Convert pressure to SPL"""
    if pressure < 0.0:
        logger.error("pressure is negative p=%f", pressure)
    return 105.0 + 20.0 * math.log10(pressure)


def column_trim(col: str) -> str:
    """Remove _v or _h from a column name"""
    if col[-2:] in ("_v", "_h"):
        return col[:-2]
    return col


def column_valid(col: str) -> bool:
    """True is a column is valid false otherwise"""
    if col[0:4] in ("On A", "Ceil", "Rear", "Fron", "Side", "Floo"):
        return True
    if col == "Freq" or col[0:5] == "Phase":
        return False
    return int(column_trim(col)[:-1]) % 10 == 0


def spatial_average(sp_window: pd.DataFrame, func="rms") -> pd.DataFrame:
    """Compute the spatial average of pressure with a function"""
    sp_cols = sp_window.columns
    if "Freq" not in sp_cols:
        logger.debug("Freq is not in sp_cols")
        return pd.DataFrame()
    if len(sp_window) < 2:
        logger.debug("Len window is %d", len(sp_window))
        return pd.DataFrame()
    result = pd.DataFrame(
        {
            "Freq": sp_window.Freq,
        }
    )

    def weighted_rms(pressure):
        avg = [sp_weigths_hv[c] * pressure[c] ** 2 for c in sp_cols if column_valid(c)]
        wsm = [sp_weigths_hv[c] for c in sp_cols if column_valid(c)]
        return np.sqrt(np.sum(avg) / np.sum(wsm))

    def rms(pressure):
        avg = [pressure[c] ** 2 for c in sp_cols if column_valid(c)]
        n_avg = len(avg)
        # hack
        if n_avg == 0:
            return 0.000000001
        return np.sqrt(np.sum(avg) / n_avg)

    if func == "rms":
        result["dB"] = (
            sp_window.drop(columns=["Freq"])
            .apply(spl2pressure)
            .apply(rms, axis=1)
            .apply(pressure2spl)
        )
    elif func == "weighted_rms":
        result["dB"] = (
            sp_window.drop(columns=["Freq"])
            .apply(spl2pressure)
            .apply(weighted_rms, axis=1)
            .apply(pressure2spl)
        )

    return result.reset_index(drop=True)


def spatial_average1(spl, sel, func="rms") -> pd.DataFrame:
    """Compute the spatial average of SPL 1D"""
    if spl.empty:
        return pd.DataFrame()
    spl_window = spl[[c for c in spl.columns if c in sel]]
    if "Freq" not in spl_window.columns:
        logger.debug("Freq not in spl_window")
        return pd.DataFrame()
    return spatial_average(spl_window, func)


def spatial_average2(
    h_spl: pd.DataFrame,
    h_sel: pd.Index | list[str],
    v_spl: pd.DataFrame,
    v_sel: pd.Index | list[str],
    func="rms",
) -> pd.DataFrame:
    """Compute the spatial average of SPL 2D"""
    if v_spl.empty and h_spl.empty:
        return pd.DataFrame()
    if v_spl.empty:
        return spatial_average1(h_spl, h_sel, func)
    if h_spl.empty:
        return spatial_average1(v_spl, v_sel, func)
    h_spl_sel = h_spl[[c for c in h_spl.columns if c in h_sel]]
    v_spl_sel = v_spl[[c for c in v_spl.columns if c in v_sel]]
    sp_window = h_spl_sel.merge(v_spl_sel, left_on="Freq", right_on="Freq", suffixes=("_h", "_v"))
    return spatial_average(sp_window, func)


def sound_power(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Sound Power
    # The sound power is the weighted rms average of all 70 measurements,
    # with individual measurements weighted according to the portion of the
    # spherical surface that they represent. Calculation of the sound power
    # curve begins with a conversion from SPL to pressure, a scalar magnitude.
    # The individual measures of sound pressure are then weighted according
    # to the values shown in Appendix C and an energy average (rms) is
    # calculated using the weighted values. The final average is converted
    # to SPL.
    """
    h_cols = h_spl.columns
    v_cols = v_spl.columns
    for to_be_dropped in ["On Axis", "180°"]:
        if to_be_dropped in v_cols:
            v_cols = v_cols.drop([to_be_dropped])
    return spatial_average2(h_spl, h_cols, v_spl, v_cols, "weighted_rms")


def listening_window(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute the Listening Window (LW) from the SPL horizontal and vertical"""
    if v_spl.empty or h_spl.empty:
        return pd.DataFrame()
    return spatial_average2(
        h_spl,
        ["Freq", "10°", "20°", "30°", "-10°", "-20°", "-30°"],
        v_spl,
        ["Freq", "On Axis", "10°", "-10°"],
    )


def total_early_reflections(
    floor_bounce: pd.DataFrame,
    ceiling_bounce: pd.DataFrame,
    front_wall_bounce: pd.DataFrame,
    side_wall_bounce: pd.DataFrame,
    rear_wall_bounce: pd.DataFrame,
    method="corrected",
) -> pd.DataFrame:
    if method == "corrected":
        df_spl = pd.DataFrame(
            {
                "Freq": floor_bounce.Freq,
                "Floor": floor_bounce.dB,
                "Ceiling": ceiling_bounce.dB,
                "Front": front_wall_bounce.dB,
                "Side": side_wall_bounce.dB,
                "Rear": rear_wall_bounce.dB,
            }
        )
        return spatial_average1(df_spl, ["Freq", "Floor", "Ceiling", "Front", "Side", "Rear"])

    spl = None
    floor = np.power(10, (floor_bounce.dB - 105.0) / 20.0)
    ceiling = np.power(10, (ceiling_bounce.dB - 105.0) / 20.0)
    side = np.power(10, (side_wall_bounce.dB - 105.0) / 20.0)
    rear = np.power(10, (rear_wall_bounce.dB - 105.0) / 20.0)
    front = np.power(10, (front_wall_bounce.dB - 105.0) / 20.0)

    spl = 105.0 + 20.0 * np.log10(
        np.sqrt((floor**2 + ceiling**2 + side**2 + rear**2 + front**2) / 5.0)
    )
    return pd.DataFrame({"dB": spl})


def early_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame, method="corrected") -> pd.DataFrame:
    """Compute the Early Reflections from the SPL horizontal and vertical"""
    floor_bounce = spatial_average1(v_spl, ["Freq", "-20°", "-30°", "-40°"])

    ceiling_bounce = spatial_average1(v_spl, ["Freq", "40°", "50°", "60°"])

    front_wall_bounce = spatial_average1(
        h_spl, ["Freq", "On Axis", "10°", "20°", "30°", "-10°", "-20°", "-30°"]
    )

    side_wall_bounce = spatial_average1(
        h_spl,
        [
            "Freq",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
            "40°",
            "50°",
            "60°",
            "70°",
            "80°",
        ],
    )

    # CEA2034 error
    rear_wall_bounce = None
    if method == "corrected":
        rear_wall_bounce = spatial_average1(
            h_spl,
            [
                "Freq",
                "-170°",
                "-160°",
                "-150°",
                "-140°",
                "-130°",
                "-120°",
                "-110°",
                "-100°",
                "-90°",
                "90°",
                "100°",
                "110°",
                "120°",
                "130°",
                "140°",
                "150°",
                "160°",
                "170°",
                "180°",
            ],
        )
    else:
        rear_wall_bounce = spatial_average1(
            h_spl,
            [
                "Freq",
                "-90°",
                "90°",
                "180°",
            ],
        )

    total_early_reflection = total_early_reflections(
        floor_bounce=floor_bounce,
        ceiling_bounce=ceiling_bounce,
        front_wall_bounce=front_wall_bounce,
        side_wall_bounce=side_wall_bounce,
        rear_wall_bounce=rear_wall_bounce,
        method=method,
    )

    early_reflection = pd.DataFrame(
        {
            "Freq": h_spl.Freq,
        }
    ).reset_index(drop=True)

    for key, name in [
        ("Floor Bounce", floor_bounce),
        ("Ceiling Bounce", ceiling_bounce),
        ("Front Wall Bounce", front_wall_bounce),
        ("Side Wall Bounce", side_wall_bounce),
        ("Rear Wall Bounce", rear_wall_bounce),
        ("Total Early Reflection", total_early_reflection),
    ]:
        if not name.empty:
            early_reflection[key] = name.dB
        else:
            logger.debug("%s is empty", key)
    return early_reflection.reset_index(drop=True)


def total_vertical_reflections(v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute the Total Vertical Reflections from the SPL horizontal and vertical"""
    return spatial_average1(v_spl, ["Freq", "On Axis", "-20°", "-30°", "-40°", "40°", "50°", "60°"])


def vertical_reflections(v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute vertical reflections

    h_spl: unused
    v_spl: vertical data
    """
    floor_reflection = spatial_average1(v_spl, ["Freq", "-20°", "-30°", "-40°"])

    ceiling_reflection = spatial_average1(v_spl, ["Freq", "40°", "50°", "60°"])

    total_vertical_reflection = total_vertical_reflections(v_spl)

    v_r = pd.DataFrame({"Freq": v_spl.Freq}).reset_index(drop=True)

    # print(vr.shape, onaxis.shape, floor_reflection.shape)
    for key, name in [
        ("Floor Reflection", floor_reflection),
        ("Ceiling Reflection", ceiling_reflection),
        ("Total Vertical Reflection", total_vertical_reflection),
    ]:
        if not name.empty:
            v_r[key] = name.dB
        else:
            logger.debug("%s is empty", key)

    return v_r.reset_index(drop=True)


def total_horizontal_reflections(h_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute the Total Horizontal Reflections from the SPL horizontal and vertical"""
    return spatial_average1(
        h_spl,
        [
            "Freq",
            "On Axis",
            "10°",
            "20°",
            "30°",
            "40°",
            "50°",
            "60°",
            "70°",
            "80°",
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "-10°",
            "-20°",
            "-30°",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
            "-90°",
            "-100°",
            "-110°",
            "-120°",
            "-130°",
            "-140°",
            "-150°",
            "-160°",
            "-170°",
            "180°",
        ],
    )


def horizontal_reflections(h_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute horizontal reflections

    h_spl: horizontal data
    v_spl: unused
    """
    if h_spl.empty:
        return pd.DataFrame()
    # Horizontal Reflections
    # Front: 0°, ± 10o, ± 20o, ± 30o horizontal
    # Side: ± 40°, ± 50°, ± 60°, ± 70°, ± 80° horizontal
    # Rear: ± 90°, ± 100°, ± 110°, ± 120°, ± 130°, ± 140°, ± 150°, ± 160°, ± 170°, 180°
    # horizontal, (i.e.: the horizontal part of the rear hemisphere).
    front = spatial_average1(
        h_spl, ["Freq", "On Axis", "10°", "20°", "30°", "-10°", "-20°", "-30°"]
    )

    side = spatial_average1(
        h_spl,
        [
            "Freq",
            "40°",
            "50°",
            "60°",
            "70°",
            "80°",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
        ],
    )

    rear = spatial_average1(
        h_spl,
        [
            "Freq",
            "90°",
            "100°",
            "110°",
            "120°",
            "130°",
            "140°",
            "150°",
            "160°",
            "170°",
            "-90°",
            "-100°",
            "-110°",
            "-120°",
            "-130°",
            "-140°",
            "-150°",
            "-160°",
            "-170°",
            "180°",
        ],
    )

    total_horizontal_reflection = total_horizontal_reflections(h_spl)

    h_r = pd.DataFrame(
        {
            "Freq": h_spl.Freq,
        }
    ).reset_index(drop=True)
    for key, name in [
        ("Front", front),
        ("Side", side),
        ("Rear", rear),
        ("Total Horizontal Reflection", total_horizontal_reflection),
    ]:
        if not name.empty:
            h_r[key] = name.dB
        else:
            logger.debug("%s is empty", key)
    return h_r.reset_index(drop=True)


def estimated_inroom(l_w: pd.DataFrame, e_r: pd.DataFrame, s_p: pd.DataFrame) -> pd.DataFrame:
    """Compute the Estimated In-Room Response (PIR) from the SPL horizontal and vertical"""
    if l_w.empty or e_r.empty or s_p.empty:
        return pd.DataFrame()
    # The Estimated In-Room Response shall be calculated using the directivity
    # data acquired in Section 5 or Section 6.
    # It shall be comprised of a weighted average of
    #     12 % Listening Window,
    #     44 % Early Reflections,
    # and 44 % Sound Power.
    # The sound pressure levels shall be converted to squared pressure values
    # prior to the weighting and summation. After the weightings have been
    # applied and the squared pressure values summed they shall be converted
    # back to sound pressure levels.
    key = "Total Early Reflection"
    if key not in e_r:
        key = "dB"

    try:
        # print(l_w.dB.shape, e_r[key].shape, s_p.dB.shape)
        # print(l_w.dB.apply(spl2pressure))
        # print(e_r[key].apply(spl2pressure))
        # print(s_p.dB.apply(spl2pressure))

        eir = (
            np.sqrt(
                0.12 * l_w.dB.apply(spl2pressure) ** 2
                + 0.44 * e_r[key].apply(spl2pressure) ** 2
                + 0.44 * s_p.dB.apply(spl2pressure) ** 2
            )
        ).apply(pressure2spl)

        # print(eir)

    except TypeError:
        logger.exception("compute EIR failed")
        return pd.DataFrame()

    return pd.DataFrame({"Freq": l_w.Freq, "Estimated In-Room Response": eir}).reset_index(
        drop=True
    )


def estimated_inroom_hv(
    h_spl: pd.DataFrame, v_spl: pd.DataFrame, method="corrected"
) -> pd.DataFrame:
    """Compute the PIR from the SPL horizontal and vertical"""
    if v_spl.empty or h_spl.empty:
        return pd.DataFrame()
    l_w = listening_window(h_spl, v_spl)
    e_r = early_reflections(h_spl, v_spl, method)
    s_p = sound_power(h_spl, v_spl)
    return estimated_inroom(l_w, e_r, s_p)


def compute_cea2034(h_spl: pd.DataFrame, v_spl: pd.DataFrame, method="corrected") -> pd.DataFrame:
    """Compute all the graphs from CEA2034 from the SPL horizontal and vertical"""
    if v_spl.empty or h_spl.empty:
        return pd.DataFrame()
    # average the 2 onaxis
    onaxis = spatial_average2(h_spl, ["Freq", "On Axis"], v_spl, ["Freq", "On Axis"])
    spin: pd.DataFrame = pd.DataFrame(
        {
            "Freq": onaxis.Freq,
            "On Axis": onaxis.dB,
        }
    ).reset_index(drop=True)
    l_w = listening_window(h_spl, v_spl)
    s_p = sound_power(h_spl, v_spl)
    ter = early_reflections(h_spl, v_spl, method)
    if not l_w.empty:
        lw_col = "Listening Window"
        spin.loc[:, lw_col] = l_w.dB
    if not s_p.empty:
        sp_col = "Sound Power"
        spin.loc[:, sp_col] = s_p.dB

    if "Total Early Reflection" in ter:
        er_col = "Early Reflections"
        spin.loc[:, er_col] = ter["Total Early Reflection"]

    if l_w.empty or s_p.empty or ter.empty:
        logger.error("LW or SP or TER is empty")
        return spin.reset_index(drop=True)

    erdi = pd.DataFrame({"dB": l_w.dB - ter["Total Early Reflection"]})
    # add a di offset to mimic other systems
    di_offset = pd.DataFrame({"dB": [0 for i in range(0, len(erdi))]})
    # Sound Power Directivity Index (SPDI)
    # For the purposes of this standard the Sound Power Directivity Index is defined
    # as the difference between the listening window curve and the sound power curve.
    # An SPDI of 0 dB indicates omnidirectional radiation. The larger the SPDI, the
    # more directional the loudspeaker is in the direction of the reference axis.
    spdi = pd.DataFrame({"dB": l_w.dB - s_p.dB})
    for key, name in [
        ("Early Reflections DI", erdi),
        ("Sound Power DI", spdi),
        ("DI offset", di_offset),
    ]:
        if not name.empty:
            spin.loc[:, key] = name.dB
        else:
            logger.debug("%s is empty", key)
    return spin.reset_index(drop=True)


def compute_onaxis(h_spl: pd.DataFrame | None, v_spl: pd.DataFrame | None) -> pd.DataFrame:
    """Compute On Axis depending of which kind of data we have"""
    onaxis = pd.DataFrame()
    if v_spl is None or v_spl.empty:
        if h_spl is None or h_spl.empty:
            return pd.DataFrame()
        onaxis = spatial_average1(h_spl, ["Freq", "On Axis"])
    else:
        onaxis = spatial_average1(v_spl, ["Freq", "On Axis"])

    if onaxis.empty:
        return onaxis

    return pd.DataFrame(
        {
            "Freq": onaxis.Freq,
            "On Axis": onaxis.dB,
        }
    )
