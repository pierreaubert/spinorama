#                                                  -*- coding: utf-8 -*-
import logging
import math
import numpy as np
import pandas as pd

logger = logging.getLogger("spinorama")


def compute_areaQ(alpha_d, beta_d):
    """Compute the area of the sphere between 4 lines at alpha and beta angles"""
    alpha = alpha_d * 2 * math.pi / 360
    beta = beta_d * 2 * math.pi / 360
    gamma = math.acos(math.cos(alpha) * math.cos(beta))
    A = math.atan(math.sin(beta) / math.tan(alpha))
    B = math.atan(math.sin(alpha) / math.tan(beta))
    C = math.acos(
        -math.cos(A) * math.cos(B) + math.sin(A) * math.sin(B) * math.cos(gamma)
    )
    S = 4 * C - 2 * math.pi
    # print('gamma {} A {} B {} C {} S {}'.format(
    #    gamma*360/2/math.pi, A*360/2/math.pi, B*360/2/math.pi, C*360/2/math.pi, S))
    return S


def compute_weigths():
    """Compute the weigths from the CEA2034 standards"""
    a = [i * 10 + 5 for i in range(0, 9)] + [90]
    wa = [compute_areaQ(i, i) for i in a]
    # weigths are the delta between 2 consecutive areas
    w = [wa[0]] + [wa[i] - wa[i - 1] for i in range(1, len(wa))]
    # hum not sure about that. It matches the standards
    w[9] *= 2.0
    return w


std_weigths = compute_weigths()

sp_weigths = {
    "On Axis": std_weigths[0],
    "180°": std_weigths[0],
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
sp_weigths_hv = {}
for k, v in sp_weigths.items():
    sp_weigths_hv[k] = v
    sp_weigths_hv["{0}_h".format(k)] = v
    sp_weigths_hv["{0}_v".format(k)] = v


def spl2pressure(spl: float) -> float:
    """Convert SPL to pressure"""
    try:
        p = pow(10, (spl - 105.0) / 20.0)
        return p
    except TypeError as e:
        print("spl2pressure: spl={0} e={1}".format(spl, e))
        logger.error("spl2pressure spl={0} e={1}".format(spl, e))


def pressure2spl(p: float) -> float:
    """Convert pressure to SPL"""
    if p < 0.0:
        print("pressure is negative p={0}".format(p))
        logger.error("pressure is negative p={0}".format(p))
    return 105.0 + 20.0 * math.log10(p)


def column_trim(c):
    """Remove _v or _h from a column name"""
    if c[-2:] in ("_v", "_h"):
        return c[:-2]
    return c


def column_valid(c):
    """True is a column is valid false otherwise"""
    if c[0] == "O":
        return True
    if c[0] == "F":
        return False
    if int(column_trim(c)[:-1]) % 10 == 0:
        return True
    return False


def spatial_average(sp_window, func="rms"):
    """Compute the spatial average of pressure with a function"""
    sp_cols = sp_window.columns
    if "Freq" not in sp_cols:
        logger.debug("Freq is not in sp_cols")
        return None
    if len(sp_window) < 2:
        logger.debug("Len window is {0}".format(len(sp_window)))
        return None

    result = pd.DataFrame({"Freq": sp_window.Freq,})

    def weighted_rms(spl):
        avg = [sp_weigths_hv[c] * spl[c] ** 2 for c in sp_cols if column_valid(c)]
        wsm = [sp_weigths_hv[c] for c in sp_cols if column_valid(c)]
        return np.sqrt(np.sum(avg) / np.sum(wsm))

    def rms(spl):
        avg = [spl[c] ** 2 for c in sp_cols if column_valid(c)]
        n = len(avg)
        # hack
        if n == 0:
            return 0.000000001
        r = np.sqrt(np.sum(avg) / n)
        return r

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


def spatial_average1(spl, sel, func="rms"):
    """Compute the spatial average of SPL 1D"""
    if spl is None:
        return None
    spl_window = spl[[c for c in spl.columns if c in sel]]
    if "Freq" not in spl_window.columns:
        logger.debug("Freq not in spl_window")
        return None
    return spatial_average(spl_window, func)


def spatial_average2(
    h_spl: pd.DataFrame, h_sel, v_spl: pd.DataFrame, v_sel, func="rms"
) -> pd.DataFrame:
    """Compute the spatial average of SPL 2D"""
    if v_spl is None and h_spl is None:
        return None
    if v_spl is None:
        return spatial_average1(h_spl, h_sel, func)
    if h_spl is None:
        return spatial_average1(v_spl, v_sel, func)
    h_spl_sel = h_spl[[c for c in h_spl.columns if c in h_sel]]
    v_spl_sel = v_spl[[c for c in v_spl.columns if c in v_sel]]
    sp_window = h_spl_sel.merge(
        v_spl_sel, left_on="Freq", right_on="Freq", suffixes=("_h", "_v")
    )
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


def listening_window(h_spl, v_spl):
    """Compute the Listening Window (LW) from the SPL horizontal and vertical"""
    if v_spl is None or h_spl is None:
        return None
    return spatial_average2(
        h_spl,
        ["Freq", "10°", "20°", "30°", "-10°", "-20°", "-30°"],
        v_spl,
        ["Freq", "On Axis", "10°", "-10°"],
    )


def total_early_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.Series:
    """Compute the Total Early Reflections from the SPL horizontal and vertical"""
    if v_spl is None or h_spl is None:
        return None
    return spatial_average2(
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
            "-10°",
            "-20°",
            "-30°",
            "-40°",
            "-50°",
            "-60°",
            "-70°",
            "-80°",
            "-90°",
            "180°",
        ],
        v_spl,
        ["Freq", "On Axis", "-20°", "-30°", "-40°", "40°", "50°", "60°"],
    )


