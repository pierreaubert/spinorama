# -*- coding: utf-8 -*-
def space2url(context, text):
    """basic url escaping"""
    return text.replace(" ", "%20").replace("&", "%26")


def space2dash(context, text):
    return (
        text.replace(" ", "-")
        .replace("'", "-")
        .replace(".", "-")
        .replace("+", "-")
        .replace("&", "-")
    )


def removeVendors(context, text):  # noqa: N802
    return text.replace("Vendors-", "").replace(" ", "%20").replace("&", "%26")


def eq2text(context, eq):
    text = {
        "0": "LowPass",
        "1": "HighPass",
        "2": "BandPass",
        "3": "Peak",
        "4": "Notch",
        "5": "LowShelf",
        "6": "HighShelf",
    }
    return text.get(eq, "ERROR")


def unmeltC(context, text):  # noqa: N802
    return text.replace("_unmelted", " Contour")


def unmeltI(context, text):  # noqa: N802
    return text.replace("_unmelted", " IsoBand")


def unmeltR(context, text):  # noqa: N802
    return text.replace("_unmelted", " Radar")


def float2str(context, f):
    if "." not in f:
        return f
    return f.split(".")[0]


def eqtype2str(context, eq_type: str) -> str:
    infos = {
        "0": "LP",
        "1": "HP",
        "2": "BP",
        "3": "PK",
        "4": "NO",
        "5": "LS",
        "6": "HS",
    }
    return infos.get(eq_type, "??")


import re  # noqa: E402


_VALID_SHAPES = frozenset(
    ["floorstanders", "bookshelves", "center", "columns", "liveportable", "cinema"]
)


def _remove_vendors(text):
    return text.replace("Vendors-", "")


def _encode_uri(text):
    return text.replace(" ", "%20").replace("&", "%26")


def sanitize_filename(context, name: str) -> str:
    """Replace characters invalid on Windows filesystems with underscores."""
    invalid_chars = '|:<>"\\/\\?*'
    for char in invalid_chars:
        name = name.replace(char, "_")
    return name


def get_id(context, brand, model):
    return re.sub(r"['.+& |]", "-", brand + " " + model)


def get_price(context, price, amount):
    try:
        val = float(price)
    except (ValueError, TypeError):
        return "?"
    if amount and amount == "each":
        return str(price)
    return str(val / 2.0)


def get_dollar(context, price):
    if price == "?":
        return price
    iprice = int(float(price))
    if iprice <= 200:
        return "$"
    elif iprice <= 500:
        return "$$"
    return "$$$"


def get_picture_url(context, brand, model, suffix):
    return _encode_uri(
        "pictures/"
        + sanitize_filename(context, brand)
        + " "
        + sanitize_filename(context, model)
        + "."
        + suffix
    )


def icon_value(context, value):
    if value == "***":
        return "0"
    try:
        iv = int(float(value))
    except (ValueError, TypeError):
        return "0"
    if iv <= 30:
        return "0"
    elif iv <= 60:
        return "1"
    elif iv <= 90:
        return "2"
    return "3"


def get_loading(context, index):
    if index < 12:
        return "eager"
    return "lazy"


def get_decoding(context, index):
    if index < 12:
        return "sync"
    return "async"


def get_score(context, value):
    defm = value.get("default_measurement")
    score = "***"
    lfx = "***"
    flatness = 0.0
    smoothness = "***"
    score_scaled = "***"
    lfx_scaled = "***"
    flatness_scaled = 0.0
    smoothness_scaled = "***"

    measurements = value.get("measurements", {})
    if defm and defm in measurements:
        measurement = measurements[defm]

        estimates = measurement.get("estimates", {})
        if estimates:
            flatness = estimates.get("ref_band", 0.0)

        scaled = measurement.get("scaled_pref_rating", {})
        if scaled and "scaled_flatness" in scaled:
            flatness_scaled = scaled["scaled_flatness"]

        pref = measurement.get("pref_rating")
        if pref:
            score = pref.get("pref_score", 0.0)
            lfx = pref.get("lfx_hz", 0.0)
            smoothness = pref.get("sm_pred_in_room", 0.0)

            score_scaled = scaled.get("scaled_pref_score", 0.0)
            lfx_scaled = scaled.get("scaled_lfx_hz", 0.0)
            smoothness_scaled = scaled.get("scaled_sm_pred_in_room", 0.0)

    return {
        "score": "{:.1f}".format(float(score)) if score != "***" else score,
        "lfx": "{:.0f}".format(float(lfx)) if lfx != "***" else lfx,
        "flatness": "{:.1f}".format(float(flatness)),
        "smoothness": "{:.1f}".format(float(smoothness)) if smoothness != "***" else smoothness,
        "scoreScaled": "{:.1f}".format(float(score_scaled))
        if score_scaled != "***"
        else score_scaled,
        "lfxScaled": lfx_scaled,
        "flatnessScaled": flatness_scaled,
        "smoothnessScaled": smoothness_scaled,
    }


