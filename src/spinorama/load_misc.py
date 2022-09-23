# -*- coding: utf-8 -*-
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("spinorama")


def graph_melt(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.reset_index()
        .melt(id_vars="Freq", var_name="Measurements", value_name="dB")
        .loc[lambda df: df["Measurements"] != "index"]
    )


def sort_angles(dfi: pd.DataFrame) -> pd.DataFrame:
    # sort columns in increasing angle order
    def a2v(angle):
        if angle == "Freq":
            return -1000
        if angle in ("On Axis", "On-Axis"):
            return 0
        return int(angle[:-1])

    dfu = dfi.reindex(columns=sorted(set(dfi.columns), key=a2v))
    dfu = dfu.rename(columns={"On-Axis": "On Axis"})
    return dfu


def check_nan(df):
    for k in df.keys():
        if not isinstance(df[k], pd.DataFrame):
            continue
        for j in df[k].keys():
            if isinstance(df[k], pd.DataFrame):
                count = df[k][j].isna().sum()
                if count > 0:
                    logger.error("{} {} {}".format(k, j, count))
    return np.sum(
        [
            df[frame].isna().sum().sum()
            for frame in df.keys()
            if isinstance(df[frame], pd.DataFrame)
        ]
    )
