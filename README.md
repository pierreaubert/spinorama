# Spinorama : a library to display speaker frequency response and similar graphs

[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://gitHub.com/pierreaubert/spinorama/graphs/commit-activity)
[![Website www.spinorama.org](https://img.shields.io/website-up-down-green-red/http/shields.io.svg)](https://www.spinorama.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![DeepSource](https://deepsource.io/gh/pierreaubert/spinorama.svg/?label=active+issues&show_trend=true)](https://deepsource.io/gh/pierreaubert/spinorama/?ref=repository-badge)
[![Spinorama Python](https://github.com/pierreaubert/spinorama/actions/workflows/pythonapp.yml/badge.svg?branch=develop)](https://github.com/pierreaubert/spinorama/actions/workflows/pythonapp.yml)
[![Spinorama Javascript](https://github.com/pierreaubert/spinorama/actions/workflows/webapp.yml/badge.svg?branch=develop)](https://github.com/pierreaubert/spinorama/actions/workflows/webapp.yml)

This library provides an easy way to view, compare or analyse speakers
data. This can help you take informed
decision when buying a speaker instead of relying on commercial
information or internet buzz. There are enough measurements now that
you can do statistical analysis if you wanted too.

## Jump to the [gallery](https://www.spinorama.org) of all (1000+) speakers measurements.

# What is a spinorama set of graphs?

It is a way to understand quickly a speaker properties, how it will sound.

Here is an example:

![image](https://www.spinorama.org/speakers/Genelec%208341A/ASR/asr-vertical/CEA2034.jpg)

- On Axis: this the frequency response. You expect it to be as flat as possible after 100Hz.
- Listening Window: an average of various measurements around on axis. Expected to be close to the previous one.
- Sound power DI: expected to be a smooth, slowy growing line.

The speaker above is _very_ good.

Please read:

- this [post on ASR](https://www.audiosciencereview.com/forum/index.php?threads/jbl-305p-mkii-and-control-1-pro-monitors-review.10811/) by [Amir Majidimehr](https://www.linkedin.com/in/amir-majidimehr-0014a75/).
  to get a better insight on how to analyse a spinorama.
- or this [post on Audioholics](https://www.audioholics.com/loudspeaker-design/understanding-loudspeaker-measurements) by [James Larson](https://www.audioholics.com/authors/james-larson)
- this [Objective Loudspeaker Measurements to Predict Subjective Preferences?](https://www.audioholics.com/loudspeaker-design/measure-loudspeaker-performance) from [Dr. Floyd Toole](https://www.linkedin.com/in/floydtoole/) and [Gene DellaSala](https://www.audioholics.com/authors/gene-dellasala) on Audioholics too.

Or if you prefer videos, there is a nice set from [ErinsAudioCorner](https://www.youtube.com/channel/UCW_IqM21u0J-zsKtCq4Gj2w):

1. [What Is Frequency Response? || Understanding the Measurements Part 1](https://www.youtube.com/watch?v=dltza-EGtCg)
2. [Off-Axis vs On-Axis Response || Understanding the Measurements Part 2](https://www.youtube.com/watch?v=j_-b6A1xJaw)
3. [What the heck is SPINORAMA?! || Understanding the Measurements Part 3](https://www.youtube.com/watch?v=b3hYn02uBog)
4. [Predicting Loudspeaker Performance In YOUR Room || Understanding the Measurements Part 4](https://www.youtube.com/watch?v=qmBit3GWSWE)
5. [Loudspeaker Compression || Understanding the Measurements Part 5](https://www.youtube.com/watch?v=6YY71Wqv2u0&t=2s)

# Features

## Import capabilities

The library support four different formats of data:

1. [Klippel NFS](https://www.klippel.de/products/rd-system/modules/nfs-near-field-scanner.html)
   format: a set of CSV files. Various variants of the data format are
   supported via scripts that allows to convert one format to another.
2. Princeton 3D3A files: they are IR data in [hdf5](https://www.hdfgroup.org/solutions/hdf5/) format.
3. Scanned data from a picture with [WebPlotDigitizer](https://automeris.io/WebPlotDigitizer/).
4. Export in text form from [REW](https://www.roomeqwizard.com/)
5. GLL data files are also (weakly) supported. If you want access to
   the automation, then please drop an email. GLL viewer is a Windows
   only application and the automation is based on Windows automation.

## Computations

1. Generate CEA2034 data from horizontal and vertical SPL data.
2. Calculate contour plots, radar plots, isolines and isobands.
3. Estimate basic data for a speaker (-3dB output, flatness over a range, etc)
4. Compute various parameters defined in a paper from Olive (ref. below).
5. It can generate an EQ to optimise the speaker (and get a better
   preference score also called Olive score) based on anechoic
   data. Note: this is not yet a room correction software. EQ can be
   PEQ based but it also can generate a solution for a hardware
   graphical EQ.
6. It can compute the effect of an EQ (IIR) on the spinorama.

## Website generation

1. Webpages digestable on mobile but also on very large 4k screens.
2. Graphs are interactive.
3. Comparison between speakers is possible.
4. Some statistics.
5. All generated EQs are easily accessible.
6. You can find similar speakers at a lower price point.

# Other ways to look at the graphs in a more interactive way.

If you want to generate the graphs yourself or play with the data you need to install the software. Please see
the dedicated [INSTALL section](./tutorial/INSTALL.md).

# How to add a speaker to the database.

Please see the dedicated [tutorial](./tutorial/ADDSPEAKER.md).

# How to use the software.

Please see the dedicated [manual](./tutorial/HOWTOUSE.md).

# Source of data and citations

## [AudioScienceReview _aka_ ASR](https://www.audiosciencereview.com)

ASR is a fantastic source of speakers data thanks to [amirm@](https://www.audiosciencereview.com/forum/index.php?threads/a-bit-about-your-host.1906/). They also have a lot of data about DACs that you may found useful. There is little correlation between price and quality in the audio world and this data gives some objective criteria to decide what to buy. You can [support ASR](https://www.audiosciencereview.com/forum/index.php?threads/how-to-support-audio-science-review.8150/).

## [ErinsAudioCorner _aka_ EAC](https://www.erinsaudiocorner.com/)

Erin is a motivated person reviewing speakers and doing an outstanging
jobs. He also has a [Youtube
channel](https://youtube.com/c/ErinsAudioCorner). You can also
[support him](https://www.erinsaudiocorner.com/contribute/).

## [3D3A](https://www.princeton.edu/3D3A/) is a research organisation at [Princeton](https://www.princeton.edu).

- They provide a database of speaker measurements ([manual](https://www.princeton.edu/3D3A/Manuals/3D3A_Directivity_Database.pdf))
- Some scientific papers I have used:
  - Metrics for Constant Directivity ([abstract](https://www.princeton.edu/3D3A/Publications/Sridhar_AES140_CDMetrics.html), [paper](https://www.princeton.edu/3D3A/Publications/Sridhar_AES140_CDMetrics.pdf), [poster](https://www.princeton.edu/3D3A/Publications/Sridhar_AES140_CDMetrics-poster.pdf))
    - Authors: Sridhar, R., Tylka, J. G., Choueiri, E. Y.
    - Publication: 140th Convention of the Audio Engineering Society (AES 140)
    - Date: May 26, 2016
  - A Database of Loudspeaker Polar Radiation Measurements ([abstract](https://www.princeton.edu/3D3A/Publications/Tylka_AES139_3D3ADirectivity.html), )
  - On the Calculation of Full and Partial Directivity Indices ([abstract](https://www.princeton.edu/3D3A/Publications/Tylka_3D3A_DICalculation.html))
    - Authors: Tylka, J. G., Choueiri, E. Y.
    - Publication: 3D3A Lab Technical Report #1
    - Date: November 16, 2014

## Books and research papers

- [Sound Reproduction: The Acoustics and Psychoacoustics of Loudspeakers and Rooms](https://books.google.ch/books/about/Sound_Reproduction.html?id=tJ0uDwAAQBAJ&printsec=frontcover&source=kp_read_button&redir_esc=y#v=onepage&q&f=false) By Floyd E. Toole
- Standard Method of Measurement for In-Home Loudspeakers is available for free at [CTA](https://www.cta.tech)
- A Multiple Regression Model for Predicting Loudspeaker Preference Using Objective Measurements: Part II - Development of the Model by Sean E. Olive, AES Fellow. Convention paper 6190 from the [AES](https://www.aes.org).
- Fast Template Matching. J.P.Lewis [pdf](http://scribblethink.org/Work/nvisionInterface/vi95_lewis.pdf)
- Farina, A. “Simultaneous Measurement of Impulse Response and Distortion with a Swept-Sine Technique,” Presented at the AES 108th Convention, Feb. 2000.
- Hatziantoniou, P. D. and Mourjopoulos, J. N. “Generalized Fractional-Octave Smoothing of Audio and Acoustic Responses,” J. Audio Eng. Soc., 48(4):259–280, 2000.

Some papers related to finding the optimal IIR filters: I used a different algorithm but that's interesting to read.
- Ramos, G., and Lopez, J. (2006). “Filter design method for loudspeaker equalization based on IIR parametric filters,” J. Audio Eng. Soc. 54(12), 1162–1178.
- Vairetti, Giacomo & Sena, Enzo & Catrysse, Michael & Jensen, Søren & Moonen, Marc & Waterschoot, Toon. (2018). An Automatic Design Procedure for Low-order IIR Parametric Equalizers. Journal of the Audio Engineering Society. 66. 935-952. 10.17743/jaes.2018.0049.
- Equalization of loudspeaker response using balanced model truncation, Xiansheng Li, Zhibo Cai, Chengshi Zheng, et al.

## Speakers manufacturers.

- If you are a manufacturer of speakers, it would be great if you could provide spinorama datas. Send me an email pierre@spinorama.org.
- Manufactures with good datas usually in speaker's manual:
  - Adam Audio
  - Arendal Sound
  - Ascend Acoustic
  - Buscardt Audio
  - DB Audiotechnik
  - Devialet
  - Eve Audio
  - Fulcrum Acoustic
  - Genelec
  - GGNTKT
  - JBL
  - JTR
  - KEF
  - Meyer Sound
  - Neumann
  - Perlisten
  - PSI Audio
  - Revel
  - RCF
  - Sigberg Audio
