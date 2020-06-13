import logging
from math import log10
import numpy as np
import pandas as pd


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

# same weigths with multiples keys, this helps when merging dataframes
sp_weigths_hv = {}
for k,v in sp_weigths.items():
    sp_weigths_hv[k] = v
    sp_weigths_hv['{0}_h'.format(k)] = v
    sp_weigths_hv['{0}_v'.format(k)] = v


def spl2pressure(spl: float) -> float:
    # convert SPL to pressure
    try:
        p = pow(10, (spl-105.0)/20.0)
        return p
    except TypeError as e:
        print('spl={0} e={1}'.format(spl, e))
        logging.error('spl={0} e={1}'.format(spl, e))


def pressure2spl(p: float) -> float:
    # convert pressure back to SPL
    if p<0.0:
        print('pressure is negative')
    return 105.0+20.0*log10(p)


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

def spatial_average(sp_window, func='rms'):
    sp_cols = sp_window.columns
    if 'Freq' not in sp_cols:
        logging.debug('Freq is not in sp_cols')
        return None
    if len(sp_window) < 2:
        logging.debug('Len window is {0}'.format(len(sp_window)))
        return None
    
    result = pd.DataFrame({
        'Freq': sp_window.Freq,
    })
    
    def weighted_rms(spl):
        avg = [sp_weigths_hv[c] * spl[c]**2 for c in sp_cols if column_valid(c)]
        wsm = [sp_weigths_hv[c] for c in sp_cols if column_valid(c)]
        return np.sqrt(np.sum(avg)/np.sum(wsm))

    def rms(spl):
        avg = [spl[c]**2 for c in sp_cols if column_valid(c)]
        n = len(avg)
        # hack
        if n == 0:
            return 0.000000001
        r = np.sqrt(np.sum(avg)/n)
        return r

    if func == 'rms':
        result['dB'] = sp_window\
            .drop(columns=['Freq'])\
            .apply(spl2pressure)\
            .apply(rms, axis=1)\
            .apply(pressure2spl)
    elif func == 'weighted_rms':
        result['dB'] = sp_window\
            .drop(columns=['Freq'])\
            .apply(spl2pressure)\
            .apply(weighted_rms, axis=1)\
            .apply(pressure2spl)

    return result.reset_index(drop=True)


def spatial_average1(spl, sel, func='rms'):
    if spl is None:
        return None
    spl_window = spl[[c for c in spl.columns if c in sel]]
    if 'Freq' not in spl_window.columns:
        logging.debug('Freq not in spl_window')
        return None
    return spatial_average(spl_window, func)


def spatial_average2(h_spl: pd.DataFrame, h_sel, 
                     v_spl: pd.DataFrame, v_sel,
                     func='rms') -> pd.DataFrame:
    if v_spl is None and h_spl is None:
        return None
    if v_spl is None:
        return spatial_average1(h_spl, h_sel, func)
    if h_spl is None:
        return spatial_average1(v_spl, v_sel, func)
    h_spl_sel = h_spl[[c for c in h_spl.columns if c in h_sel]]
    v_spl_sel = v_spl[[c for c in v_spl.columns if c in v_sel]]
    sp_window = h_spl_sel.merge(v_spl_sel, left_on='Freq', right_on='Freq', suffixes=('_h', '_v'))
    return spatial_average(sp_window, func)


