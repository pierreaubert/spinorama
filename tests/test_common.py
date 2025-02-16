# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import unittest
from spinorama.constant_paths import MEAN_MIN, MEAN_MAX
from spinorama.misc import (
    measurements_complete_freq,
    measurements_complete_spl,
    graph_melt,
    graph_unmelt,
    measurements_missing_angles,
)
from spinorama.compute_misc import unify_freq

from spinorama.load_klippel import parse_graphs_speaker_klippel
from spinorama.load_princeton import parse_graphs_speaker_princeton
from spinorama.load_spl_hv_txt import parse_graphs_speaker_spl_hv_txt
from spinorama.load_gll_hv_txt import parse_graphs_speaker_gll_hv_txt
from spinorama.load_rew_text_dump import parse_graphs_speaker_rew_text_dump
from spinorama.load_webplotdigitizer import parse_graphs_speaker_webplotdigitizer
from spinorama.load import (
    filter_graphs,
    filter_graphs_partial,
    spin_compute_di_eir,
    symmetrise_speaker_measurements,
)


EXPECTED_FULL_SET = set(
    [
        "SPL Horizontal",
        "SPL Horizontal_unmelted",
        "SPL Horizontal_normalized_unmelted",
        "SPL Vertical",
        "SPL Vertical_unmelted",
        "SPL Vertical_normalized_unmelted",
        "sensitivity",
        "sensitivity_distance",
        "sensitivity_1m",
        "Early Reflections_unmelted",
        "Early Reflections",
        "Horizontal Reflections_unmelted",
        "Horizontal Reflections",
        "Vertical Reflections_unmelted",
        "Vertical Reflections",
        "Estimated In-Room Response_unmelted",
        "Estimated In-Room Response",
        "Estimated In-Room Response Normalized_unmelted",
        "Estimated In-Room Response Normalized",
        "On Axis_unmelted",
        "On Axis",
        "CEA2034_unmelted",
        "CEA2034",
        "CEA2034 Normalized_unmelted",
        "CEA2034 Normalized",
    ]
)

EXPECTED_LIMITED_SET = set(
    [
        "SPL Horizontal",
        "SPL Horizontal_unmelted",
        "SPL Horizontal_normalized_unmelted",
        "SPL Vertical",
        "SPL Vertical_unmelted",
        "SPL Vertical_normalized_unmelted",
        "sensitivity",
        "sensitivity_distance",
        "sensitivity_1m",
        "On Axis_unmelted",
        "On Axis",
    ]
)

EXPECTED_PARTIAL_SET = set(
    [
        "On Axis",
        "On Axis_unmelted",
        "CEA2034",
        "CEA2034_unmelted",
        "CEA2034 Normalized",
        "CEA2034 Normalized_unmelted",
        "sensitivity",
        "sensitivity_distance",
        "sensitivity_1m",
        "Estimated In-Room Response",
        "Estimated In-Room Response_unmelted",
        "Estimated In-Room Response Normalized_unmelted",
        "Estimated In-Room Response Normalized",
    ]
)