def get_sensitivity(context, value):
    defm = value.get("default_measurement")
    if value.get("type") == "passive" and defm and defm in value.get("measurements", {}):
        measurement = value["measurements"][defm]
        specs = measurement.get("specifications", {})
        if specs and "sensitivity" in specs:
            return specs["sensitivity"]
        computed = measurement.get("computed_sensitivity", {})
        if computed:
            return computed.get("sensitivity_1m") or computed.get("computed", 0)
    return 0


def get_spl(context, value):
    defm = value.get("default_measurement")
    measurements = value.get("measurements", {})
    if defm and defm in measurements:
        specs = measurements[defm].get("specifications", {})
        if specs:
            spl = specs.get("SPL", {})
            if spl:
                if "peak" in spl:
                    return ("Peak", spl["peak"])
                elif "max" in spl:
                    return ("Max", spl["max"])
                elif "continuous" in spl:
                    return ("Continuous", spl["continuous"])
    return ("***", 0.0)


def get_default_url(context, value):
    defm = value.get("default_measurement")
    measurements = value.get("measurements", {})
    if defm and defm in measurements:
        origin = measurements[defm].get("origin", "")
        return _encode_uri(
            "speakers/"
            + sanitize_filename(context, value["brand"])
            + " "
            + sanitize_filename(context, value["model"])
            + "/"
            + _remove_vendors(origin)
            + "/index_"
            + defm
            + ".html"
        )
    return None


_REVIEWER_ICONS = [
    (
        "Audio First Design",
        '<img width="16" height="16" src="/pictures/icon-afd-32x32.webp" alt="">',
    ),
    (
        "Audio Science Review",
        '<img width="16" height="16" src="/pictures/icon-asr-32x32.webp" alt="">',
    ),
    ("Danley", '<img width="16" height="16" src="/pictures/icon-danley-32x32.webp" alt="">'),
    (
        "Erin's Audio Corner",
        '<img width="16" height="16" src="/pictures/icon-eac-32x32.webp" alt="">',
    ),
    ("JBL", '<img width="16" height="16" src="/pictures/icon-jbl-32x32.webp" alt="">'),
    ("KEF", '<img width="16" height="16" src="/pictures/icon-kef-32x32.webp" alt="">'),
    ("Genelec", '<img width="16" height="16" src="/pictures/icon-genelec-32x32.webp" alt="">'),
    ("Neumann", '<img width="16" height="16" src="/pictures/icon-neumann-32x32.webp" alt="">'),
    ("Perlisten", '<img width="16" height="16" src="/pictures/icon-perlisten-32x32.webp" alt="">'),
    ("Sigberg", '<img width="16" height="16" src="/pictures/icon-sigbergaudio-32x32.webp" alt="">'),
]


