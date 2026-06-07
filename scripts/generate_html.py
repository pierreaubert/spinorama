#!/usr/bin/env python3
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

from glob import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

import argparse

from mako.lookup import TemplateLookup

from datas.metadata import speakers_info as extradata
from generate_common import (
    args2level,
    get_custom_logger,
    find_metadata_file,
    find_metadata_chunks,
    sort_metadata_per_score,
    sort_metadata_per_date,
)

import spinorama.constant_paths as cpaths
from spinorama.misc import need_update, sanitize_filename, write_if_different


def find_original_speaker_name(sanitized_name):
    """Find original speaker name from metadata given a sanitized filesystem name."""
    for speaker_name in extradata:
        if sanitize_filename(speaker_name) == sanitized_name:
            return speaker_name
    return None


SITEPROD = "https://www.spinorama.org"
SITEDEV = "https://dev.spinorama.org"
CACHE_VERSION = "v5"


def get_files(dir: str, ext: str) -> list[str]:
    """return a list of files matching the extension in a directory, results are stripped of paths and extensions"""
    files = []
    filenames = glob("{}/*.{}".format(dir, ext))
    for filename in filenames:
        if not os.path.isfile(filename):
            continue
        files.append(os.path.basename(filename).split(".")[-2])
    return files


def get_versions(filename: str) -> dict[str, str]:
    """get the current versions for some js libraries"""
    versions = {}
    with open(filename, "r") as fd:
        lines = fd.readlines()
        for line in lines:
            tokens = line[:-1].split("=")
            if len(tokens) != 2:
                continue
            if not (tokens[0].isalpha() and tokens[0].isupper()):
                continue
            numbers = tokens[1].split(".")
            if not (
                len(numbers) == 3
                and numbers[0].isdigit()
                and numbers[1].isdigit()
                and numbers[2].isdigit()
            ):
                continue
            versions[tokens[0]] = tokens[1]
    versions["CACHE"] = CACHE_VERSION
    # usefull when debugging FUSE itself, waiting for patches to be included post 7.0.0
    # versions["FUSE"] += '-pa2'
    # print(versions)
    return versions


def adapt_imports(jscode, versions: dict[str, str], js_files: list[str], mini: str):
    """ " replace import statements

    The source code is compatible with node / vite / vitess.
    The production code need to be browser compatible.

    Local js files go to /js and libraries go to /js3rd.

    This is very very basic.
    """
    replacements = [
        (" from 'fuse.js';", " from '/js3rd/fuse-{}.min.mjs';".format(versions["FUSE"])),
        (
            " from 'handlebars.js';",
            " from '/js3rd/handlebars-{}.min.js';".format(versions["HANDLEBARS"]),
        ),
        (
            "import Plotly from 'plotly.js-dist-min';",
            "",  # because module support is complicated :(
        ),
    ]
    re_replacements = [
        (
            r"}} from '\.\/({})\.js';".format("|".join(js_files)),
            r"}} from '/js/\1-{}{}.js';".format(CACHE_VERSION, mini),
        ),
    ]
    code = jscode
    for str_from, str_to in replacements:
        code = code.replace(str_from, str_to)
    for re_from, re_to in re_replacements:
        code = re.sub(re_from, re_to, code)

    return code


FREQ_FILTER = [
    "CEA2034",
    "CEA2034 Normalized",
    "On Axis",
    "Early Reflections",
    "Estimated In-Room Response",
    "Horizontal Reflections",
    "Vertical Reflections",
    "SPL Horizontal",
    "SPL Vertical",
    "SPL Horizontal Normalized",
    "SPL Vertical Normalized",
]

CONTOUR_FILTER = [
    "SPL Horizontal Contour",
    "SPL Vertical Contour",
    "SPL Horizontal Contour Normalized",
    "SPL Vertical Contour Normalized",
    "SPL Horizontal Contour 3D",
    "SPL Vertical Contour 3D",
    "SPL Horizontal Contour Normalized 3D",
    "SPL Vertical Contour Normalized 3D",
]