def early_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute the Early Reflections from the SPL horizontal and vertical"""
    if v_spl is None or h_spl is None:
        return None
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

    rear_wall_bounce = spatial_average1(h_spl, ["Freq", "-90°", "90°", "180°"])

    total_early_reflection = total_early_reflections(h_spl, v_spl)

    er = pd.DataFrame({"Freq": h_spl.Freq,}).reset_index(drop=True)

    for (key, name) in [
        ("Floor Bounce", floor_bounce),
        ("Ceiling Bounce", ceiling_bounce),
        ("Front Wall Bounce", front_wall_bounce),
        ("Side Wall Bounce", side_wall_bounce),
        ("Rear Wall Bounce", rear_wall_bounce),
        ("Total Early Reflection", total_early_reflection),
    ]:
        if name is not None:
            er[key] = name.dB
        else:
            logger.debug("{0} is None".format(key))
    return er.reset_index(drop=True)


def total_vertical_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.Series:
    """Compute the Total Vertical Reflections from the SPL horizontal and vertical"""
    if v_spl is None or h_spl is None:
        return None
    return spatial_average1(
        v_spl, ["Freq", "On Axis", "-20°", "-30°", "-40°", "40°", "50°", "60°"]
    )


def vertical_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute vertical reflections

    h_spl: unused
    v_spl: vertical data
    """
    if v_spl is None:
        return None
    floor_reflection = spatial_average1(v_spl, ["Freq", "-20°", "-30°", "-40°"])

    ceiling_reflection = spatial_average1(v_spl, ["Freq", "40°", "50°", "60°"])

    total_vertical_reflection = total_vertical_reflections(h_spl, v_spl)

    vr = pd.DataFrame({"Freq": v_spl.Freq}).reset_index(drop=True)

    # print(vr.shape, onaxis.shape, floor_reflection.shape)
    for (key, name) in [
        ("Floor Reflection", floor_reflection),
        ("Ceiling Reflection", ceiling_reflection),
        ("Total Vertical Reflection", total_vertical_reflection),
    ]:
        if name is not None:
            vr[key] = name.dB
        else:
            logger.debug("{0} is None".format(key))

    return vr.reset_index(drop=True)


def total_horizontal_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.Series:
    """Compute the Total Horizontal Reflections from the SPL horizontal and vertical"""
    if v_spl is None or h_spl is None:
        return None
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


