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


def eqtype2str(context, eq_type : str) -> str:
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
