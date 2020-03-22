import numpy as np
import pandas as pd


def unify_freq(dfs):
    """ unify_freq

    There is no guaranty that all frequency points are the same on all graphs. This is 
    an issue for operations on multiple graphs at the same time. Let's merge all freq
    points such that all graphs have exactlty the same set of points and thus the same shape.

    This use linear interpolation for missing points and can generate some NaN in the frame.
    Rows (Freq) with at least 1 NaN are removed.

    dfs: a spinorama stored into a panda DataFrame
    """
    on = dfs[dfs.Measurements == 'On Axis'].rename(columns={'dB': 'ON'}).set_index('Freq')
    lw = dfs[dfs.Measurements == 'Listening Window'].rename(columns={'dB': 'LW'}).set_index('Freq')
    er = dfs[dfs.Measurements == 'Early Reflections'].rename(columns={'dB': 'ER'}).set_index('Freq')
    sp = dfs[dfs.Measurements == 'Sound Power'].rename(columns={'dB': 'SP'}).set_index('Freq')
    # align 2 by 2
    align = on.align(lw, axis=0)
    # print(align[0].shape)
    align = align[0].align(er, axis=0)
    # print(align[0].shape)
    all_on = align[0].align(sp, axis=0)
    # print(all_on[0].head())
    # print(all_on[0].shape)
    # realigned with the largest frame
    all_lw = all_on[0].align(lw, axis=0)
    all_er = all_on[0].align(er, axis=0)
    all_sp = all_on[0].align(sp, axis=0)
    # print(all_lw[1].shape, all_er[1].shape, all_sp[1].shape)
    # extract right parts and interpolate
    a_on = all_on[0].drop('Measurements', axis=1).interpolate()
    a_lw = all_lw[1].drop('Measurements', axis=1).interpolate()
    a_er = all_er[1].drop('Measurements', axis=1).interpolate()
    a_sp = all_sp[1].drop('Measurements', axis=1).interpolate()
    # print(a_lw.shape, a_er.shape, a_sp.shape)
    # remove NaN numbers
    res2 = pd.DataFrame({'Freq': a_lw.index, 
                         'On Axis': a_on.ON,
                         'Listening Window': a_lw.LW, 
                         'Early Reflections': a_er.ER, 
                         'Sound Power': a_sp.SP})
    # print(res2.head())
    return res2.dropna().reset_index(drop=True)


def normalize_mean(df):
    on = df[df.Measurements == 'On Axis']
    mean = np.mean(on.loc[(on.Freq>500) & (on.Freq<10000)].dB)
    return mean


def normalize_cea2034(dfc, mean):
    df = dfc.copy()

    offset = mean
    if 'DI offset' in df.Measurements.unique():
        offset = np.mean(df[df.Measurements == 'DI offset'].dB)

    for measurement in ('On Axis', 'Listening Window', 'Sound Power', 'Early Reflections'):
        df.loc[df.Measurements == measurement, 'dB'] -= mean

    for measurement in ('Sound Power DI', 'Early Reflections DI', 'DI offset'):
        df.loc[df.Measurements == measurement, 'dB'] -= offset

    return df


def normalize(dfc, mean):
    df = dfc.copy()
    df.dB -= mean
    return df


def pprint(df):
    for m in df.Measurements.unique():
        min = np.min(df[df.Measurements == m].dB)
        max = np.max(df[df.Measurements == m].dB)
        print('{0} {1} {2}'.format(min, max, m))


def resample(df, target_size):
    len_freq = df.shape[0]
    if len_freq > 2*target_size:
        roll = int(len_freq/target_size)
        sampled = df.loc[df.Freq.rolling(roll).max()[1::roll].index,:]
        return sampled
    return df


