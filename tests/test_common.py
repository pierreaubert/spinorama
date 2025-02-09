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
from spinorama.misc import measurements_complete_freq, measurements_complete_spl, graph_melt, graph_unmelt, measurements_missing_angles
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
    #
    _, (h, v) = parse_graphs_speaker_klippel(
        "datas/measurements", "Neumann", "Neumann KH 80", "asr-v3-20200711", None
    )
    full = measurements_complete_spl(h, v) and measurements_complete_freq(h, v)
    if not full:
        print(measurements_missing_angles(h,v))
    dfs["klippel"] = {
        "full": full,
        "graphs": filter_graphs("Neumann KH 80", h, v, MEAN_MIN, MEAN_MAX, "klippel", 1)
    }
    #
    _, (h, v) = parse_graphs_speaker_princeton(
        "datas/measurements", "Genelec", "Genelec 8351A", "princeton", None
    )
    full = measurements_complete_spl(h, v) and measurements_complete_freq(h, v)
    dfs["princeton"] = {
        "full": full,
        "graphs": filter_graphs(
            "Genelec 8351A", h, v, MEAN_MIN, MEAN_MAX, "princeton", 1
        )
    }
    #
    _, (h, v) = parse_graphs_speaker_gll_hv_txt(
        "datas/measurements", "RCF ART 708-A MK4", "vendor-pattern-90x70"
    )
    full = measurements_complete_spl(h, v) and measurements_complete_freq(h, v)
    dfs["spl_hv"] = {
        "full": full,
        "graphs": filter_graphs(
            "RCF ART 708-A MK4", h, v, MEAN_MIN, MEAN_MAX, "gll_hv_txt", 10
        )
    }
    #
    _, (h, v) = parse_graphs_speaker_spl_hv_txt(
        "datas/measurements", "Andersson", "Andersson HIS 2.1", "misc-ageve"
    )
    h2, v2 = symmetrise_speaker_measurements(h, v, "vertical")
    full = measurements_complete_spl(h2, v2) and measurements_complete_freq(h2, v2)
    dfs["gll_hv"] = {
        "full": full,
        "graphs": filter_graphs(
            "Andersson HIS 2.1", h, v, MEAN_MIN, MEAN_MAX, "spl_hv_txt", 1
        )
    }

    return dfs


def parse_partial_each_format():
    dfs = {}

    speaker_name = "BIC America Venturi DV62si"
    _, (title, df_melted) = parse_graphs_speaker_rew_text_dump(
        "datas/measurements",
        "BIC America",
        speaker_name,
        "",
        "vendor",
    )
    df_unmelted = graph_melt(unify_freq(df_melted))
    df_full = spin_compute_di_eir(speaker_name, title, df_unmelted)
    df_filtered = filter_graphs_partial(df_full, "rew_text_dump", 1.0)
    dfs["rew_text_dump"] = df_filtered

    speaker_name = "RBH Sound R-5"
    _, (title, df_melted) = parse_graphs_speaker_webplotdigitizer(
        "datas/measurements",
        "RBH Sound",
        speaker_name,
        "",
        "misc-audioholics",
    )
    df_unmelted = graph_unmelt(df_melted)
    df_full = spin_compute_di_eir(speaker_name, title, df_unmelted)
    df_filtered = filter_graphs_partial(df_full, "webplotdigitizer", 1.0)
    dfs["webplotdigitizer"] = df_filtered

    return dfs

class SpinoramaLoaderCommon(unittest.TestCase):

    def test_full(self):
        measurements = parse_full_each_format()
        for k, m in measurements.items():
            ln = len(m["graphs"])
            print(k, m["full"], ln, m["graphs"].keys())
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

