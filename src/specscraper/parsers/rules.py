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
        canonical="sensitivity",
        pattern=re.compile(r"^sensitivity\s*m", re.I),
    ),
    FieldRule(
        canonical="min_impedance_ohms",
        pattern=re.compile(r"^(minimum|min)\s+impedance|\(ohms\)$", re.I),
    ),
    FieldRule(
        canonical="dims",
        pattern=re.compile(r"product\s*dims|dimensions", re.I),
    ),
    FieldRule(
        canonical="weight_each",
        pattern=re.compile(r"product\s*weight\s*\(each\)", re.I),
    ),
]


def canonicalize(label: str) -> Optional[str]:
    for rule in RULES:
        if rule.pattern.search(label.strip()):
            return rule.canonical
    return None