def parse_full_each_format():
    dfs = {}
    # standard klippel measurement
    speaker_name = "Neumann KH 80"
    speaker_version = "asr-v3-20200711"
    _, (h, v) = parse_graphs_speaker_klippel(
        "datas/measurements", "Neumann", speaker_name, speaker_version, None
    )
    full = measurements_complete_spl(h, v) and measurements_complete_freq(h, v)
    dfs["klippel"] = {
        "speaker_name": speaker_name,
        "speaker_version": speaker_version,
        "full": full,
        "h_spl": h,
        "v_spl": v,
        "graphs": filter_graphs("Neumann KH 80", h, v, MEAN_MIN, MEAN_MAX, "klippel", 1),
    }
    # princeton data, no data below 500hz, horizontal symmetry, 1m
    speaker_name = "Genelec 8351A"
    speaker_version = "princeton"
    _, (h, v) = parse_graphs_speaker_princeton(
        "datas/measurements", "Genelec", speaker_name, speaker_version, "None"
    )
    h2, v2 = symmetrise_speaker_measurements(h, v, "horizontal")
    full = measurements_complete_spl(h2, v2) and measurements_complete_freq(h2, v2)
    dfs["princeton"] = {
        "speaker_name": speaker_name,
        "speaker_version": speaker_version,
        "full": full,
        "h_spl": h2,
        "v_spl": v2,
        "graphs": filter_graphs("Genelec 8351A", h2, v2, MEAN_MIN, MEAN_MAX, "princeton", 1),
    }
    # standard gll file, distance is 10m
    speaker_name = "RCF ART 708-A MK4"
    speaker_version = "vendor-pattern-90x70"
    _, (h, v) = parse_graphs_speaker_gll_hv_txt("datas/measurements", speaker_name, speaker_version)
    full = measurements_complete_spl(h, v) and measurements_complete_freq(h, v)
    dfs["spl_hv"] = {
        "speaker_name": speaker_name,
        "speaker_version": speaker_version,
        "full": full,
        "h_spl": h,
        "v_spl": v,
        "graphs": filter_graphs("RCF ART 708-A MK4", h, v, MEAN_MIN, MEAN_MAX, "gll_hv_txt", 10),
    }
    # standard spl file, vertical symmetry
    speaker_name = "Andersson HIS 2.1"
    speaker_version = "misc-ageve"
    _, (h, v) = parse_graphs_speaker_spl_hv_txt(
        "datas/measurements",
        "Andersson",
        speaker_name,
        speaker_version,
    )
    h2, v2 = symmetrise_speaker_measurements(h, v, "vertical")
    full = measurements_complete_spl(h2, v2) and measurements_complete_freq(h2, v2)
    dfs["gll_hv"] = {
        "speaker_name": speaker_name,
        "speaker_version": speaker_version,
        "full": full,
        "h_spl": h2,
        "v_spl": v2,
        "graphs": filter_graphs("Andersson HIS 2.1", h2, v2, MEAN_MIN, MEAN_MAX, "spl_hv_txt", 1),
    }
    return dfs


def parse_partial_each_format():
    dfs = {}
    # rew text dump
    speaker_name = "BIC America Venturi DV62si"
    speaker_version = "vendor"
    _, (title, df_melted) = parse_graphs_speaker_rew_text_dump(
        "datas/measurements",
        "BIC America",
        speaker_name,
        "",
        speaker_version,
    )
    df_unmelted = graph_melt(unify_freq(df_melted))
    df_full = spin_compute_di_eir(speaker_name, title, df_unmelted)
    df_filtered = filter_graphs_partial(df_full, "rew_text_dump", 1.0)
    dfs["rew_text_dump"] = df_filtered

    # webplotdigitizer
    speaker_name = "RBH Sound R-5"
    speaker_version = "misc-audioholics"
    _, (title, df_melted) = parse_graphs_speaker_webplotdigitizer(
        "datas/measurements",
        "RBH Sound",
        speaker_name,
        "",
        speaker_version,
    )
    df_unmelted = graph_unmelt(df_melted)
    df_full = spin_compute_di_eir(speaker_name, title, df_unmelted)
    df_filtered = filter_graphs_partial(df_full, "webplotdigitizer", 1.0)
    dfs["webplotdigitizer"] = df_filtered

    return dfs


class SpinoramaLoaderCommon(unittest.TestCase):
    def test_full(self):
        measurements = parse_full_each_format()
        for m in measurements.values():
            ln = len(m["graphs"])
            if m["full"]:
                self.assertEqual(len(m["graphs"].keys()), 25)
            else:
                self.assertEqual(len(m["graphs"].keys()), 11)

    def test_partial(self):
        measurements = parse_partial_each_format()
        for m in measurements.values():
            self.assertEqual(len(m.keys()), 13)


if __name__ == "__main__":
    unittest.main()