RADAR_FILTER = [
    "SPL Horizontal Radar",
    "SPL Vertical Radar",
]


def generate_measurement(
    dataframe,
    meta,
    site,
    use_search,
    versions,
    speaker_name,
    origins,
    speaker_html,
    graph_html,
    origin,
    measurements,
    key,
    dfs,
):
    logger.debug("generate %s %s %s", speaker_name, origin, key)
    freq = {k: dfs[k] for k in FREQ_FILTER if k in dfs}
    contour = {k: dfs[k] for k in CONTOUR_FILTER if k in dfs}
    radar = {k: dfs[k] for k in RADAR_FILTER if k in dfs}
    # eq
    eq = None
    if key != "default_eq":
        eq_filter = [
            "ref_vs_eq",
        ]
        # TODO
        eq = {k: dfs[k] for k in eq_filter if k in dfs}
    # get index.html filename
    dirname = "{}/{}/".format(cpaths.CPATH_DIST_SPEAKERS, sanitize_filename(speaker_name))
    if origin in ("ASR", "Princeton", "ErinsAudioCorner", "Misc"):
        dirname += origin
    else:
        dirname += meta[speaker_name]["brand"]
    index_name = "{0}/index_{1}.html".format(dirname, key)

    # ensure directory exists
    os.makedirs(os.path.dirname(index_name), mode=0o755, exist_ok=True)

    # write index.html
    logger.info("Writing %s for %s", index_name, speaker_name)
    speaker_content = speaker_html.render(
        speaker=speaker_name,
        g_freq=freq,
        g_contour=contour,
        g_radar=radar,
        g_key=key,
        g_eq=eq,
        meta=meta,
        origin=origin,
        site=site,
        use_search=use_search,
        min=".min" if flag_optim else "",
        versions=versions,
    )
    meta_file, eq_file = find_metadata_file()
    index_deps = [
        "./src/website/speaker.html",
        "./src/website/speaker_desc.html",
        "./src/website/utils.py",
        "./datas/metadata.py",
        meta_file,
        eq_file,
        *find_metadata_chunks().values(),
        *glob("./src/website/*.js"),
    ]
    index_force = need_update(index_name, index_deps)
    write_if_different(speaker_content, index_name, index_force)

    # write a small file per graph to render the json generated by Vega
    for kind in [freq, contour, radar]:
        for graph_name in kind:
            graph_filename = "{0}/{1}/{2}.html".format(dirname, key, graph_name)
            logger.info("Writing %s/%s for %s", key, graph_filename, speaker_name)
            graph_content = graph_html.render(
                speaker=speaker_name,
                graph=graph_name,
                meta=meta,
                site=site,
                min=".min" if flag_optim else "",
                versions=versions,
            )
            graph_deps = [
                *glob("./datas/measurements/{}/{}/*.*".format(sanitize_filename(speaker_name), key)),
                *glob("./src/spinorama/*.py"),
            ]
            graph_force = need_update(graph_filename, graph_deps)
            os.makedirs(os.path.dirname(graph_filename), mode=0o755, exist_ok=True)
            write_if_different(graph_content, graph_filename, graph_force)


def generate_speaker(
    dataframe,
    meta,
    site,
    use_search,
    versions,
    speaker_name,
    origins,
    speaker_html,
    graph_html,
):
    for origin, measurements in origins.items():
        for key, dfs in measurements.items():
            try:
                # print('DEBUG: '+speaker_name+' origin='+origin+' version='+key)
                generate_measurement(
                    dataframe,
                    meta,
                    site,
                    use_search,
                    versions,
                    speaker_name,
                    origins,
                    speaker_html,
                    graph_html,
                    origin,
                    measurements,
                    key,
                    dfs,
                )
            except KeyError as key_error:
                print(
                    "generate_speaker: a file per speaker for {} failed with {}".format(
                        speaker_name, key_error
                    )
                )
                print("Maybe you forgot to cache the computations? Try running:")
                print("./scripts/generate_graphs.py --speaker='{}' --update-cache".format(speaker_name))
                print("./scripts/generate_meta.py")


