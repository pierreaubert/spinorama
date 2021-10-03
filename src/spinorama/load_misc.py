# -*- coding: utf-8 -*-
import logging
import pandas as pd


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

    dfu = dfi.reindex(columns=sorted(dfi.columns, key=a2v))
    dfu = dfu.rename(columns={"On-Axis": "On Axis"})
    return dfu
