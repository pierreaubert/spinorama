import logging
import math
from math import log10
from scipy.stats import linregress
from scipy.optimize import curve_fit
import numpy as np
import pandas as pd


def flinear(x: float, a: float, b: float):
    return np.log(x) * a + b


def fconst(x :float, a: float):
    return a


def estimates(onaxis: pd.DataFrame):
    # TODO doesn't work for Princeton measurements which are valid >500hz
    try:
        xdata1 = np.array(onaxis.loc[onaxis['Freq'] < 60].Freq)
        ydata1 = np.array(onaxis.loc[onaxis['Freq'] < 60].dB)

        popt1, pcov1 = curve_fit(flinear, xdata1, ydata1)

        xdata2 = np.array(onaxis.loc[onaxis['Freq'] >= 100].Freq)
        ydata2 = np.array(onaxis.loc[onaxis['Freq'] >= 100].dB)

        popt2, pcov2 = curve_fit(fconst, xdata2, ydata2)

        inter = math.exp((popt2[0] - popt1[1]) / popt1[0])
        inter_3 = math.exp((popt2[0] - popt1[1] - 3) / popt1[0])
        inter_6 = math.exp((popt2[0] - popt1[1] - 6) / popt1[0])

        # search band up/down
        up: float = ydata2.max() - popt2[0]
        down: float = ydata2.min() - popt2[0]

        return [int(inter), int(inter_3), int(inter_6),
                math.floor(max(up, -down) * 10) / 10]
    except TypeError as te:
        logging.warning('Estimates failed for {0} with {1}'.format(onaxis.shape, te))
        return [-1, -1, -1, -1]
    except ValueError as ve:
        logging.warning('Estimates failed for {0} with {1}'.format(onaxis.shape, ve))
        return [-1, -1, -1, -1]


def spatial_average1(window, sel):
    window_sel = window[[c for c in window.columns if c in sel and c != 'Freq']]
    if len(window_sel.columns) == 0:
        return None
    spa1 = None
    if len(window_sel.columns) == 1:
        spa1 = pd.DataFrame({
            'Freq': window.Freq, 
            'dB': window_sel[0]
        })
    else:
        spa1 = pd.DataFrame({
            'Freq': window.Freq, 
            'dB': window_sel.mean(axis=1)
        })
        
    if spa1.isnull().sum().sum() > 0:
        logging.error(spa1.dropna().shape, spa1.shape, window.shape, window_sel.shape)
        logging.error('Null value in spa1')

    return spa1 #.dropna(inplace=True)


def spatial_average2(h_df, h_sel, v_df, v_sel):
    # some graphs don't have all angles
    h_df_sel = h_df[[c for c in h_df.columns if c in h_sel]]
    v_df_sel = v_df[[c for c in v_df.columns if c in v_sel]]
    # some don't have vertical measurements
    if len(v_df_sel.columns) == 1:
        return spatial_average1(h_df, h_sel)
    # merge both
    window = h_df_sel.merge(v_df_sel, left_on='Freq', right_on='Freq', suffixes=('_h', '_v'))
    spa2 = pd.DataFrame({
        'Freq': window.Freq, 
        'dB': window.loc[:, lambda df: [c for c in df.columns if c != 'Freq']].mean(axis=1)
    })
    # print(spa2.shape, h_df_sel.shape, v_df_sel.shape, window.shape)
    if spa2.isnull().sum().sum() > 0:
        logging.error('Null value in spa2')
    return spa2 # .dropna(inplace=True)


def listening_window(h_spl, v_spl):
    if v_spl is None or h_spl is None:
        return None
    return spatial_average2(
        h_spl, ['Freq', '10°', '20°', '30°'], 
        v_spl, ['Freq', 'On Axis', '10°', '-10°'])
    

def early_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    if v_spl is None or h_spl is None:
        return None
    floor_bounce = spatial_average1(
        v_spl, ['Freq', '-20°',  '-30°', '-40°'])

    ceiling_bounce = spatial_average1(
        v_spl, ['Freq', '40°',  '50°', '60°'])

    front_wall_bounce = spatial_average1(
        h_spl, ['Freq', 'On Axis', '10°',  '20°', '30°'])

    side_wall_bounce = spatial_average1(
        h_spl, ['Freq', '40°',  '50°',  '60°',  '70°',  '80°'])

    rear_wall_bounce = spatial_average1(
        h_spl, ['Freq', '90°',  '180°'])

    er = pd.DataFrame({
        'Freq': listening_window(h_spl, v_spl).Freq,
    })
    for (key, name) in [('Floor Bounce', floor_bounce),
                        ('Ceiling Bounce', ceiling_bounce),
                        ('Front Wall Bounce', front_wall_bounce),
                        ('Side Wall Bounce', side_wall_bounce),
                        ('Rear Wall Bounce', rear_wall_bounce)]:
        if name is not None:
            er[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))
            
    # not sure it is this an average
    if floor_bounce is not None and \
        ceiling_bounce is not None and \
        side_wall_bounce is not None and \
        rear_wall_bounce is not None:
        total = floor_bounce.dB+ceiling_bounce.dB+\
            front_wall_bounce.dB+side_wall_bounce.dB+rear_wall_bounce.dB
        total /= 5.0
        er['Total Early Reflection'] = total
    
    return er


