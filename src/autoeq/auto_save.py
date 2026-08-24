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

import contextlib
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
import re
import pathlib

import plotly.io
from spinorama import logger, setup_logger
from spinorama.ltype import OptimResult
from spinorama.constant_paths import CPATH_DIST_SPEAKERS
from spinorama.misc import (
    graph_melt,
    measurements_complete_spl,
    measurements_complete_freq,
    sanitize_filename,
)
from spinorama.loaders.rew_eq import parse_eq_iir_rews
from spinorama.filters.peq import peq_format_apo, Peq
from spinorama.filters.scores import (
    scores_apply_filter,
    scores_print,
)
from spinorama.measurements import Measurements
from autoeq.auto_target import get_freq, get_target
from autoeq.auto_plot import graph_results as auto_graph_results
from autoeq.auto_strategy import optim_strategy


EQ_IMAGE_CACHE_VERSION = "eq-images-v1"


def _eq_image_cache_key(
    speaker_name: str, speaker_origin: str, optim_config: dict
) -> str:
    relevant_config = {
        key: value
        for key, value in optim_config.items()
        if key not in {"verbose", "level", "input_fingerprint"}
    }
    payload = json.dumps(relevant_config, sort_keys=True, default=str)
    return hashlib.sha256(
        f"{EQ_IMAGE_CACHE_VERSION}:{speaker_name}:{speaker_origin}:{payload}".encode("utf-8")
    ).hexdigest()


def _eq_image_cache_path(
    speaker_name: str, speaker_origin: str, optim_config: dict
) -> pathlib.Path:
    cache_key = _eq_image_cache_key(speaker_name, speaker_origin, optim_config)
    return pathlib.Path("build/eq-image-cache") / f"{cache_key}.json"


def _eq_images_up_to_date(
    speaker_name: str, speaker_origin: str, optim_config: dict
) -> bool:
    input_fingerprint = optim_config.get("input_fingerprint")
    if not input_fingerprint:
        return False
    cache_path = _eq_image_cache_path(speaker_name, speaker_origin, optim_config)
    try:
        with cache_path.open("r", encoding="utf-8") as cache_fd:
            cached = json.load(cache_fd)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return False
    if cached.get("input_fingerprint") != input_fingerprint:
        return False
    outputs = cached.get("outputs", [])
    if not outputs:
        return False
    return all(
        pathlib.Path(filename).is_file() and pathlib.Path(filename).stat().st_size > 0
        for filename in outputs
    )


def eq_images_up_to_date(
    speaker_name: str, speaker_origin: str, optim_config: dict
) -> bool:
    """Public fast-path check for callers that can avoid loading measurements."""
    return _eq_images_up_to_date(speaker_name, speaker_origin, optim_config)


def eq_images_cached_outputs(
    speaker_name: str, speaker_origin: str, optim_config: dict
) -> list[str]:
    """Return validated image outputs from one cache marker, if available."""
    if not _eq_images_up_to_date(speaker_name, speaker_origin, optim_config):
        return []
    cache_path = _eq_image_cache_path(speaker_name, speaker_origin, optim_config)
    try:
        with cache_path.open("r", encoding="utf-8") as cache_fd:
            return list(json.load(cache_fd)["outputs"])
    except (FileNotFoundError, OSError, json.JSONDecodeError, KeyError, TypeError):
        return []


