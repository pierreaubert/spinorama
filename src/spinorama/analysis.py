import math
from scipy.optimize import curve_fit
import numpy as np

def flinear(x,a,b):
    return np.log(x)*a+b

def fconst(x,a):
    return a

def estimates(onaxis):

    xdata1 = np.array(onaxis.loc[onaxis['Freq']<60].Freq)
    ydata1 = np.array(onaxis.loc[onaxis['Freq']<60].dB)

    popt1, pcov1 = curve_fit(flinear, xdata1, ydata1)
    
    xdata2 = np.array(onaxis.loc[onaxis['Freq']>=100].Freq)
    ydata2 = np.array(onaxis.loc[onaxis['Freq']>=100].dB)

    popt2, pcov2 = curve_fit(fconst, xdata2, ydata2)

    inter   = math.exp((popt2[0]-popt1[1])/popt1[0])
    inter_3 = math.exp((popt2[0]-popt1[1]-3)/popt1[0])
    inter_6 = math.exp((popt2[0]-popt1[1]-6)/popt1[0])

    # search band up/down
    up = ydata2.max()-popt2[0]
    down = ydata2.min()-popt2[0]

    return [int(inter), int(inter_3), int(inter_6), math.floor(max(up, -down)*10)/10]