def vertical_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute horizontal reflections

    h_spl: unused
    v_spl: vertical data
    """
    if v_spl is None:
        return None
    floor_reflection = spatial_average1(
        v_spl, ['Freq', '-20°',  '-30°', '-40°'])

    ceiling_reflection = spatial_average1(
        v_spl, ['Freq', '40°',  '50°', '60°'])

    vr = pd.DataFrame({
        'Freq': v_spl.Freq,
        'On Axis': v_spl['On Axis'],
        })
    
    # print(vr.shape, onaxis.shape, floor_reflection.shape)
    for (key, name) in [('Floor Reflection', floor_reflection),
                        ('Ceiling Reflection', ceiling_reflection)]:
        if name is not None:
            vr[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))

    return vr


def horizontal_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    """Compute horizontal reflections

    h_spl: horizontal data
    v_spl: unused
    """
    if h_spl is None:
        return None
    # Horizontal Reflections
    # Front: 0°, ± 10o, ± 20o, ± 30o horizontal
    # Side: ± 40°, ± 50°, ± 60°, ± 70°, ± 80° horizontal
    # Rear: ± 90°, ± 100°, ± 110°, ± 120°, ± 130°, ± 140°, ± 150°, ± 160°, ± 170°, 180°
    # horizontal, (i.e.: the horizontal part of the rear hemisphere).
    front = spatial_average1(
        h_spl, ['Freq', 'On Axis', '10°',  '20°', '30°'])

    side = spatial_average1(
        h_spl, ['Freq', '40°',  '50°', '60°', '70°', '80°'])

    rear = spatial_average1(
        h_spl, ['Freq', '90°',  '100°', '110°', '120°', '130°',
                '140°', '150°', '160°', '170°', '180°'])

    hr = pd.DataFrame({
        'Freq': h_spl.Freq,
        'On Axis': h_spl['On Axis'],
    })
    for (key, name) in [('Front', front), ('Side', side), ('Rear', rear)]:
        if name is not None:
            hr[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))
    return hr


def early_reflections_bounce(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.Series:
    if v_spl is None or h_spl is None:
        return None
    return spatial_average2(
        h_spl, ['Freq', 'On Axis', '10°',  '20°', '30°', '40°',  '50°',  '60°',  '70°',  '80°', '90°',  '180°'],
        v_spl, ['Freq', 'On Axis', '10°', '-10°', '-20°',  '-30°', '-40°', '40°',  '50°', '60°']
    )


# from the standard appendix
# weigth http://emis.impa.br/EMIS/journals/BAG/vol.51/no.1/b51h1san.pdf
sp_weigths = {
    'On Axis': 0.000604486,
       '180°': 0.000604486,
    #
    '10°':   0.004730189,
    '170°':  0.004730189,
    '-170°': 0.004730189,
    '-10°':  0.004730189,
    #
    '20°':   0.008955027,
    '160°':  0.008955027,
    '-160°': 0.008955027,
    '-20°':  0.008955027,
    #
    '30°':   0.012387354,
    '150°':  0.012387354,
    '-150°': 0.012387354,
    '-30°':  0.012387354,
    # 
    '40°':   0.014989611,
    '140°':  0.014989611,
    '-140°': 0.014989611,
    '-40°':  0.014989611,
    # 
    '50°':   0.016868154,
    '130°':  0.016868154,
    '-130°': 0.016868154,
    '-50°':  0.016868154,
    # 
    '60°':   0.018165962,
    '120°':  0.018165962,
    '-120°': 0.018165962,
    '-60°':  0.018165962,
    #
    '70°':   0.019006744,
    '110°':  0.019006744,
    '-110°': 0.019006744,
    '-70°':  0.019006744,
    #
    '80°':   0.019477787,
    '100°':  0.019477787,
    '-100°': 0.019477787,
    '-80°':  0.019477787,
    #
    '90°':   0.019629373,
    '-90°':  0.019629373,
}

def spl2pressure(spl : float) -> float:
    return pow(10,(spl-105)/20)


def pressure2spl(p : float) -> float:
    return 105+20*log10(p)


def sound_power(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    if v_spl is None or h_spl is None:
        return None
    # Sound Power
    # The sound power is the weighted rms average of all 70 measurements,
    # with individual measurements weighted according to the portion of the
    # spherical surface that they represent. Calculation of the sound power
    # curve begins with a conversion from SPL to pressure, a scalar magnitude.
    # The individual measures of sound pressure are then weighted according
    # to the values shown in Appendix C and an energy average (rms) is
    # calculated using the weighted values. The final average is converted
    # to SPL.
    sp_window = h_spl.merge(
        v_spl,
        left_on='Freq', right_on='Freq', suffixes=('_h', '_v')
    )
    sp_cols = sp_window.columns

    def column_trim(c):
        if c[-2:] == '_v' or c[-2:] == '_h':
            return c[:-2]
        return c

    def column_valid(c):
        if c[0] == 'O':
            return True
        elif c[0] == 'F':
            return False
        elif int(column_trim(c)[:-1]) % 10 == 0:
            return True
        return False

    def rms(spl):
        print(len([c for c in sp_cols if column_valid(c)]))
        avg = [(sp_weigths[column_trim(c)] * spl2pressure(spl[c]))**2 for c in sp_cols if column_valid(c)]
        wsm = [sp_weigths[column_trim(c)]**2 for c in sp_cols if column_valid(c)]
        return pressure2spl(np.sqrt(np.sum(avg)/np.sum(wsm)))

    sp_window['rms'] = sp_window.apply(rms, axis=1)
    
    return pd.DataFrame({
        'Freq': sp_window.Freq,
        'dB': sp_window.rms,
    })


def estimated_inroom(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    if v_spl is None or h_spl is None:
        return None
    # The Estimated In-Room Response shall be calculated using the directivity
    # data acquired in Section 5 or Section 6.
    # It shall be comprised of a weighted average of
    #     12 % Listening Window,
    #     44 % Early Reflections,
    # and 44 % Sound Power.
    lw = listening_window(h_spl, v_spl)
    er = early_reflections(h_spl, v_spl)
    sp = sound_power(h_spl, v_spl)
    # The sound pressure levels shall be converted to squared pressure values
    # prior to the weighting and summation. After the weightings have been
    # applied and the squared pressure values summed they shall be converted
    # back to sound pressure levels.
    eir = \
      0.12*lw.dB.apply(spl2pressure) + \
      0.44*er['Total Early Reflection'].apply(spl2pressure) + \
      0.44*sp.dB.apply(spl2pressure)
    
    return pd.DataFrame({
        'Freq': lw.Freq,
        'Estimated In-Room Response': eir.apply(pressure2spl)
        })


def compute_cea2034(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    if v_spl is None or h_spl is None:
        return None
    # average the 2 onaxis
    onaxis = spatial_average2(h_spl, ['Freq', 'On Axis'], v_spl, ['Freq', 'On Axis'])
    spin = pd.DataFrame({
        'Freq': onaxis.Freq,
        'On Axis': onaxis.dB,
    })
    lw = listening_window(h_spl, v_spl)
    sp = sound_power(h_spl, v_spl)
    # Early Reflections Directivity Index (ERDI)
    # The Early Reflections Directivity Index is defined as the difference 
    # between the listening window curve and the early reflections curve.
    # add 60 (graph start at 60)
    erb = early_reflections_bounce(h_spl, v_spl)
    erdi = lw.dB - erb.dB + 60
    # Sound Power Directivity Index (SPDI)
    # For the purposes of this standard the Sound Power Directivity Index is defined
    # as the difference between the listening window curve and the sound power curve.
    # An SPDI of 0 dB indicates omnidirectional radiation. The larger the SPDI, the
    # more directional the loudspeaker is in the direction of the reference axis.
    spdi = lw.dB - sp.dB + 60
    for (key, name) in [('Listening Window', lw), ('Sound Power', sp)]:
        if name is not None:
            spin[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))
    for (key, name) in [('Early Reflections DI', erdi), ('Sound Power DI', spdi)]:
        if name is not None:
            spin[key] = name
        else:
            logging.debug('{0} is None'.format(key))
    return spin


# https://courses.physics.illinois.edu/phys406/sp2017/Lab_Handouts/Octave_Bands.pdf
def octave(N):
    """compute 1/N octave band"""
    p = pow(2,1/N)
    p_band= pow(2,1/(2*N))
    iter = int((N*10+1)/2)
    center = [1000 / p**i for i in range(iter,0,-1)]+[1000*p**i for i in range(0,iter+1,1)]
    return [(c/p_band,c*p_band) for c in center]


def aad(dfu):
    # mean betwenn 200hz and 400hz
    y_ref = np.mean(dfu.loc[(dfu.Freq>=200) & (dfu.Freq<=400)].dB)
    # print(y_ref)
    aad_sum = 0
    n = 0
    # 1/20 octave
    for (omin, omax) in octave(20):
        # 100hz to 16k hz
        if omin < 100:
            continue
        if omax > 16000:
            break
        selection = dfu.loc[(dfu.Freq>=omin) & (dfu.Freq<omax)]
        if selection.shape[0] > 0:
            aad_sum += abs(y_ref-np.mean(selection.dB))
            n += 1
    aad_value = aad_sum/n
    #if math.isnan(aad_value):
    #    pd.set_option('display.max_rows', dfu.shape[0]+1)
    #    print(aad_sum, n, dfu)
    return aad_value

def nbd(dfu):
    sum = 0
    n = 0
    # 1/2 octave
    for (omin, omax) in octave(2):
        # 100hz to 12k hz
        if omin < 100:
            continue
        if omax > 12000:
            break
        y = dfu.loc[(dfu.Freq>=omin) & (dfu.Freq<omax)].dB
        y_avg = np.mean(y)
        # don't sample, take all points in this octave
        sum += np.mean(np.abs(y_avg-y))
        n += 1
    if n == 0:
        logging.error('nbd is None')
        return None
    return sum/n


def lfx(lw, sp):
    y_ref = np.mean(lw.loc[(lw.Freq>=300) & (lw.Freq<=10000)].dB)-6
    # find first freq such that y[freq]<y_ref-6dB
    y = math.log10(sp.loc[(sp.Freq<300)&(sp.dB<=y_ref)].Freq.max())
    return y


def lfq(lw, sp, lfx_log):
    lfx = pow(10,lfx_log)
    sum = 0
    n = 0
    for (omin, omax) in octave(20):
        # 100hz to 12k hz
        if omin < lfx:
            continue
        if omax > 300:
            break
        s_lw = lw.loc[(lw.Freq>=omin) & (lw.Freq<omax)]
        s_sp = sp.loc[(sp.Freq>=omin) & (sp.Freq<omax)]
        if s_lw.shape[0] > 0 and s_sp.shape[0] > 0:
            y_lw = np.mean(s_lw.dB)
            y_sp = np.mean(s_sp.dB)
            sum += abs(y_lw-y_sp)
            n += 1
    return sum/n

def sm(dfu):
    data = dfu.loc[(dfu.Freq>=100) & (dfu.Freq<=16000)]
    slope, intercept, r_value, p_value, std_err = linregress(data.Freq, data.dB)
    return r_value**2
                

def pref_rating(nbd_on, nbd_pir, lfx, sm_pir):
    return 12.69-2.49*nbd_on-2.99*nbd_pir-4.31*lfx+2.32*sm_pir


def speaker_pref_rating(cea2034):
    df_on_axis = cea2034.loc[lambda df: df.Measurements == 'On Axis']
    df_listening_window = cea2034.loc[lambda df: df.Measurements == 'Listening Window']
    df_sound_power = cea2034.loc[lambda df: df.Measurements == 'Sound Power']
    for dfu in (df_on_axis, df_listening_window, df_sound_power):
        if dfu.loc[(dfu.Freq>=100) & (dfu.Freq<=400)].shape[0] == 0:
            logging.info('No freq under 400hz, skipping pref_rating'.format())
            return None
    aad_on_axis = aad(df_on_axis)
    nbd_on_axis = nbd(df_on_axis)
    nbd_listening_window = nbd(df_listening_window)
    nbd_sound_power = nbd(df_sound_power)
    lfx_hz = lfx(df_listening_window, df_sound_power)
    lfq_db = lfq(df_listening_window, df_sound_power, lfx_hz)
    sm_sound_power = sm(df_sound_power)
    pref = pref_rating(nbd_on_axis, nbd_sound_power, lfx_hz, sm_sound_power)
    ratings = {
        'aad_on_axis': round(aad_on_axis, 2),
        'nbd_on_axis': round(nbd_on_axis, 2),
        'nbd_listening_window': round(nbd_listening_window, 2),
        'nbd_sound_power': round(nbd_sound_power, 2),
        'lfx_hz': int(pow(10, lfx_hz)), # in Hz
        'lfq': round(lfq_db, 2),
        'sm_sound_power': round(sm_sound_power, 2),
        'pref_score': round(pref, 1),
    }
    logging.info('Ratings: {0}'.format(ratings))
    return ratings
    
