def get_speaker_docs_path(metadata, speaker, measurement):
    """ return the path where to store computed datas about a speaker """
    return 'docs/{:s}/'.format(speaker)

def measurement2name(speaker, measurement):
    if 'key' in measurement:
        return '{:s} - {:s} {:s}'.format(speaker, measurement['origin'], measurement['key'])
    else:
        return '{:s} - {:s}'.format(speaker, measurement['origin'])
        

def name2measurement(name):
    return name.split(' - ')
