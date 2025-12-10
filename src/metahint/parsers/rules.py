# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FieldRule:
    canonical: str
    pattern: re.Pattern[str]


# Heuristic label→canonical mapping rules
RULES: list[FieldRule] = [
    FieldRule(
        canonical="sensitivity_db_2p83v_1m",
        pattern=re.compile(r"^sensitivity", re.I),
    ),
    FieldRule(
        canonical="min_impedance_ohms",
        pattern=re.compile(r"^(minimum|min)\s+impedance|\(ohms\)$", re.I),
    ),
    FieldRule(
        canonical="overall_freq_hz",
        pattern=re.compile(r"overall\s*frequency\s*response", re.I),
    ),
    FieldRule(
        canonical="minus3db_freq_hz",
        pattern=re.compile(r"frequency\s*response.*-3\s*db|frequency\s*response.*\(-3db", re.I),
    ),
    FieldRule(
        canonical="overall_freq_hz",
        pattern=re.compile(r"^frequency\s*response$", re.I),
    ),
    FieldRule(
        canonical="amplifier_power_recommended_w",
        pattern=re.compile(r"recommended\s*amplifier\s*power", re.I),
    ),
    FieldRule(
        canonical="dims",
        pattern=re.compile(r"product\s*dims|dimensions", re.I),
    ),
    FieldRule(
        canonical="weight_each",
        pattern=re.compile(r"product\s*weight\s*\(each\)", re.I),
    ),
    FieldRule(
        canonical="uom_sold_as",
        pattern=re.compile(r"uom\s*\(sold\s*as\)", re.I),
    ),
]


def canonicalize(label: str) -> Optional[str]:
    for rule in RULES:
        if rule.pattern.search(label.strip()):
            return rule.canonical
    return None
