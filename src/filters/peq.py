import logging
import math
import altair as alt
import numpy as np
import pandas as pd
from .iir import Biquad
from src.spinorama.load import graph_melt


def peq_build(freq, peq):
    filter = 0
    for w, iir in peq:
        filter += w*np.array([iir.log_result(f) for f in freq])
    return filter


def peq_freq(spl, peq):
    filter = 0
    for w, iir in peq:
        filter += w*np.array([iir(v) for v in spl])
    return filter


def peq_apply_measurements(spl, peq):
    freq   = spl['Freq'].to_numpy()
    mean = np.mean(spl.loc[(spl.Freq>500) & (spl.Freq<10000)]['On Axis'])
    ddf = []
    ddf.append(pd.DataFrame({'Freq': freq}))
    for angle in spl.keys():
        if angle == 'Freq':
            continue
        curve = spl[angle]-mean
        curve_filtered = curve+peq_build(freq, peq)
        logging.debug('{0:7s} range [{1:.1f}, {2:.1f}] filtered [{3:.1f}, {4:.1f}]'.format(angle, np.min(curve), np.max(curve), np.min(curve_filtered), np.max(curve_filtered)))
        # print(curve, curve_filtered)
        ddf.append(pd.DataFrame({angle: curve_filtered}))
    return pd.concat(ddf, axis=1)


def peq_graph_measurements(spin, measurement, peq):
    spin_freq   = spin['Freq'].to_numpy()
    mean = np.mean(spin.loc[(spin.Freq>500) & (spin.Freq<10000)]['On Axis'])
    curve = spin[measurement]-mean
    filter = peq_build(spin_freq, peq)
    curve_filtered = peq_apply_measurements(curve, peq)
    dff = pd.DataFrame({'Freq': spin_freq, measurement: curve, '{0} Filtered'.format(measurement): curve_filtered, 'Filter': filter})
    return alt.Chart(graph_melt(dff)).mark_line(clip=True).encode(
        x=alt.X('Freq:Q', scale=alt.Scale(type='log', nice=False, domain=[20, 20000])),
        y=alt.Y('dB:Q', scale=alt.Scale(domain=[-25, 5])),
        color=alt.Color('Measurements')
    )




    
