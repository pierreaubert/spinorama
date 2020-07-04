from more_itertools import consecutive_groups
import logging
import math
import numpy as np
from scipy.stats import linregress
from .load import graph_melt
from .cea2034 import estimated_inroom_HV

# https://courses.physics.illinois.edu/phys406/sp2017/Lab_Handouts/Octave_Bands.pdf
def octave(N):
    """compute 1/N octave band

    N: >=2 when N increases, bands are narrower
    """
    # why 1290 and not 1000?
    reference = 1290
    p = pow(2, 1/N)
    p_band = pow(2, 1/(2*N))
    iter = int((N*10+1)/2)
    center = [reference / p**i for i in range(iter, 0, -1)]+[reference]+[reference*p**i for i in range(1, iter+1, 1)]
    octave = [(c/p_band, c, c*p_band) for c in center]
    # print('Octave({0}) octave[{1}], octave[{2}'.format(N, octave[0], octave[-1]))
    return octave


def aad(dfu):
    """ aad Absolute Average Deviation
    """
    # mean betwenn 200hz and 400hz
    y_ref = np.mean(dfu.loc[(dfu.Freq >= 200) & (dfu.Freq <= 400)].dB)
    # print(y_ref)
    aad_sum = 0
    n = 0
    # 1/20 octave
    for (bmin, bcenter, bmax) in octave(20):
        # 100hz to 16k hz
        if bcenter < 100 or bmax > 16000:
            continue
        selection = dfu.loc[(dfu.Freq >= bmin) & (dfu.Freq < bmax)]
        if selection.shape[0] > 0:
            aad_sum += abs(y_ref-np.nanmean(selection.dB))
            n += 1
    if n == 0:
        logging.error('aad is None')
        return None
    aad_value = aad_sum/n
    #if math.isnan(aad_value):
    #    pd.set_option('display.max_rows', dfu.shape[0]+1)
    #    print(aad_sum, n, dfu)
    return aad_value


def nbd(dfu):
    """ nbd Narrow Band

    The narrow band deviation is defined by:
      NBD(dB)=⎜ ∑ y −y ⎟÷N  ⎛
    where ⎜ OctaveBandn⎟ is the average amplitude value
    within the 1⁄2-octave band n, yb is the amplitude
    value of band b, and N is the total number of 1⁄2­ octave bands 
    between 100 Hz-12 kHz. The mean absolute deviation within each 
    1⁄2-octave band is based a sample of 10 equally log-spaced data points.
    """
    #return np.mean([median_absolute_deviation(dfu.loc[(dfu.Freq >= bmin) & (dfu.Freq <= bmax)].dB)
    #                for (bmin, bcenter, bmax) in octave(2)
    #                if bcenter >=100 and bcenter <=12000])
    return np.nanmean([dfu.loc[(dfu.Freq >= bmin) & (dfu.Freq <= bmax)].dB.mad()
                       for (bmin, bcenter, bmax) in octave(2)
                       if bcenter >=100 and bcenter <=12000])


def lfx(lw, sp):
    """ lfx Low Frequency Extension

    The low frequency extension (LFX)
         LFX = log10(xSP−6dB.re:y _ LW(300Hz−10kHz) (7)
    where LFX is the log10 of the first frequency x_SP below 300 Hz
    in the sound power curve, that is -6 dB relative to the mean level y_LW
    measured in listening window (LW) between 300 Hz-10 kHz.
    LFX is log-transformed to produce a linear relationship between the 
    variable LFX and preference rating. The sound power curve (SP) is used
    for the calculation because it better defines the true bass output of
    the loudspeaker, particularly speakers that have rear-firing ports.
    """
    lw_ref = np.mean(lw.loc[(lw.Freq >= 300) & (lw.Freq <= 10000)].dB)-6
    # find first freq such that y[freq]<y_ref-6dB
    lfx_range = sp.loc[(sp.Freq < 300) & (sp.dB <= lw_ref)].Freq
    lfx_grouped = consecutive_groups(lfx_range.iteritems(), lambda x: x[0])
    try:
        lfx_hz = list(next(lfx_grouped))[-1][1]
    except Exception:
        lfx_hz = lfx_range.max()
        logging.debug('lfx: selecting max {0}'.format(lfx_hz))
    return math.log10(lfx_hz)


def lfq(lw, sp, lfx_log):
    """ lfq Low Frequency Quality

    LFQ is intended to quantify deviations in amplitude response over the
    bass region between the low frequency cut-off and 300 Hz.
    """
    lfx = pow(10, lfx_log)
    sum = 0
    n = 0
    # print('DEBUG lfx={1} octave(20): {0}'.format(octave(20), lfx))
    for (bmin, bcenter, bmax) in octave(20):
        # 100hz to 12k hz
        if bmin < lfx or bmax > 300:
            continue
        s_lw = lw.loc[(lw.Freq >= bmin) & (lw.Freq < bmax)]
        s_sp = sp.loc[(sp.Freq >= bmin) & (sp.Freq < bmax)]
        if s_lw.shape[0] > 0 and s_sp.shape[0] > 0:
            y_lw = np.mean(s_lw.dB)
            y_sp = np.mean(s_sp.dB)
            sum += abs(y_lw-y_sp)
            n += 1
    if n == 0:
        logging.error('lfq is None')
        return None
    return sum/n