def sound_power(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    # Sound Power
    # The sound power is the weighted rms average of all 70 measurements,
    # with individual measurements weighted according to the portion of the
    # spherical surface that they represent. Calculation of the sound power
    # curve begins with a conversion from SPL to pressure, a scalar magnitude.
    # The individual measures of sound pressure are then weighted according
    # to the values shown in Appendix C and an energy average (rms) is
    # calculated using the weighted values. The final average is converted
    # to SPL.      
    h_cols = h_spl.columns
    v_cols = v_spl.columns #.drop(['On Axis', '180°'])
    for to_be_dropped in ['On Axis', '180°']:
        if to_be_dropped in v_cols:
            v_cols = v_cols.drop([to_be_dropped])
    return spatial_average2(h_spl, h_cols, v_spl, v_cols, 'weighted_rms')


def listening_window(h_spl, v_spl):
    if v_spl is None or h_spl is None:
        return None
    return spatial_average2(
        h_spl, ['Freq', '10°', '20°', '30°', '-10°', '-20°', '-30°'],
        v_spl, ['Freq', 'On Axis', '10°', '-10°'])


def total_early_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.Series:
    if v_spl is None or h_spl is None:
        return None
    return spatial_average2(
        h_spl, ['Freq', 'On Axis',
                 '10°',  '20°',  '30°',  '40°',  '50°',  '60°',  '70°',  '80°',  '90°',
                '-10°', '-20°', '-30°', '-40°', '-50°', '-60°', '-70°', '-80°', '-90°',
                '180°'],
        v_spl, ['Freq', 'On Axis',
                '-20°',  '-30°', '-40°',
                '40°',  '50°', '60°']
    )


def early_reflections(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    if v_spl is None or h_spl is None:
        return None
    floor_bounce = spatial_average1(
        v_spl, ['Freq', '-20°',  '-30°', '-40°'])

    ceiling_bounce = spatial_average1(
        v_spl, ['Freq', '40°',  '50°', '60°'])

    front_wall_bounce = spatial_average1(
        h_spl, ['Freq', 'On Axis', '10°',  '20°', '30°', '-10°',  '-20°', '-30°'])

    side_wall_bounce = spatial_average1(
        h_spl, ['Freq', '-40°',  '-50°',  '-60°',  '-70°',  '-80°', '40°',  '50°',  '60°',  '70°',  '80°'])

    rear_wall_bounce = spatial_average1(
        h_spl, ['Freq', '-90°', '90°',  '180°'])

    total_early_reflection = total_early_reflections(h_spl, v_spl)

    er = pd.DataFrame({
        'Freq': h_spl.Freq,
    }).reset_index(drop=True)
    
    for (key, name) in [
        ('Floor Bounce', floor_bounce),
        ('Ceiling Bounce', ceiling_bounce),
        ('Front Wall Bounce', front_wall_bounce),
        ('Side Wall Bounce', side_wall_bounce),
        ('Rear Wall Bounce', rear_wall_bounce),
        ('Total Early Reflection', total_early_reflection),
        ]:
        if name is not None:
            er[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))
    return er.reset_index(drop=True)


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

    vr = pd.DataFrame({'Freq': v_spl.Freq, 'On Axis': v_spl['On Axis']}).reset_index(drop=True)

    # print(vr.shape, onaxis.shape, floor_reflection.shape)
    for (key, name) in [('Floor Reflection', floor_reflection),
                        ('Ceiling Reflection', ceiling_reflection)]:
        if name is not None:
            vr[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))

    return vr.reset_index(drop=True)


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
        h_spl, ['Freq', 'On Axis', '10°',  '20°', '30°', '-10°',  '-20°', '-30°' ])

    side = spatial_average1(
        h_spl, ['Freq', '40°',  '50°', '60°', '70°', '80°', '-40°',  '-50°', '-60°', '-70°', '-80°' ])

    rear = spatial_average1(
        h_spl, ['Freq',
                '90°',  '100°', '110°', '120°', '130°', '140°', '150°', '160°', '170°',
                '-90°',  '-100°', '-110°', '-120°', '-130°', '-140°', '-150°', '-160°', '-170°',
                '180°'])

    hr = pd.DataFrame({
        'Freq': h_spl.Freq,
        'On Axis': h_spl['On Axis'],
    }).reset_index(drop=True)
    for (key, name) in [('Front', front), ('Side', side), ('Rear', rear)]:
        if name is not None:
            hr[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))
    return hr.reset_index(drop=True)


