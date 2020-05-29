import logging
import pandas as pd

def parse_graphs_speaker_rewstextdump(speaker_brand, speaker_name):
    dfs = {}
    try:
        spin = None
        freqs = []
        spls = []
        msrts = []
        for txt, msrt in (('DI', 'Sound Power DI'),
                          ('ER', 'Early Reflections'),
                          ('LW', 'Listening Window'),
                          ('On Axis', 'On Axis'),
                          ('SP', 'Sound Power'),
                          ('ERDI', 'Early Reflections DI')):
            filename = 'datas/Vendors/{0}/{1}/{2}.txt'.format(speaker_brand, speaker_name, txt)
            with open(filename, 'r') as f:
                lines = f.readlines()
                for l in lines:
                    if len(l)>0 and l[0] == '*':
                        continue
                    words = l.split()
                    if len(words) == 3:
                        freq = float(words[0])
                        spl  = float(words[1])
                        # phase = float(words[2])
                        freqs.append(freq)
                        spls.append(spl)
                        msrts.append(msrt)
        spin = pd.DataFrame({'Freq': freqs, 'dB': spls, 'Measurements': msrts})    
        dfs['CEA2034'] = spin
    except FileNotFoundError:
        logging.info('Speaker: {0} Not found: {1}'.format(speaker_brand, speaker_name))
    return dfs
        
    