def horizontal_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute horizontal reflections

    h_spl: horizontal data
    v_spl: unused
    """
    if h_spl is None:
        return None
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

    total_horizontal_reflection = total_horizontal_reflections(h_spl, v_spl)

    hr = pd.DataFrame({"Freq": h_spl.Freq,}).reset_index(drop=True)
    for (key, name) in [
        ("Front", front),
        ("Side", side),
        ("Rear", rear),
        ("Total Horizontal Reflection", total_horizontal_reflection),
    ]:
        if name is not None:
            hr[key] = name.dB
        else:
            logger.debug("{0} is None".format(key))
    return hr.reset_index(drop=True)


def estimated_inroom(
    lw: pd.DataFrame, er: pd.DataFrame, sp: pd.DataFrame
) -> pd.DataFrame:
    """Compute the Estimated In-Room Response (PIR) from the SPL horizontal and vertical"""
    if lw is None or er is None or sp is None:
        return None
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
    if key not in er.keys():
        key = "dB"

    try:
        # print(lw.dB.shape, er[key].shape, sp.dB.shape)
        # print(lw.dB.apply(spl2pressure))
        # print(er[key].apply(spl2pressure))
        # print(sp.dB.apply(spl2pressure))

        eir = (
            0.12 * lw.dB.apply(spl2pressure)
            + 0.44 * er[key].apply(spl2pressure)
            + 0.44 * sp.dB.apply(spl2pressure)
        )

        # print(eir)

        return pd.DataFrame(
            {"Freq": lw.Freq, "Estimated In-Room Response": eir.apply(pressure2spl)}
        ).reset_index(drop=True)
    except TypeError as e:
        logger.error(e)
        return None


def estimated_inroom_HV(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute the PIR from the SPL horizontal and vertical"""
    if v_spl is None or h_spl is None:
        return None
    lw = listening_window(h_spl, v_spl)
    er = early_reflections(h_spl, v_spl)
    sp = sound_power(h_spl, v_spl)
    return estimated_inroom(lw, er, sp)


def compute_cea2034(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute all the graphs from CEA2034 from the SPL horizontal and vertical"""
    if v_spl is None or h_spl is None:
        return None
    # average the 2 onaxis
    onaxis = spatial_average2(h_spl, ["Freq", "On Axis"], v_spl, ["Freq", "On Axis"])
    spin = pd.DataFrame({"Freq": onaxis.Freq, "On Axis": onaxis.dB,}).reset_index(
        drop=True
    )
    lw = listening_window(h_spl, v_spl)
    sp = sound_power(h_spl, v_spl)
    # Early Reflections Directivity Index (ERDI)
    # The Early Reflections Directivity Index is defined as the difference
    # between the listening window curve and the early reflections curve.
    erb = total_early_reflections(h_spl, v_spl)
    erdi = lw.dB - erb.dB
    # add a di offset to mimic other systems
    di_offset = [0 for i in range(0, len(erdi))]
    # Sound Power Directivity Index (SPDI)
    # For the purposes of this standard the Sound Power Directivity Index is defined
    # as the difference between the listening window curve and the sound power curve.
    # An SPDI of 0 dB indicates omnidirectional radiation. The larger the SPDI, the
    # more directional the loudspeaker is in the direction of the reference axis.
    spdi = lw.dB - sp.dB
    for (key, name) in [
        ("Listening Window", lw),
        ("Sound Power", sp),
        ("Early Reflections", erb),
    ]:
        if name is not None:
            spin[key] = name.dB
        else:
            logger.debug("{0} is None".format(key))
    for (key, name) in [
        ("Early Reflections DI", erdi),
        ("Sound Power DI", spdi),
        ("DI offset", di_offset),
    ]:
        if name is not None:
            spin[key] = name
        else:
            logger.debug("{0} is None".format(key))
    return spin.reset_index(drop=True)


def compute_onaxis(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute On Axis depending of which kind of data we have"""
    onaxis = None
    if v_spl is None:
        if h_spl is None:
            return None
        onaxis = spatial_average1(h_spl, ["Freq", "On Axis"])
    else:
        onaxis = spatial_average1(v_spl, ["Freq", "On Axis"])

    if onaxis is None:
        return None

    df = pd.DataFrame({"Freq": onaxis.Freq, "On Axis": onaxis.dB,})
    return df
