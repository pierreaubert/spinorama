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


def speaker2unitprice(s: Speaker) -> float:
    price = s["price"]
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
