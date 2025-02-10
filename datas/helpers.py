# -*- coding: utf-8 -*-

from . import Measurement, Speaker
from spinorama import logger


def measurement2distance(speaker_name: str, m: Measurement) -> float:
    d = 1.0
    if "data_acquisition" in m and "distance" in m["data_acquisition"]:
        try:
            d = float(m["data_acquisition"]["distance"])
        except ValueError:
            logger.warning(
                "Found a measurement distance for %s but it is not a float", speaker_name
            )
            return -1.0
    return d


def measurement_valid_freq(speaker_name: str, m: Measurement) -> tuple[float, float]:
    min_valid_freq = 20.0
    max_valid_freq = 20000.0
    if "data_acquisition" in m and "min_valid_freq" in m["data_acquisition"]:
        try:
            freq = float(m["data_acquisition"]["min_valid_freq"])
        except ValueError:
            logger.warning("Found a min_valid_freq for %s but it is not a float", speaker_name)
        else:
            min_valid_freq = freq
    if "data_acquisition" in m and "max_valid_freq" in m["data_acquisition"]:
        try:
            freq = float(m["data_acquisition"]["max_valid_freq"])
        except ValueError:
            logger.warning("Found a max_valid_freq for %s but it is not a float", speaker_name)
        else:
            max_valid_freq = freq
    return min_valid_freq, max_valid_freq


def speaker2unitprice(s: Speaker) -> float:
    price = s.get("price", -1.0)
    fprice = -1
    try:
        fprice = float(price)
    except ValueError:
        logger.warning("Found a price  for %s %s but it is not a float", s["brand"], s["model"])
        return -1.0
    amount = s.get("amount", "pair")
    if amount == "pair":
        return fprice / 2.0
    return fprice