def generate_speakers(mako, dataframe, meta, site, use_search, versions):
    """For each speaker, generates a set of HTML files driven by templates"""
    speaker_html = mako.get_template("speaker.html")
    graph_html = mako.get_template("graph.html")
    for speaker_name, origins in dataframe.items():
        logger.debug("html generation for speaker_name %s", speaker_name)
        if speaker_name in extradata and extradata[speaker_name].get("skip", False):
            logger.debug("skipping %s", speaker_name)
            continue
        generate_speaker(
            dataframe,
            meta,
            site,
            use_search,
            versions,
            speaker_name,
            origins,
            speaker_html,
            graph_html,
        )

    return 0


def main():
    # create some directories
    for dir in (
        cpaths.CPATH_DIST,
        cpaths.CPATH_DIST_JS,
        cpaths.CPATH_DIST_JS3RD,
        cpaths.CPATH_DIST_JSON,
        cpaths.CPATH_DIST_CSS,
    ):
        os.makedirs(dir, mode=0o755, exist_ok=True)

    # load all metadata from generated json file
    metadata_json_filename, eqdata_json_filename = find_metadata_file()
    metadata_json_chunks = find_metadata_chunks()
    for radical, json_check in (
        ("metadata", metadata_json_filename),
        ("eqdata", eqdata_json_filename),
    ):
        if json_check is None:
            logger.error("Cannot find %s, you should run ./scripts/generate_meta.py again!", radical)
            sys.exit(1)

    meta = None
    with open(metadata_json_filename, "r") as f:
        meta = json.load(f)

    with open(eqdata_json_filename, "r") as f:
        meta_eqs = json.load(f)
        for k, v in meta_eqs.items():
            if "eqs" in v:
                meta[k]["eqs"] = v["eqs"]

    # load versions for various css and js files
    versions = get_versions("{}/update_3rdparties.sh".format(cpaths.CPATH_SCRIPTS))

    # get a list of js files
    jsfiles = get_files(cpaths.CPATH_WEBSITE, "js")

    # only build a dictionnary will all graphs
    main_df = {}
    speakers = glob("{}/*".format(cpaths.CPATH_DIST_SPEAKERS))
    for speaker in speakers:
        if not os.path.isdir(speaker):
            continue
        # humm annoying
        speaker_name = speaker.replace(cpaths.CPATH_DIST_SPEAKERS + "/", "")
        if speaker_name in ("score", "assets", "stats", "compare", "logos", "pictures"):
            continue
        # Map sanitized filesystem name back to original metadata name
        original_name = find_original_speaker_name(speaker_name)
        if original_name is not None:
            speaker_name = original_name
        main_df[speaker_name] = {}
        origins = glob(speaker + "/*")
        for origin in origins:
            if not os.path.isdir(origin):
                continue
            origin_name = os.path.basename(origin)
            main_df[speaker_name][origin_name] = {}
            defaults = glob(origin + "/*")
            for default in defaults:
                if not os.path.isdir(default):
                    continue
                default_name = os.path.basename(default)
                main_df[speaker_name][origin_name][default_name] = {}
                graphs = glob(default + "/*.json")
                for graph in graphs:
                    g = os.path.basename(graph).replace(".json", "")
                    main_df[speaker_name][origin_name][default_name][g] = {}

    # configure Mako
    mako_templates = TemplateLookup(
        directories=[cpaths.CPATH_WEBSITE, cpaths.CPATH_BUILD_WEBSITE],
        module_directory=cpaths.CPATH_BUILD_MAKO,
    )

    # write index.html
    logger.info("Write index.html")
    index_html = mako_templates.get_template("index.html")
    meta_sorted_date = sort_metadata_per_date(meta)

    try:
        html_content = index_html.render(
            df=main_df,
            meta=meta_sorted_date,
            site=site,
            use_search=True,
            min=".min" if flag_optim else "",
            versions=versions,
        )
        html_filename = f"{cpaths.CPATH_DIST}/index.html"
        write_if_different(html_content, html_filename, force=False)
    except KeyError as key_error:
        print("Generating index.html failed with {}".format(key_error))
        sys.exit(1)

    # write eqs.html
    logger.info("Write eqs.html")
    eqs_html = mako_templates.get_template("eqs.html")

    try:
        eqs_content = eqs_html.render(
            df=main_df,
            meta=meta_sorted_date,
            site=site,
            use_search=True,
            min=".min" if flag_optim else "",
            versions=versions,
        )
        eqs_filename = f"{cpaths.CPATH_DIST}/eqs.html"
        if isinstance(eqs_content, str):
            write_if_different(eqs_content, eqs_filename, force=False)
        else:
            print("Generating eqs.html failed, template generation failed")
            sys.exit(1)
    except KeyError as key_error:
        print("Generating eqs.html failed with {}".format(key_error))
        sys.exit(1)

    # write various html files
    meta_sorted_score = sort_metadata_per_score(meta)
    try:
        for item in (
            "compare",
            "customization",
            "scores",
            "similar",
            "statistics",
        ):
            item_name = "{0}.html".format(item)
            logger.info("Write %s", item_name)
            item_html = mako_templates.get_template(item_name)
            use_search = False
            if item in ("scores", "similar"):
                use_search = True
            item_content = item_html.render(
                df=main_df,
                meta=meta_sorted_score,
                site=site,
                use_search=use_search,
                    min=".min" if flag_optim else "",
                versions=versions,
            )
            item_filename = cpaths.CPATH_DIST + "/" + item_name
            write_if_different(item_content, item_filename, force=False)

    except KeyError as key_error:
        print("Generating various html files failed with {}".format(key_error))
        sys.exit(1)

    # write headphone html pages
    logger.info("Write headphone pages")
    try:
        hp_meta = None
        hp_meta_file = cpaths.CPATH_DIST_HEADPHONE_METADATA_JSON
        if os.path.isfile(hp_meta_file):
            with open(hp_meta_file, "r") as f:
                hp_meta = json.load(f)

        if hp_meta:
            hp_eqdata_file = cpaths.CPATH_DIST_HEADPHONE_EQDATA_JSON
            if os.path.isfile(hp_eqdata_file):
                with open(hp_eqdata_file, "r") as f:
                    hp_eqs = json.load(f)
                    for k, v in hp_eqs.items():
                        if k in hp_meta and "eqs" in v:
                            hp_meta[k]["eqs"] = v["eqs"]
                        if k in hp_meta and "default_eq" in v:
                            hp_meta[k]["default_eq"] = v["default_eq"]

            # headphone index page
            for hp_page in ("headphone_index", "headphone_eqs", "headphone_scores"):
                hp_page_name = "{}.html".format(hp_page)
                logger.info("Write %s", hp_page_name)
                hp_page_html = mako_templates.get_template(hp_page_name)
                hp_content = hp_page_html.render(
                    df={},
                    meta=hp_meta,
                    site=site,
                    use_search=True,
                    min=".min" if flag_optim else "",
                    versions=versions,
                )
                # headphone_index.html -> /headphones.html etc
                dist_name = hp_page_name.replace("headphone_index", "headphones").replace(
                    "headphone_", "headphone_"
                )
                hp_filename = f"{cpaths.CPATH_DIST}/{dist_name}"
                write_if_different(hp_content, hp_filename, force=False)

            # per-headphone pages
            hp_html = mako_templates.get_template("headphone.html")
            graph_html = mako_templates.get_template("graph.html")

            HEADPHONE_FREQ_FILTER = [
                "Frequency Response",
                "Frequency Response Compensated",
                "Target Deviation",
            ]

            for hp_name, hp_data in hp_meta.items():
                if hp_data.get("skip", False):
                    continue
                brand = hp_data.get("brand", "")
                default_m = hp_data.get("default_measurement", "asr")
                m_data = hp_data.get("measurements", {}).get(default_m, {})
                origin = m_data.get("origin", "ASR")

                hp_dist_dir = "{}/{}/{}/".format(
                    cpaths.CPATH_DIST_HEADPHONES, hp_name, origin
                )
                os.makedirs(hp_dist_dir, exist_ok=True)

                # Check which graphs exist
                freq_graphs = {}
                for gname in HEADPHONE_FREQ_FILTER:
                    gpath = "{}/{}/{}.json".format(hp_dist_dir, default_m, gname)
                    if os.path.isfile(gpath):
                        freq_graphs[gname] = {}

                if not freq_graphs:
                    continue

                # Check which EQ graphs exist
                eq_graph_names = ["Frequency Response", "Target Deviation"]
                eq_graphs = {}
                has_eq_flat = False
                has_eq_score = False
                eq_flat_key = None
                eq_score_key = None
                for eq_key in ("autoeq_score", "autoeq_flat"):
                    eq_subdir = "{}_eq_{}".format(default_m, eq_key)
                    eq_subdir_path = os.path.join(hp_dist_dir, eq_subdir)
                    if not os.path.isdir(eq_subdir_path):
                        continue
                    graphs = {}
                    for gname in eq_graph_names:
                        gpath = os.path.join(eq_subdir_path, "{}.json".format(gname))
                        if os.path.isfile(gpath):
                            graphs[gname] = {}
                    if not graphs:
                        continue
                    eq_graphs[eq_key] = (eq_subdir, graphs)
                    if eq_key == "autoeq_flat":
                        has_eq_flat = True
                        eq_flat_key = eq_subdir
                    else:
                        has_eq_score = True
                        eq_score_key = eq_subdir

                index_name = "{}/index_{}.html".format(hp_dist_dir, default_m)
                logger.info("Writing %s for %s", index_name, hp_name)
                hp_content = hp_html.render(
                    headphone=hp_name,
                    g_freq=freq_graphs,
                    g_key=default_m,
                    meta=hp_meta,
                    origin=origin,
                    has_eq_flat=has_eq_flat,
                    has_eq_score=has_eq_score,
                    eq_flat_key=eq_flat_key,
                    eq_score_key=eq_score_key,
                    g_eq_flat=eq_graphs.get("autoeq_flat", ({}, {}))[1],
                    g_eq_score=eq_graphs.get("autoeq_score", ({}, {}))[1],
                    site=site,
                    use_search=False,
                    min=".min" if flag_optim else "",
                    versions=versions,
                )
                write_if_different(hp_content, index_name, force=False)

                # per-graph html pages
                for graph_name in freq_graphs:
                    graph_filename = "{}/{}/{}.html".format(hp_dist_dir, default_m, graph_name)
                    graph_content = graph_html.render(
                        speaker=hp_name,
                        graph=graph_name,
                        meta=hp_meta,
                        site=site,
                        min=".min" if flag_optim else "",
                        versions=versions,
                    )
                    write_if_different(graph_content, graph_filename, force=False)

                # per-EQ-graph html pages
                for eq_subdir, graphs in eq_graphs.values():
                    for graph_name in graphs:
                        graph_filename = "{}/{}/{}.html".format(
                            hp_dist_dir, eq_subdir, graph_name
                        )
                        graph_content = graph_html.render(
                            speaker=hp_name,
                            graph=graph_name,
                            meta=hp_meta,
                            site=site,
                            min=".min" if flag_optim else "",
                            versions=versions,
                        )
                        write_if_different(graph_content, graph_filename, force=False)
    except Exception as e:
        print("Generating headphone pages failed with {}".format(e))
        import traceback
        traceback.print_exc()

    # write a file per speaker
    if not skip_speakers:
        logger.info("Write a file per speaker")
        try:
            generate_speakers(
                mako_templates, main_df, meta=meta, site=site, use_search=False, versions=versions
            )
        except KeyError as key_error:
            print("Generating a file per speaker failed with {}".format(key_error))
            sys.exit(1)
    else:
        logger.info("Skip speaker html generation!")

    # copy all icons (png, jpg, webp, svg, ico) to dist/pictures
    for file_in in glob("{}/*".format(cpaths.CPATH_DATAS_ICONS)):
        if file_in.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico")):
            f = os.path.basename(file_in)
            file_out = cpaths.CPATH_DIST + "/pictures/" + f
            shutil.copy(file_in, file_out)

    # copy custom css and manifest
    for file, sub in [
        ("spinorama.css", "css/"),
        ("manifest.json", "/"),
    ]:
        file_in = "{}/{}".format(cpaths.CPATH_WEBSITE, file)
        file_out = "{}/{}{}".format(cpaths.CPATH_DIST, sub, file)
        shutil.copy(file_in, file_out)

    # copy css/js files
    logger.info("Copy js files to %s", cpaths.CPATH_DIST_JS)
    for item in (
        "compare",
        "download",
        "error",
        "eqs",
        "graph",
        "index",
        "meta",
        "misc",
        "onload",
        "pagination",
        "plot",
        "plot-config",
        "scores",
        "search",
        "similar",
        "statistics",
        "tabs",
        "theme",
        "headphone_index",
        "headphone_eqs",
        "headphone_scores",
        "headphone_target",
    ):
        try:
            # remove the ./dist parts
            len_dist = len("/dist/")
            metadata_filename = metadata_json_filename[len_dist:]
            metadata_filename_head = metadata_json_chunks["head"][len_dist:]
            js_chunks = "[{}]".format(
                ", ".join(
                    [
                        "'{}'".format(v[len_dist:])
                        for k, v in metadata_json_chunks.items()
                        if k != "head"
                    ]
                )
            )
            # pipeline
            item_name = "{}.js".format(item)
            item_original = "{}/{}.js".format(cpaths.CPATH_WEBSITE, item)
            # if item == "misc":
            #     item_original = "{}/{}.js.tmpl".format(cpaths.CPATH_WEBSITE, item)
            item_mako_tmpl = "{}-0-copy.js".format(item)
            item_post_copy = "{}/{}-0-copy.js".format(cpaths.CPATH_BUILD_WEBSITE, item)
            item_post_mako = "{}/{}-1-mako.js".format(cpaths.CPATH_BUILD_WEBSITE, item)
            item_post_import = "{}/{}-2-import.js".format(cpaths.CPATH_BUILD_WEBSITE, item)
            item_post_terser = "{}/{}-3-terser.js".format(cpaths.CPATH_BUILD_WEBSITE, item)
            if flag_optim:
                item_dist = "{}/{}-{}.min.js".format(cpaths.CPATH_DIST_JS, item, CACHE_VERSION)
            else:
                item_dist = "{}/{}-{}.js".format(cpaths.CPATH_DIST_JS, item, CACHE_VERSION)

            shutil.copy(item_original, item_post_copy)

            # build first generation with metadata expension, now only useful for meta.js
            if item == "meta":
                item_html = mako_templates.get_template(item_mako_tmpl)
                eqdata_filename = eqdata_json_filename[len_dist:]
                item_content = item_html.render(
                    df=main_df,
                    meta=meta_sorted_score,
                    site=site,
                    metadata_filename=metadata_filename,
                    metadata_filename_head=metadata_filename_head,
                    metadata_filename_chunks=js_chunks,
                    eqdata_filename=eqdata_filename,
                    min=".min" if flag_optim else "",
                    versions=versions,
                )
                if item_content:
                    write_if_different(str(item_content), item_post_mako, force=True)
            else:
                shutil.copy(item_post_copy, item_post_mako)

            # change import to match prod/dev and browser requirements
            with open(item_post_mako, "r") as fd:
                item_content = "".join(fd.readlines())
                item_content = adapt_imports(
                    item_content, versions, jsfiles, ".min" if flag_optim else ""
                )
                write_if_different(item_content, item_post_import, force=True)

            # compress files with terser
            if flag_optim:
                terser_command = "{0} {1}".format("./node_modules/.bin/terser", item_post_import)
                # remove stale terser output before running
                if os.path.exists(item_post_terser):
                    os.remove(item_post_terser)
                try:
                    with open(item_post_terser, "w") as item_post_terser_fd:
                        status = subprocess.run(  # noqa: S603
                            shlex.split(terser_command),
                            shell=False,
                            check=True,
                            stdout=item_post_terser_fd,
                        )
                        if status.returncode != 0:
                            print("terser failed for item {}".format(item))
                except subprocess.CalledProcessError as e:
                    print("terser failed for item {} with {}".format(item, e))
                    # remove failed terser output
                    if os.path.exists(item_post_terser):
                        os.remove(item_post_terser)

                # copy terser output if it exists, otherwise fall back to uncompressed
                if os.path.exists(item_post_terser):
                    shutil.copy(item_post_terser, item_dist)
                else:
                    shutil.copy(item_post_import, item_dist)
            else:
                # copy last file
                shutil.copy(item_post_import, item_dist)
                # remove stale terser output to avoid confusion
                if os.path.exists(item_post_terser):
                    os.remove(item_post_terser)

        except KeyError as key_error:
            print("Generating {} js file failed with {}".format(item, key_error))
            sys.exit(1)

    # generate robots.txt and sitemap.xml
    logger.info("Copy robots/sitemap files to %s", cpaths.CPATH_DIST)
    try:
        for item_name in (
            "robots.txt",
            "sitemap.xml",
        ):
            logger.info("Write %s", item_name)
            item_html = mako_templates.get_template(item_name)
            item_content = item_html.render(
                df=main_df,
                meta=meta_sorted_score,
                site=site,
                isProd=(site == SITEPROD),
                min=".min" if flag_optim else "",
                versions=versions,
            )
            item_filename = cpaths.CPATH_DIST + "/" + item_name
            # ok for robots but likely doesn't work for sitemap
            write_if_different(str(item_content), item_filename, force=True)
    except KeyError as key_error:
        print("Copying robots files failed with {}".format(key_error))
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate HTML website for spinorama data.")
    parser.add_argument("--version", action="version", version="./scripts/generate_html.py version 1.23")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Generate the dev website (disables optimizations unless overridden).",
    )
    parser.add_argument(
        "--optim", action="store_true", help="Generate an optimised build (minification, etc.)."
    )
    parser.add_argument(
        "--sitedev",
        type=str,
        help="Base URL for dev site (e.g., http://localhost:8000/dist). Used if --dev is active.",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level (default: WARNING).",
    )
    parser.add_argument(
        "--skip-speakers",
        action="store_true",
        help="Skip speaker HTML page generation (useful for debugging, only effective with --dev).",
    )

    parsed_args = parser.parse_args()

    flag_dev = parsed_args.dev
    flag_optim = parsed_args.optim
    site = SITEPROD  # Default site URL
    skip_speakers = False  # Default for skipping speaker page generation

    if flag_dev:
        site = SITEDEV  # Default dev site URL
        if parsed_args.sitedev is not None:
            site = parsed_args.sitedev
            if not site.startswith("http"):
                print(f"Error: --sitedev URL '{site}' must start with http:// or https://")
                sys.exit(1)
        skip_speakers = parsed_args.skip_speakers
    # If not --dev, flag_optim remains as set by parsed_args.optim

    logger = get_custom_logger(level=args2level(parsed_args), duplicate=True)
    main()  # main() uses the module-level flags set above
