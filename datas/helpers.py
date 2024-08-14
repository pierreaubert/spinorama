# -*- coding: utf-8 -*-

from . import Measurement, Speaker


def measurement2distance(m: Measurement) -> float:
    if "data_acquisition" in m and "distance" in m["data_acquisition"]:
        return m["data_acquisition"]["distance"]
    return 1.0


def speaker2unitprice(s: Speaker) -> float:
    price = s["price"]
    fprice = -1
    try:
        fprice = float(price)
    except ValueError:
        return fprice
    amount = s.get("amount", "pair")
    if amount == "pair":
        return fprice / 2.0
    return fprice
