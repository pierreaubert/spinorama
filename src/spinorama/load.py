import math
import locale
from locale import atof
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
import pandas as pd
import numpy as np

removequote = str.maketrans({'"': None, '\n': ''})

def graph_melt(df):
    return df.reset_index().melt(id_vars='Freq', var_name='Measurements', value_name='dB').loc[lambda df: df['Measurements'] != 'index']

                                                                            
def parse_graph_freq(filename):
    title = None
    columns = ['Freq']
    usecols = [0]
    with open(filename) as csvfile:
        # first line is graph title
        title = csvfile.readline().split('\t')[0][1:-1]
        # second line is column titles
        csvcolumns = [c.translate(removequote) for c in csvfile.readline().split('\t')]
        # third line is column units
        units = [c.translate(removequote) for c in csvfile.readline().split('\t')]
        # print(units)
        columns.extend([c for c in csvcolumns if len(c)>0])
        # print(columns)
        usecols.extend([1+i*2 for i in range(len(columns)-1)])
        #print(usecols)

    # read all columns, drop 0
    df = pd.read_csv(filename, sep='\t', skiprows=2, usecols=usecols, names=columns, thousands=',').drop(0)
    # convert to float (issues with , and . in numbers)
    df = df.applymap(atof)
    # melt tables
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
        csvfilename = "datas/"+speakerpath+"/"+csv+".txt"
        try:
            title, df = parse_graph_freq(csvfilename)
            # print('Speaker: '+speakerpath+' Loaded: '+title)
            dfs[title] = graph_melt(df)
            dfs[title+'_unmelted']=df
        except FileNotFoundError:
            # print('Speaker: '+speakerpath+' Not found: '+csv)
            pass

    return dfs

def parse_all_speakers():
    speakerlist= [
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
    print('Loading speaker: ')
    for speaker in speakerlist:
        print('  '+speaker+', ')
        df[speaker] = parse_graphs_speaker(speaker)
    return df
    