def get_reviews(context, value):
    reviews = []
    measurements = value.get("measurements", {})
    for version, measurement in measurements.items():
        origin = measurement.get("origin", "")
        origin_long = origin
        origin_short = origin

        url = _encode_uri(
            "speakers/"
            + sanitize_filename(context, value["brand"])
            + " "
            + sanitize_filename(context, value["model"])
            + "/"
            + _remove_vendors(origin)
            + "/index_"
            + version
            + ".html"
        )

        if origin == "Misc":
            origin = version.replace("misc-", "")
            origin_short = version.replace("misc-", "")
            origin_long = version.replace("misc-", "")
        else:
            origin = origin.replace("Vendors-", "")
            origin_short = origin.replace("Vendors-", "")
            origin_long = origin.replace("Vendors-", "")

        if origin == "Princeton":
            origin_short = "Pri."
        elif origin == "napilopez":
            origin = "Napilopez"
            origin_short = "Nap."
        elif origin == "speakerdata2034":
            origin = "SpeakerData2034"
            origin_short = "SPD."
        elif origin == "archimago":
            origin = "Archimago"
            origin_short = "Arc."
        elif origin == "audioxpress":
            origin = "AudioXPress"
            origin_short = "Axp."
        elif origin == "audioholics":
            origin_short = "Aud."
        elif origin == "soundstageultra":
            origin = "Sound Stage Ultra"
            origin_short = "SSU."
        elif origin == "sr":
            origin = "Sound & Recordings"
            origin_short = "S&R"
        elif "nuyes" in origin:
            origin = "Nuyes"
            origin_short = "Nuy."
        elif "ASR" in origin:
            origin_short = "ASR"
            origin = "Audio Science Review"
        elif "ErinsAudioCorner" in origin:
            origin = "Erin's Audio Corner"
            origin_short = "EAC"
        elif "pp" in origin and origin != "Topping":
            origin = "Production Partner"
            origin_short = "PP"
        elif origin == "Danley":
            origin_short = "Danley"
        elif origin == "Perlisten":
            origin_short = "Perlisten"

        origin = origin[0].upper() + origin[1:] if origin else origin
        origin_long = origin_long[0].upper() + origin[1:] if origin_long and origin else origin_long

        if "sealed" in version:
            origin = origin + " (Sealed)"
            origin_long = origin_long + " (Sealed)"
            origin_short = origin_short + " (S)"
        elif "vented" in version:
            origin = origin + " (Vented)"
            origin_long = origin_long + " (Vented)"
            origin_short = origin_short + " (V)"
        elif "ported" in version:
            origin = origin + " (Ported)"
            origin_long = origin_long + " (Ported)"
            origin_short = origin_short + " (P)"

        if "grille-on" in version:
            origin = origin + " (Grille on)"
            origin_short = origin_short + " (Gon)"
            origin_long = origin_long + " (Grille on)"
        elif "no-grille" in version:
            origin = origin + " (Grille off)"
            origin_short = origin_short + " (Gof)"
            origin_long = origin_long + " (Grille off)"

        if "short-port" in version:
            origin = origin + " (Short Port)"
            origin_short = origin_short + " (sP)"
            origin_long = origin_long + " (Short Port)"
        elif "long-port" in version:
            origin = origin + " (Long Port)"
            origin_short = origin_short + " (lP)"
            origin_long = origin_long + " (Long Port)"

        if "bassreflex" in version:
            origin = origin + " (BR)"
            origin_short = origin_short + " (BR)"
            origin_long = origin_long + " (Bass Reflex)"
        elif "cardioid" in version:
            origin = origin + " (C)"
            origin_short = origin_short + " (C)"
            origin_long = origin_long + " (Cardiod)"

        if "fullrange" in version:
            origin = origin + " (FR)"
            origin_short = origin_short + " (FR)"
            origin_long = origin_long + " (Full Range)"
        elif "lowcut" in version:
            origin = origin + " (LC)"
            origin_short = origin_short + " (LC)"
            origin_long = origin_long + " (Low Cut)"

        if "active" in version:
            origin = origin + " (Act.)"
            origin_long = origin_long + " (Active)"
        elif "passive" in version:
            origin = origin + " (Pas.)"
            origin_long = origin_long + " (Passive)"

        if "horizontal" in version:
            origin = origin + " (Hor.)"
            origin_short = origin_short + " (Ho)"
            origin_long = origin_long + " (Horizontal)"
        elif "vertical" in version:
            origin = origin + " (Ver.)"
            origin_short = origin_short + " (Ve)"
            origin_long = origin_long + " (Vertical)"

        if "gll" in version:
            origin = origin + " (gll)"
            origin_short = origin_short + " (gll)"
            origin_long = origin_long + " (gll)"
        elif "klippel" in version:
            origin = origin + " (klippel)"
            origin_short = origin_short + " (nfs)"
            origin_long = origin_long + " (klippel)"

        if "wide" in version:
            origin = origin[: len(origin) - 1] + "/W)"
            origin_short = origin_short + " (/W)"
            origin_long = origin_long[: len(origin_long) - 1] + "/Wide)"
        elif "narrow" in version:
            origin = origin[: len(origin) - 1] + "/N)"
            origin_short = origin_short + " (/N)"
            origin_long = origin_long[: len(origin_long) - 1] + "/Narrow)"
        elif "medium" in version:
            origin = origin[: len(origin) - 1] + "/M)"
            origin_short = origin_short + " (/M)"
            origin_long = origin_long[: len(origin_long) - 1] + "/Medium)"

        if "Gecko" in version:
            origin = origin + " (Gecko)"
            origin_long = origin_long + " (Gecko)"
        elif "Tree" in version:
            origin = origin + " (Tree)"
            origin_long = origin_long + " (Tree)"
        elif "Pod" in version:
            origin = origin + " (Pod)"
            origin_long = origin_long + " (Pod)"

        ipattern = version.find("pattern")
        if ipattern != -1:
            sversion = version[ipattern + 8 :]
            times_pos = sversion.find("x")
            if times_pos != -1:
                vertical_angle = sversion[times_pos:]
                dash_pos = vertical_angle.find("-")
                if dash_pos == -1:
                    sversion_deg = (
                        " " + sversion[:times_pos] + "\u00ba" + sversion[times_pos:] + "\u00ba"
                    )
                else:
                    sversion_deg = (
                        " " + sversion[:times_pos] + "\u00ba" + vertical_angle[:dash_pos] + "\u00ba"
                    )
            else:
                sversion_deg = " " + sversion + "\u00ba"
            origin = origin + sversion_deg
            origin_long = origin_long + sversion_deg

        pos_version = re.search(r"-v([123456])-", version)
        if pos_version:
            vnum = pos_version.group(1)
            rest = version[pos_version.end() :]
            origin = origin + " (v" + vnum + "-" + rest + ")"
            origin_long = origin_long + " (v" + vnum + "-" + rest + ")"

        pos_counter = re.search(r"-v([123456])x", version)
        if pos_counter:
            vnum = pos_counter.group(1)
            origin = origin + " (" + vnum + "x)"
            origin_long = origin_long + " (" + vnum + "x)"

        pos_config = version.find("-configuration-")
        if pos_config != -1:
            config_str = version[pos_config + 15 :].replace("-", " ")
            origin = origin + " (" + config_str + ")"
            origin_long = origin_long + " (" + config_str + ")"

        degree_match = re.search(r"[-][0-9]+[-]deg(ree)?", origin)
        if degree_match:
            origin = re.sub(r"[-]deg(ree)?", "\u00b0", origin)
            origin_short = re.sub(r"[-]deg(ree)?", "\u00b0", origin_short)
            origin_long = re.sub(r"[-]deg(ree)?", "\u00b0", origin_long)

        for reviewer, img in _REVIEWER_ICONS:
            if reviewer in origin:
                origin_long = '<span class="icon-text"><span class="icon">{}</span><span>{}</span></span>'.format(
                    img, origin_long
                )
                break

        reviews.append(
            {
                "url": url,
                "origin": origin,
                "originShort": origin_short,
                "originLong": origin_long,
            }
        )
    return reviews


def is_short_reviews(context, reviews):
    max_len = 29
    total = 0
    for review in reviews:
        if review.get("origin"):
            total += len(review["origin"]) + 4
        else:
            total += 10
    return total < max_len


def sensitivity_html(context, stype, sensitivity):
    if stype == "active":
        return "Active"
    if sensitivity and float(sensitivity) != 0:
        return "Sensitivity: <b>{:.0f}</b>&nbsp;dB".format(float(sensitivity))
    return "Sensitivity: <b>?</b>&nbsp;dB"


def spl_html(context, splinfo, splvalue):
    if splinfo == "***" or splinfo == "0":
        return "SPL ? dB"
    return "{} SPL: <b>{}</b>&nbsp;dB".format(splinfo, splvalue)
