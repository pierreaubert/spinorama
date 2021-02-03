#                                                  -*- coding: utf-8 -*-
# taken somewhere, find reference, check license

import math

class Biquad:

  # pretend enumeration
  LOWPASS, HIGHPASS, BANDPASS, PEAK, NOTCH, LOWSHELF, HIGHSHELF = range(7)

  type2name = {
    LOWPASS: ['Lowpass', 'LP'],
    HIGHPASS: ['Highpass', 'HP'],
    BANDPASS: ['Bandpath', 'BP'],
    PEAK: ['Peak', 'PK'],
    NOTCH: ['Notch', 'NO'],
    LOWSHELF: ['Lowshelf', 'LS'],
    HIGHSHELF: ['Highshelf', 'HS'],
  }

  def __init__(self, typ, freq, srate, Q, dbGain=0):
    types = {
      Biquad.LOWPASS : Biquad.lowpass,
      Biquad.HIGHPASS : Biquad.highpass,
      Biquad.BANDPASS : Biquad.bandpass,
      Biquad.PEAK : Biquad.peak,
      Biquad.NOTCH : Biquad.notch,
      Biquad.LOWSHELF : Biquad.lowshelf,
      Biquad.HIGHSHELF : Biquad.highshelf
    }
    if typ not in types:
      raise AssertionError
    self.typ = typ
    self.freq = float(freq)
    self.srate = float(srate)
    self.Q = float(Q)
    self.dbGain = float(dbGain)
    self.a0 = self.a1 = self.a2 = 0
    self.b0 = self.b1 = self.b2 = 0
    self.x1 = self.x2 = 0
    self.y1 = self.y2 = 0
    # only used for peaking and shelving filter types
    A = math.pow(10, dbGain / 40)
    omega = 2 * math.pi * self.freq / self.srate
    sn = math.sin(omega)
    cs = math.cos(omega)
    alpha = sn / (2*Q)
    beta = math.sqrt(A + A)
    types[typ](self,A, omega, sn, cs, alpha, beta)
    # prescale constants
    self.b0 /= self.a0
    self.b1 /= self.a0
    self.b2 /= self.a0
    self.a1 /= self.a0
    self.a2 /= self.a0

  def lowpass(self,A, omega, sn, cs, alpha, beta):
    self.b0 = (1 - cs) /2
    self.b1 = 1 - cs
    self.b2 = (1 - cs) /2
    self.a0 = 1 + alpha
    self.a1 = -2 * cs
    self.a2 = 1 - alpha

  def highpass(self, A, omega, sn, cs, alpha, beta):
    self.b0 = (1 + cs) /2
    self.b1 = -(1 + cs)
    self.b2 = (1 + cs) /2
    self.a0 = 1 + alpha
    self.a1 = -2 * cs
    self.a2 = 1 - alpha

  def bandpass(self, A, omega, sn, cs, alpha, beta):
    self.b0 = alpha
    self.b1 = 0
    self.b2 = -alpha
    self.a0 = 1 + alpha
    self.a1 = -2 * cs
    self.a2 = 1 - alpha

  def notch(self, A, omega, sn, cs, alpha, beta):
    self.b0 = 1
    self.b1 = -2 * cs
    self.b2 = 1
    self.a0 = 1 + alpha
    self.a1 = -2 * cs
    self.a2 = 1 - alpha

  def peak(self, A, omega, sn, cs, alpha, beta):
    self.b0 = 1 + (alpha * A)
    self.b1 = -2 * cs
    self.b2 = 1 - (alpha * A)
    self.a0 = 1 + (alpha /A)
    self.a1 = -2 * cs
    self.a2 = 1 - (alpha /A)

  def lowshelf(self, A, omega, sn, cs, alpha, beta):
    self.b0 = A * ((A + 1) - (A - 1) * cs + beta * sn)
    self.b1 = 2 * A * ((A - 1) - (A + 1) * cs)
    self.b2 = A * ((A + 1) - (A - 1) * cs - beta * sn)
    self.a0 = (A + 1) + (A - 1) * cs + beta * sn
    self.a1 = -2 * ((A - 1) + (A + 1) * cs)
    self.a2 = (A + 1) + (A - 1) * cs - beta * sn

  def highshelf(self, A, omega, sn, cs, alpha, beta):
    self.b0 = A * ((A + 1) + (A - 1) * cs + beta * sn)
    self.b1 = -2 * A * ((A - 1) + (A + 1) * cs)
    self.b2 = A * ((A + 1) + (A - 1) * cs - beta * sn)
    self.a0 = (A + 1) - (A - 1) * cs + beta * sn
    self.a1 = 2 * ((A - 1) - (A + 1) * cs)
    self.a2 = (A + 1) - (A - 1) * cs - beta * sn

  # perform filtering function
  def __call__(self, x):
    y = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2 - self.a1 * self.y1 - self.a2 * self.y2
    self.x2 = self.x1
    self.x1 = x
    self.y2 = self.y1
    self.y1 = y
    return y
    
  # provide a static result for a given frequency f
  def result(self, f):
    phi = (math.sin(math.pi * f * 2/(2*self.srate)))**2
    r =((self.b0+self.b1+self.b2)**2 - \
    4*(self.b0*self.b1 + 4*self.b0*self.b2 + \
    self.b1*self.b2)*phi + 16*self.b0*self.b2*phi*phi) / \
    ((1+self.a1+self.a2)**2 - 4*(self.a1 + 4*self.a2 + \
    self.a1*self.a2)*phi + 16*self.a2*phi*phi)
    if(r < 0):
      r = 0
    return r**(.5)

  # provide a static log result for a given frequency f
  def log_result(self, f):
    try:
      r = 20 * math.log10(self.result(f))
    except:
      r = -200
    return r

  # return computed constants
  def constants(self):
    return self.a1, self.a2, self.b0, self.b1, self.b2

  def type2str(self, short=True):
    if short is True:
      return self.type2name[self.typ][1]
    else:
      return self.type2name[self.typ][0]

    
  def __str__(self):
    return "Type:%s,Freq:%.1f,Rate:%.1f,Q:%.1f,Gain:%.1f" % (self.type2str(),self.freq,self.srate,self.Q,self.dbGain)
