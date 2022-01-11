# -*- coding: utf-8 -*-
import os
import logging
import pathlib
import copy
import zipfile
import pandas as pd
from wand.image import Image as wim

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray


from .speaker_display import (
    display_spinorama,
    display_onaxis,
    display_inroom,
    display_reflection_early,
    display_reflection_horizontal,
    display_reflection_vertical,
    display_spl_horizontal,
    display_spl_vertical,
    display_spl_horizontal_normalized,
    display_spl_vertical_normalized,
    display_contour_horizontal,
    display_contour_vertical,
    display_contour_horizontal_normalized,
    display_contour_vertical_normalized,
    display_radar_horizontal,
    display_radar_vertical,
)
from .plot import plot_params_default, contour_params_default, radar_params_default


logger = logging.getLogger("spinorama")


def print_graph(speaker, origin, key, title, chart, force, fileext):
    updated = 0
    if chart is not None:
        filedir = "docs/" + speaker + "/" + origin.replace("Vendors-", "") + "/" + key
        pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
        for ext in ["json", "png"]:  # svg and html skipped to keep size small
            # skip the 2cols.json and 3cols.json as they are really large
            # 2cols and 3cols are more for printing
            if ext == "json" and title in (
                "2cols",
                "3cols",
            ):
                continue
            filename = filedir + "/" + title.replace("_smoothed", "")
            if ext == "png":
                # generate large image that are then easy to find and compress
                # before uploading
                filename += "_large"
            filename += "." + ext
            if ext == "json":
                filename += ".zip"
            if (
                force
                or not os.path.exists(filename)
                or (os.path.exists(filename) and os.path.getsize(filename) == 0)
            ):
                if fileext is None or (fileext is not None and fileext == ext):
                    try:
                        if ext == "json":
                            content = chart.to_json()
                            with zipfile.ZipFile(
                                filename,
                                "w",
                                compression=zipfile.ZIP_DEFLATED,
                                allowZip64=True,
                            ) as current_zip:
                                current_zip.writestr("{0}.json".format(title), content)
                                logger.info("Saving {0} in {1}".format(title, filename))
                                updated += 1
                        else:
                            chart.write_image(filename)
                            if os.path.getsize(filename) == 0:
                                logger.warning(
                                    "Saving {0} in {1} failed!".format(title, filename)
                                )
                            else:
                                logger.info("Saving {0} in {1}".format(title, filename))
                                updated += 1
                                with wim(filename=filename) as pict:
                                    pict.convert("webp").save(
                                        filename="{}.webp".format(filename[:-10])
                                    )
                                    # pict.convert("avif").save(
                                    #    filename="{}.avif".format(filename[:-10])
                                    # )
                                    pict.compression_quality = 75
                                    pict.convert("jpg").save(
                                        filename="{}.jpg".format(filename[:-10])
                                    )
                    except Exception as e:
                        logger.error("Got unkown error {0} for {1}".format(e, filename))
    else:
        logger.debug(
            "Chart is None for {:s} {:s} {:s} {:s}".format(speaker, origin, key, title)
        )
    return updated


@ray.remote
def print_graphs(
    df: pd.DataFrame,
    speaker,
    origin,
    origins_info,
    key="default",
    width=1200,
    height=800,
    force_print=False,
    filter_file_ext=None,
):
    # may happens at development time
    if df is None:
        return 0

    graph_params = copy.deepcopy(plot_params_default)
    if width // height != 4 // 3:
        logger.error("ratio width / height must be 4/3")
        height = int(width * 3 / 4)
    graph_params["width"] = width
    graph_params["height"] = height
    graph_params["layout"] = "compact"
    graph_params["xmin"] = origins_info[origin]["min hz"]
    graph_params["xmax"] = origins_info[origin]["max hz"]
    graph_params["ymin"] = origins_info[origin]["min dB"]
    graph_params["ymax"] = origins_info[origin]["max dB"]
    logger.debug("Graph configured with {0}".format(graph_params))

    graphs = {}
    graphs["CEA2034"] = display_spinorama(df, graph_params)
    graphs["On Axis"] = display_onaxis(df, graph_params)
    graphs["Estimated In-Room Response"] = display_inroom(df, graph_params)
    graphs["Early Reflections"] = display_reflection_early(df, graph_params)
    graphs["Horizontal Reflections"] = display_reflection_horizontal(df, graph_params)
    graphs["Vertical Reflections"] = display_reflection_vertical(df, graph_params)
    graphs["SPL Horizontal"] = display_spl_horizontal(df, graph_params)
    graphs["SPL Vertical"] = display_spl_vertical(df, graph_params)
    graphs["SPL Horizontal Normalized"] = display_spl_horizontal_normalized(
        df, graph_params
    )
    graphs["SPL Vertical Normalized"] = display_spl_vertical_normalized(
        df, graph_params
    )

    # change params for contour
    contour_params = copy.deepcopy(contour_params_default)
    contour_params["width"] = width
    contour_params["height"] = width // 2
    contour_params["layout"] = "compact"
    contour_params["xmin"] = origins_info[origin]["min hz"]
    contour_params["xmax"] = origins_info[origin]["max hz"]

    graphs["SPL Horizontal Contour"] = display_contour_horizontal(df, contour_params)
    graphs["SPL Vertical Contour"] = display_contour_vertical(df, contour_params)
    graphs["SPL Horizontal Contour Normalized"] = display_contour_horizontal_normalized(
        df, contour_params
    )
    graphs["SPL Vertical Contour Normalized"] = display_contour_vertical_normalized(
        df, contour_params
    )

    # better square
    radar_params = copy.deepcopy(radar_params_default)
    radar_params["width"] = int(height * 4 / 5)
    radar_params["height"] = height
    radar_params["layout"] = "compact"
    radar_params["xmin"] = origins_info[origin]["min hz"]
    radar_params["xmax"] = origins_info[origin]["max hz"]

    graphs["SPL Horizontal Radar"] = display_radar_horizontal(df, radar_params)
    graphs["SPL Vertical Radar"] = display_radar_vertical(df, radar_params)

    # add a title and setup legend
    for k in graphs:
        title = k.replace("_smoothed", "")
        # optimised for small screens / vertical orientation
        if graphs[k] is not None:
            graphs[k].update_layout(
                title=dict(
                    text="{2} for {0} measured by {1}".format(speaker, origin, title),
                    font=dict(
                        size=24,
                    ),
                ),
                font=dict(
                    size=22,
                ),
            )

    updated = 0
    for (title, graph) in graphs.items():
        if graph is not None:
            updated = print_graph(
                speaker, origin, key, title, graph, force_print, filter_file_ext
            )
    return updated