def estimated_inroom(lw: pd.DataFrame, er: pd.DataFrame, sp: pd.DataFrame) -> pd.DataFrame:
    if lw is None or er is None or sp is None:
        return None
    # The Estimated In-Room Response shall be calculated using the directivity
    # data acquired in Section 5 or Section 6.
    # It shall be comprised of a weighted average of
    #     12 % Listening Window,
    #     44 % Early Reflections,
    # and 44 % Sound Power.
    # The sound pressure levels shall be converted to squared pressure values
    # prior to the weighting and summation. After the weightings have been
    # applied and the squared pressure values summed they shall be converted
    # back to sound pressure levels.
    key = 'Total Early Reflection'
    if key not in er.keys():
        key = 'dB'

    try:
        # print(lw.dB.shape, er[key].shape, sp.dB.shape)
        # print(lw.dB.apply(spl2pressure))
        # print(er[key].apply(spl2pressure))
        # print(sp.dB.apply(spl2pressure))

        eir = \
            0.12*lw.dB.apply(spl2pressure) + \
            0.44*er[key].apply(spl2pressure) + \
            0.44*sp.dB.apply(spl2pressure)

        # print(eir)

        return pd.DataFrame({
            'Freq': lw.Freq,
            'Estimated In-Room Response': eir.apply(pressure2spl)
        }).reset_index(drop=True)
    except TypeError as e:
        logging.error(e)
        return None


def estimated_inroom_HV(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    if v_spl is None or h_spl is None:
        return None
    lw = listening_window(h_spl, v_spl)
    er = early_reflections(h_spl, v_spl)
    sp = sound_power(h_spl, v_spl)
    return estimated_inroom(lw, er, sp)


def compute_cea2034(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    if v_spl is None or h_spl is None:
        return None
    # average the 2 onaxis
    onaxis = spatial_average2(h_spl, ['Freq', 'On Axis'], v_spl, ['Freq', 'On Axis'])
    spin = pd.DataFrame({
        'Freq': onaxis.Freq,
        'On Axis': onaxis.dB,
    }).reset_index(drop=True)
    lw = listening_window(h_spl, v_spl)
    sp = sound_power(h_spl, v_spl)
    # Early Reflections Directivity Index (ERDI)
    # The Early Reflections Directivity Index is defined as the difference
    # between the listening window curve and the early reflections curve.
    erb = total_early_reflections(h_spl, v_spl)
    erdi = lw.dB - erb.dB
    # add a di offset to mimic other systems
    di_offset = [0 for i in range(0, len(erdi))]
    # Sound Power Directivity Index (SPDI)
    # For the purposes of this standard the Sound Power Directivity Index is defined
    # as the difference between the listening window curve and the sound power curve.
    # An SPDI of 0 dB indicates omnidirectional radiation. The larger the SPDI, the
    # more directional the loudspeaker is in the direction of the reference axis.
    spdi = lw.dB - sp.dB
    for (key, name) in [('Listening Window', lw), ('Sound Power', sp), ('Early Reflections', erb)]:
        if name is not None:
            spin[key] = name.dB
        else:
            logging.debug('{0} is None'.format(key))
    for (key, name) in [('Early Reflections DI', erdi), ('Sound Power DI', spdi), ('DI offset', di_offset)]:
        if name is not None:
            spin[key] = name
        else:
            logging.debug('{0} is None'.format(key))
    return spin.reset_index(drop=True)


def compute_onaxis(h_spl: pd.DataFrame, v_spl: pd.DataFrame) -> pd.DataFrame:
    # 4 cases
    onaxis = None
    if v_spl is None:
        if h_spl is None:
            return None
        else:
            onaxis = spatial_average1(h_spl, ['Freq', 'On Axis'])
    else:
        onaxis = spatial_average1(v_spl, ['Freq', 'On Axis'])

    if onaxis is None:
        return None
    
    df = pd.DataFrame({
        'Freq': onaxis.Freq,
        'On Axis': onaxis.dB,
    })
    return df



    