def sm(dfu):
    """ sm Smoothness

    For each of the 7 frequency response curves, the overall smoothness (SM) and
    slope (SL) of the curve was determined by estimating the line that best fits
    the frequency curve over the range of 100 Hz-16 kHz. This was done using a
    regression based on least square error. SM is the Pearson correlation 
    coefficient of determination (r2) that describes the goodness of fit of the
    regression line defined by:
    ⎛ SM =⎜ n(∑XY)−(∑X)(∑Y) ⎟ / ⎜ (n∑X2 −(∑X)2)(n∑Y2 −(∑Y)2)⎟

    where n is number of data points used to estimate the regression curve and 
    X and Y represent the measured versus estimated amplitude values of the 
    regression line. A natural log transformation is applied to the measured 
    frequency values (Hz) so that they are linearly spaced (see equation 5). 
    Smoothness (SM) values can range from 0 to 1, with larger values representing 
    smoother frequency response curves.
    """
    data = dfu.loc[(dfu.Freq>=100) & (dfu.Freq<=16000)]
    log_freq = np.log(data.Freq)
    slope, intercept, r_value, p_value, std_err = linregress(log_freq, data.dB)
    return r_value**2
                

def pref_rating_wsub(nbd_on, nbd_pir, sm_pir):
    return 12.69-2.49*nbd_on-2.99*nbd_pir+2.32*sm_pir

def pref_rating(nbd_on, nbd_pir, lfx, sm_pir):
    return 12.69-2.49*nbd_on-2.99*nbd_pir-4.31*lfx+2.32*sm_pir


def speaker_pref_rating(cea2034, df_pred_in_room, rounded=True):
    try:
        if df_pred_in_room is None or df_pred_in_room.shape[0] == 0:
            logging.info('PIR is empty')
            return None
        df_on_axis = cea2034.loc[lambda df: df.Measurements == 'On Axis']
        df_listening_window = cea2034.loc[lambda df: df.Measurements == 'Listening Window']
        df_sound_power = cea2034.loc[lambda df: df.Measurements == 'Sound Power']
        skip_full = False
        for dfu in (df_on_axis, df_listening_window, df_sound_power):
            if dfu.loc[(dfu.Freq>=100) & (dfu.Freq<=400)].shape[0] == 0:
                skip_full = True
        nbd_on_axis = nbd(df_on_axis)
        nbd_listening_window = nbd(df_listening_window)
        nbd_sound_power = nbd(df_sound_power)
        nbd_pred_in_room = nbd(df_pred_in_room)
        if not skip_full:
            aad_on_axis = aad(df_on_axis)
            lfx_hz = lfx(df_listening_window, df_sound_power)
            lfq_db = lfq(df_listening_window, df_sound_power, lfx_hz)
        sm_sound_power = sm(df_sound_power)
        sm_pred_in_room = sm(df_pred_in_room)
        if nbd_on_axis is None or nbd_pred_in_room is None or sm_pred_in_room is None:
            return None
        pref_wsub = pref_rating_wsub(nbd_on_axis, nbd_pred_in_room, sm_pred_in_room)
        if not skip_full:
            pref = pref_rating(nbd_on_axis, nbd_pred_in_room, lfx_hz, sm_pred_in_room)
        if rounded:
            ratings = {
                'nbd_on_axis': round(nbd_on_axis, 2),
                'nbd_listening_window': round(nbd_listening_window, 2),
                'nbd_sound_power': round(nbd_sound_power, 2),
                'nbd_pred_in_room': round(nbd_pred_in_room, 2),
                'sm_pred_in_room': round(sm_pred_in_room, 2),
                'sm_sound_power': round(sm_sound_power, 2),
                'pref_score_wsub': round(pref_wsub, 1),
            }
            if not skip_full:
                ratings['aad_on_axis'] = round(aad_on_axis, 2)
                if lfx_hz is not None:
                    ratings['lfx_hz'] = int(pow(10, lfx_hz)) # in Hz
                if lfq_db is not None:
                    ratings['lfq'] =  round(lfq_db, 2)
                ratings['pref_score'] = round(pref, 1)
        else:
            ratings = {
                'nbd_on_axis': nbd_on_axis,
                'nbd_listening_window': nbd_listening_window,
                'nbd_sound_power': nbd_sound_power,
                'nbd_pred_in_room':nbd_pred_in_room,
                'sm_pred_in_room': sm_pred_in_room,
                'sm_sound_power': sm_sound_power,
                'pref_score_wsub': pref_wsub,
            }
            if not skip_full:
                ratings['aad_on_axis'] = aad_on_axis,
                if lfx_hz is not None:
                    ratings['lfx_hz'] = pow(10, lfx_hz)
                if lfq_db is not None:
                    ratings['lfq'] =  lfq_db
                ratings['pref_score'] = pref
        logging.info('Ratings: {0}'.format(ratings))
        return ratings
    except ValueError as e:
        logging.error('{0}'.format(e))
        return None


def scores(df_speaker):
    spin  = df_speaker['CEA2034_unmelted']
    splH  = df_speaker['SPL Horizontal_unmelted']
    splV  = df_speaker['SPL Vertical_unmelted']
    pir   = estimated_inroom_HV(splH, splV)
    return speaker_pref_rating(graph_melt(spin), graph_melt(pir))
