import pandas as pd
import locale
from locale import atof

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

removequote = str.maketrans({'"': None, '\n': ''})


def graph_melt(df):
    return df.reset_index().melt(id_vars='Freq', var_name='Measurements',
                                 value_name='dB').loc[lambda df: df['Measurements'] != 'index']


def parse_graph_freq(filename):
    title = None
    columns = ['Freq']
    usecols = [0]
    with open(filename) as csvfile:
        # first line is graph title
        title = csvfile.readline().split('\t')[0][1:-1]
        # second line is column titles
        csvcolumns = [c.translate(removequote)
                      for c in csvfile.readline().split('\t')]
        # third line is column units
        # units = [c.translate(removequote)
        #         for c in csvfile.readline().split('\t')]
        # print(units)
        columns.extend([c for c in csvcolumns if len(c) > 0])
        # print(columns)
        usecols.extend([1 + i * 2 for i in range(len(columns) - 1)])
        # print(usecols)

    # read all columns, drop 0
    df = pd.read_csv(
        filename,
        sep='\t',
        skiprows=2,
        usecols=usecols,
        names=columns,
        thousands=',').drop(0)
    # convert to float (issues with , and . in numbers)
    df = df.applymap(atof)
    # reorder column if we are reading a file with angles (Pandas doesn't care but easier to plot)
    # c: Freq  0 10 -10 20 -20 30 -30 40-40 50 -50 60 -60 70 -70 -80 90 -90 100 -100 110 -110
    #                               120 -120 130 -130 140 -140 150 -150 160 -160 170 -170 180
    # i: 0     1  2   3  4   5  6   7  9 10 11  12 13  14 15  16  17 18  19  20   21  22   23
    #                                24   25  26   27  28   29  30   31  32   33  34   35  36
    # p: 0    18 17  19 16  20 15  22 14 23 13  24 12  25 11  26  10 27   9   28    8  29   7
    #                                 30    6  31    5  32    4  33    3  34    2  35    1 36
    perm = [
        0,
        35,
        33,
        31,
        29,
        27,
        25,
        23,
        21,
        19,
        17,
        15,
        13,
        11,
        9,
        7,
        5,
        3,
        1,
        2,
        4,
        6,
        8,
        10,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
        26,
        28,
        30,
        32,
        34,
        36]

    if len(df.columns) > 2 and df.columns[2] == '10°':
        return title, df[[df.columns[perm[i]] for i in range(0, len(perm))]]
    return title, df


def parse_graphs_speaker(speakerpath):
    dfs = {}
    csvfiles = ["CEA2034",
                "Early Reflections",
                "Directivity Index",
                "Estimated In-Room Response",
                "Horizontal Reflections",
                "Vertical Reflections",
                "SPL Horizontal",
                "SPL Vertical"]
    for csv in csvfiles:
        csvfilename = "datas/" + speakerpath + "/" + csv + ".txt"
        try:
            title, df = parse_graph_freq(csvfilename)
            # print('Speaker: '+speakerpath+' Loaded: '+title)
            dfs[title + '_unmelted'] = df
            dfs[title] = graph_melt(df)
        except FileNotFoundError:
            # print('Speaker: '+speakerpath+' Not found: '+csv)
            pass

    return dfs


def parse_all_speakers():
    speakerlist = [
        "Dayton Audio B652-AIR",
        "Emotiva Airmotive 6s",
        "Harbeth Monitor",
        "JBL 104",
        "KEF LS50",
        "Kali IN-8",
        "Micca RB42",
        "Neumann KH 80",
        "Pioneer SP-BS22-LR",
        "Realistic MC-1000",
        "Revel C52",
        "Selah Audio RC3R",
        "Yamaha HS5"
    ]
    df = {}
    # print('Loading speaker: ')
    for speaker in speakerlist:
        # print('  '+speaker+', ')
        df[speaker] = parse_graphs_speaker(speaker)
    print('Loaded {:2d} speakers'.format(len(speakerlist)))
    return df
