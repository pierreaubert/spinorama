# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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

from spinorama.ltype import Peq, FloatVector1D
from spinorama.auto_grapheq import optim_grapheq
from spinorama.auto_greedy import optim_greedy
from spinorama.auto_refine import optim_refine


def optim_multi_steps(
    speaker_name: str,
    df_speaker: dict,
    freq: FloatVector1D,
    auto_target: list[FloatVector1D],
    auto_target_interp: list[FloatVector1D],
    optim_config: dict,
    use_score,
) -> tuple[list[tuple[int, float, float]], Peq]:
    """Implement multi steps optimisation:
    Start with a greedy approach then add another algorithm to optimise for score
    """
    if optim_config["use_grapheq"] is True:
        return optim_grapheq(
            speaker_name,
            df_speaker,
            freq,
            auto_target,
            auto_target_interp,
            optim_config,
            use_score,
        )

    greedy_results, greedy_peq = optim_greedy(
        speaker_name,
        df_speaker,
        freq,
        auto_target,
        auto_target_interp,
        optim_config,
        use_score,
    )

    if not use_score or not optim_config["second_optimiser"]:
        return greedy_results, greedy_peq

    return optim_refine(
        speaker_name,
        df_speaker,
        freq,
        auto_target,
        auto_target_interp,
        optim_config,
        greedy_results,
        greedy_peq,
    )
