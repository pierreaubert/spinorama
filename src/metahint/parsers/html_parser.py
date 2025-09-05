# SPDX-License-Identifier: MIT
from __future__ import annotations

from bs4 import BeautifulSoup
from typing import Dict, List, Tuple


def _clean_text(s: str) -> str:
    return " ".join(s.replace("\xa0", " ").split()).strip()


def parse_spec_key_values(html: str) -> Tuple[Dict[str, str], List[str]]:
    """Parse common spec sections into a raw key->value dict.

    Heuristics target structures like:
      <ul class="specifications-list">
        <li>
          <span class="name">Sensitivity (2.83V/1m)</span>
          <span class="value">88dB</span>
        </li>
      </ul>
    Returns a tuple of (mapping, notes).
    """
    soup = BeautifulSoup(html, "lxml")
    out: Dict[str, str] = {}
    notes: List[str] = []

    # Find headings that suggest specs
    candidates = soup.select(
        ".specifications-list, ul.specs, ul.specifications, div.specifications, section#specifications"
    )
    if not candidates:
        # Fallback: try any ULs containing spans with name/value
        candidates = [
            ul
            for ul in soup.find_all("ul")
            if ul.find("span", class_="name") and ul.find("span", class_="value")
        ]

    for block in candidates:
        for li in block.find_all("li"):
            name_el = li.find(class_="name")
            value_el = li.find(class_="value")
            if name_el and value_el:
                k = _clean_text(name_el.get_text(" "))
                v = _clean_text(value_el.get_text(" "))
                if k:
                    out[k] = v
            else:
                # Try definition list style
                dt = li.find("dt")
                dd = li.find("dd")
                if dt and dd:
                    k = _clean_text(dt.get_text(" "))
                    v = _clean_text(dd.get_text(" "))
                    if k:
                        out[k] = v
    if not out:
        notes.append("no_spec_list_found")
    return out, notes
