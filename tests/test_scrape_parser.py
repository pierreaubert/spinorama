# SPDX-License-Identifier: MIT
from __future__ import annotations

from textwrap import dedent

from metahint.parsers.html_parser import parse_spec_key_values
from metahint.parsers.normalizer import assemble_specs, normalize_raw_map


def test_parse_and_normalize_basic_spec_list() -> None:
    html = dedent(
        """
        <html><body>
          <ul class="specifications-list">
            <li><span class="name">Sensitivity (2.83V/1m)</span><span class="value">88dB</span></li>
            <li><span class="name">Frequency Response  (-3dB limits)</span><span class="value">38Hz - 38kHz</span></li>
            <li><span class="name">Overall Frequency Response</span><span class="value">30Hz - 50kHz</span></li>
            <li><span class="name">Recommended Amplifier Power</span><span class="value">50 - 300W</span></li>
            <li><span class="name">Minimum Impedance (ohms)</span><span class="value">3.6Ω</span></li>
            <li><span class="name">Product Dims W x H x D (Includes width of feet)</span><span class="value">320.7 x 1143.8 x 428.3mm<br/> 12.6 x 45 x 16.9 in</span></li>
            <li><span class="name">Product Weight (each)</span><span class="value">79.1 lbs/35.9 kg</span></li>
            <li><span class="name">UOM (Sold As)</span><span class="value">Each</span></li>
          </ul>
        </body></html>
        """
    )

    raw, _ = parse_spec_key_values(html)
    norm = normalize_raw_map(raw)
    specs = assemble_specs(norm, source_url="https://example.com/product")

    # Key expectations
    assert specs.sensitivity.value == 88
    assert specs.impedance["min_ohms"].value == 3.6

    dims_mm = specs.dimensions["mm"].value
    dims_in = specs.dimensions["in"].value
    assert dims_mm == {"w": 320.7, "h": 1143.8, "d": 428.3}
    assert dims_in == {"w": 12.6, "h": 45.0, "d": 16.9}

    weight_each = specs.weight["each"].value
    assert weight_each["lb"].value == 79.1
    assert weight_each["kg"].value == 35.9
