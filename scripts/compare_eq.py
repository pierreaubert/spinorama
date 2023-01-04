#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import math
import numpy as np
import pandas as pd

import plotly.graph_objects as go

from spinorama.load_misc import graph_melt
from spinorama.load_rewseq import parse_eq_iir_rews
from spinorama.filter_iir import Biquad
from spinorama.filter_peq import peq_build, peq_freq


def flat():
    nb_points = 200
    flat_u = pd.DataFrame(
        {
            "Freq": np.logspace(1.0 + math.log10(2), 4.0 + math.log10(2), nb_points),
            "On Axis": [0] * nb_points,
        }
    )
    flat = graph_melt(flat_u)
    return flat


def load_peqs(paths):
    my_fs = 48000
    peqs = {}
    count = 0
    for iirname in paths:
        if os.path.isfile(iirname):
            biir = os.path.basename(iirname)
            peqs[biir] = parse_eq_iir_rews(iirname, my_fs)
    return peqs


def plot_eq(peqs):
    nb_points = 200
    freqs = np.logspace(1.0 + math.log10(2), 4.0 + math.log10(2), nb_points)
    traces = []
    for name, peq in peqs.items():
        traces.append(go.Scatter(x=freqs, y=peq_build(freqs, peq), name=name))
        fig = go.Figure(data=traces)
        fig.update_xaxes(
            dict(
                title_text="Frequency (Hz)",
                type="log",
                range=[math.log10(20), math.log10(20000)],
                showline=True,
                dtick="D1",
            ),
        )
        fig.update_yaxes(
            dict(
                title_text="SPL (dB)",
                range=[-5, 5],
                showline=True,
                dtick="D1",
            ),
        )
        fig.update_layout(title="EQs")

    return fig


if __name__ == "__main__":

    if len(sys.argv) <= 4 or sys.argv[1] != "-o":
        print("usage: {} -o output.jpg eq1.txt eq2.txt ...".format(sys.argv[0]))
        sys.exit(1)

    peqs = load_peqs(sys.argv[3:])
    fig = plot_eq(peqs)
    fig.write_image(sys.argv[2])

    sys.exit(0)