def _save_eq_image_cache(
    speaker_name: str,
    speaker_origin: str,
    optim_config: dict,
    outputs: list[str],
) -> None:
    input_fingerprint = optim_config.get("input_fingerprint")
    if not input_fingerprint or not outputs:
        return
    cache_path = _eq_image_cache_path(speaker_name, speaker_origin, optim_config)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = cache_path.with_name(f".{cache_path.name}.tmp")
    temporary_path.write_text(
        json.dumps(
            {"input_fingerprint": input_fingerprint, "outputs": sorted(set(outputs))},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    os.replace(temporary_path, cache_path)


def get_previous_score(eq_name: str) -> None | float:
    previous_score = None
    if not os.path.exists(eq_name):
        return None

    with open(eq_name, "r", encoding="utf8") as read_fd:
        lines = read_fd.readlines()
        if len(lines) > 1:
            line_pref = lines[1]
            parsed = re.findall(r"[-+]?\d+(?:\.\d+)?", line_pref)
            if len(parsed) > 1:
                previous_score = float(parsed[1])
                logger.info("EQ prev_score %0.2f", previous_score)

    return previous_score


def write_eq_to_file(
    eq_dir: str,
    eq_name: str,
    speaker_name: str,
    speaker_origin: str,
    score: dict[str, float],
    auto_score: dict[str, float],
    auto_peq: Peq,
    optim_config: dict,
) -> None:
    comments = [f"EQ for {speaker_name} computed from {speaker_origin} data"]
    comments.append(
        "Preference Score {:2.2f} with EQ {:2.2f}".format(
            score.get("pref_score", -1000), auto_score.get("pref_score", -1000)
        )
    )

    version = optim_config["version"]
    comments += [
        f"Generated from https://github.com/pierreaubert/spinorama/generate_peqs.py v{version}",
        f"Dated: {datetime.today().strftime('%Y-%m-%d-%H:%M:%S')}",
        "",
    ]
    eq_apo = peq_format_apo("\n".join(comments), auto_peq)

    with open(eq_name, "w", encoding="utf8") as write_eq_fd:
        iir_txt = "iir.txt"
        iir_name = f"{eq_dir}/{iir_txt}"
        write_eq_fd.write(eq_apo)
        if not os.path.exists(iir_name):
            with contextlib.suppress(OSError):
                os.symlink("iir-autoeq.txt", iir_name)
            eq_conf = f"{eq_dir}/conf-autoeq.json"
            with open(eq_conf, "w", encoding="utf8") as write_conf_fd:
                conf_json = json.dumps(optim_config, indent=4)
                write_conf_fd.write(conf_json)


def print_auto_graphs_seq(
    speaker_name: str,
    speaker_origin: str,
    m: Measurements,
    auto_peq: Peq,
    auto_spin,
    auto_pir,
    score: dict[str, float],
    auto_score: dict[str, float],
    optim_config: dict,
) -> list[str]:
    curves = optim_config["curve_names"]
    if auto_peq is None or len(auto_peq) == 0:
        logger.debug("skipping printing graphs")
        return []

    data_frame, freq, auto_target = get_freq(m, optim_config)
    auto_target_interp = []
    for curve in curves:
        auto_target_interp.append(get_target(data_frame, freq, curve, optim_config))

        cea2034_melted = graph_melt(m.cea2034) if m.cea2034 is not None else None
        eir_melted = graph_melt(m.eir) if m.eir is not None else None
        graphs = auto_graph_results(
            speaker_name,
            speaker_origin,
            freq,
            auto_peq,
            auto_target,
            auto_target_interp,
            cea2034_melted,
            auto_spin,
            eir_melted,
            auto_pir,
            optim_config,
            score,
            auto_score,
        )

        # Collect images to write (png, jpg, webp) and batch write using plotly.io
        graphs_to_print: list = []
        filenames_to_print: list[str] = []
        outputs_to_cache: list[str] = []
        widths_to_print: list[int] = []
        heights_to_print: list[int] = []
        img_width: int | None = None
        img_height: int | None = None

        for name, graph in graphs:
            origin = speaker_origin
            if "Vendors-" in origin:
                origin = origin[8:]
            base_filename = "{}/{}/{}/filters_{}".format(
                CPATH_DIST_SPEAKERS, sanitize_filename(speaker_name), origin, name
            )
            if optim_config["output_dir"] and pathlib.Path(optim_config["output_dir"]).exists():
                base_filename = "{}/filters_{}".format(
                    pathlib.Path(optim_config["output_dir"]).resolve(), name
                )

            if optim_config["use_grapheq"]:
                grapheq_name = optim_config["grapheq_name"]
                short_name = grapheq_name.lower().replace(" ", "-")
                base_filename += short_name
            if optim_config["smoke_test"]:
                base_filename += "_smoketest"

            # Decide whether to write based on existing files and force flag
            force = not optim_config["generate_images_only"]

            for ext in (".json", ".png", ".jpg", ".webp"):
                filename = f"{base_filename}{ext}"
                outputs_to_cache.append(filename)
                # Ensure parent directory exists
                pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)

                needs_write = (
                    force
                    or not os.path.exists(filename)
                    or (os.path.exists(filename) and os.path.getsize(filename) == 0)
                )
                # print('1: {} {}'.format(filename, needs_write))
                if needs_write:
                    if ext == ".json":
                        content = graph.to_json()
                        with open(filename, "w", encoding="utf-8") as f_d:
                            f_d.write(content)
                    else:
                        # Use the first graph's dimensions
                        try:
                            img_width = int(graph.layout.width)
                            img_height = int(graph.layout.height)
                        except Exception:
                            # Fallback defaults if layout is missing dimensions
                            graph.layout.width = 800
                            graph.layout.height = 600
                        graphs_to_print.append(graph)
                        widths_to_print.append(img_width)
                        heights_to_print.append(img_height)
                        filenames_to_print.append(filename)
                    logger.debug("queueing graph %s", filename)

        # if len(filenames_to_print) > 0:
        #     try:
        #         plotly.io.write_images(
        #             fig=graphs_to_print,
        #             file=filenames_to_print,
        #             width=widths_to_print,
        #             height=heights_to_print,
        #         )
        #     except RuntimeError as rt:
        #         logger.error("writing image(s) crashed! %s", rt)

    return outputs_to_cache


def print_small_summary(
    speaker_name: str, score: dict[str, float], auto_score: dict[str, float]
) -> None:
    logger.info("%30s ---------------------------------------", speaker_name)
    if score is not None and auto_score is not None and "nbd_on_axis" in auto_score:
        logger.info(scores_print(score, auto_score))
        logger.info("----------------------------------------------------------------------")
        logger.info(
            "%+2.2f %+2.2f %s",
            score["pref_score"],
            auto_score["pref_score"],
            speaker_name,
        )


def build_eq_name(
    current_speaker_name: str,
    optim_config: dict,
) -> tuple[pathlib.Path, str]:
    eq_dir = pathlib.Path("datas/eq/{}".format(sanitize_filename(current_speaker_name)))
    if optim_config["output_dir"]:
        output_dir = pathlib.Path(optim_config["output_dir"])
        if output_dir.exists():
            eq_dir = output_dir.resolve()
    pathlib.Path(eq_dir).mkdir(parents=True, exist_ok=True)
    eq_name = "{}/iir-autoeq.txt".format(eq_dir)

    if optim_config["use_grapheq"]:
        grapheq_name = optim_config["grapheq_name"]
        short_name = grapheq_name.lower().replace(" ", "-")
        eq_name = "{}/iir-autoeq-{}.txt".format(eq_dir, short_name)

    return eq_dir, eq_name


def smoke_test_cea2034(
    current_speaker_name: str, current_speaker_origin: str, m: Measurements
) -> tuple[bool, tuple[str, OptimResult, list[float]]]:
    if m.cea2034 is None:
        # this should not happen
        log = logger.debug if current_speaker_origin == "Princeton" else logger.error
        log("%s %s doesn't have CEA2034 data", current_speaker_name, current_speaker_origin)
        return False, ("", (0, 0, 0), [])
    return True, ("", (0, 0, 0), [])


def optim_save_peq(
    current_speaker_name: str,
    current_speaker_origin: str,
    m: Measurements,
    optim_config: dict,
) -> tuple[bool, tuple[str, OptimResult, list[float]]]:
    """Compute and then save PEQ for this speaker"""
    eq_dir, eq_name = build_eq_name(current_speaker_name, optim_config)

    if (
        optim_config["generate_images_only"]
        and not optim_config["force"]
        and _eq_images_up_to_date(current_speaker_name, current_speaker_origin, optim_config)
    ):
        logger.debug("Skipping unchanged EQ images for %s", current_speaker_name)
        return False, ("", (0, 0, 0), [])

    if (
        not optim_config["force"]
        and os.path.exists(eq_name)
        and not optim_config["generate_images_only"]
    ):
        if optim_config["verbose"]:
            logger.info("eq %s already exist!", eq_name)
        logger.debug("Skipping %s since EQ already exist!", current_speaker_name)
        return False, ("", (0, 0, 0), [])

    # do we have CEA2034 data (temporary test, should be much smarter)
    smoke_test, smoke_empty = smoke_test_cea2034(current_speaker_name, current_speaker_origin, m)
    if not smoke_test:
        return smoke_test, smoke_empty

    # do we have full H/V sweep data?
    use_score = (
        m.h_spl is not None
        and m.v_spl is not None
        and measurements_complete_spl(m.h_spl, m.v_spl)
        and measurements_complete_freq(m.h_spl, m.v_spl)
    )
    # maybe we only have partial data but enough to compute the Spin
    if not use_score and m.cea2034 is not None:
        use_score = True

    # don't optimise below the minimum freq found in measurements
    if current_speaker_origin == "Princeton":
        # we have SPL H and V but they are only above 500Hz so score computation fails.
        use_score = False
        # set EQ min to 500
        optim_config["freq_reg_min"] = max(500, optim_config["freq_reg_min"])
    elif m.cea2034 is not None:
        min_freq = max(20, m.cea2034.Freq.to_numpy().min())
        optim_config["freq_reg_min"] = max(min_freq, optim_config["freq_reg_min"])

    score: dict[str, float] = {}
    if use_score:
        logger.debug("Computing init score for %s", current_speaker_name)
        _, _, score = scores_apply_filter(m, [])

    # compute pref score from speaker if possible
    auto_score: dict[str, float] = {}
    auto_results: OptimResult = (0, 0, 0)
    if not optim_config["generate_images_only"]:
        logger.debug("Calling strategy for %s", current_speaker_name)
        auto_status, (auto_score, auto_results, auto_peq, auto_config) = optim_strategy(
            current_speaker_name, m, optim_config, use_score
        )
        if auto_status is False:
            logger.error("EQ generation failed for %s", current_speaker_name)
            return False, ("", (0, 0, 0), [])
        optim_config = deepcopy(auto_config)
    else:
        # generate images only, add some default
        auto_score["pref_score"] = 1000.0
        optim_config["target_min_freq"] = 20
        optim_config["curve_names"] = ["Listening Window"]

    # do we have a previous score?
    previous_score: float = get_previous_score(eq_name)

    skip_write_eq = False
    if (
        optim_config["smoke_test"]
        or (
            use_score
            and previous_score is not None
            and previous_score > auto_score.get("pref_score", 1000)
        )
        or optim_config["generate_images_only"]
    ):
        skip_write_eq = True

    if not skip_write_eq:
        write_eq_to_file(
            eq_dir,
            eq_name,
            current_speaker_name,
            current_speaker_origin,
            score,
            auto_score,
            auto_peq,
            optim_config,
        )

    # compute new score with this PEQ
    auto_spin = None
    auto_pir = None
    scores = (-1000, -1000)
    if use_score or optim_config["generate_images_only"]:
        if (
            previous_score is not None and previous_score > auto_score["pref_score"]
        ) or optim_config["generate_images_only"]:
            if os.path.exists(eq_name):
                auto_peq = parse_eq_iir_rews(eq_name, 48000)
            else:
                fallback_eq = "{}/iir.txt".format(eq_dir)
                auto_peq = parse_eq_iir_rews(fallback_eq, 48000)

        if (
            previous_score is not None
            and previous_score < auto_score["pref_score"]
            and optim_config["verbose"]
        ):
            print("Current run is not a winner:")
            print_small_summary(current_speaker_name, score, auto_score)

        auto_spin, auto_pir, auto_score = scores_apply_filter(m, auto_peq)
        if score is not None:
            scores = [
                score.get("pref_score", -1000),
                auto_score.get("pref_score", -1000) if auto_score else -1000,
            ]
        if (
            previous_score is not None
            and auto_score is not None
            and previous_score > auto_score.get("pref_score", -1000)
        ):
            scores[1] = previous_score

    if auto_spin is None or auto_pir is None:
        logger.error("Spin or PIR is none %s %s", current_speaker_name, current_speaker_origin)
    else:
        # print new best peq or re-print previous one
        image_outputs = print_auto_graphs_seq(
            current_speaker_name,
            current_speaker_origin,
            m,
            auto_peq,
            auto_spin,
            auto_pir,
            score,
            auto_score,
            optim_config,
        )
        if optim_config["generate_images_only"]:
            _save_eq_image_cache(
                current_speaker_name,
                current_speaker_origin,
                optim_config,
                image_outputs,
            )

    if optim_config["verbose"]:
        print_small_summary(current_speaker_name, score, auto_score)

    return True, (current_speaker_name, auto_results, scores)
