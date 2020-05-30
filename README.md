# Spinorama : a library to display speaker frequency response and similar graphs
[Spinorama](https://github.com/pierreaubert/spinorama/workflows/Spinorama/badge.svg?branch=master)

This library provides an easy way to view, compare or analyse speakers data. This can help you take informed
decision when buying a speaker instead of relying on commercial information or internet buzz.

## Jump to the [gallery](https://pierreaubert.github.com/spinorama) of all speakers measurements.

# What is a spinorama set of graphs?

It is a way to understand quickly a speaker properties.

Here is an example:

![image](https://github.com/pierreaubert/spinorama/blob/develop/datas/pictures/ex-Genelec-8341A-cea2034.png)

- On Axis: this the frequency response. You expect it to be as flat as possible after 100Hz.
- Listening Window: an average of various measurements around on axis. Expected to be close to the previous one.
- Sound power DI: expected to be a smooth, slowy growing line.

The speaker above is *very* good.

Please read this [post](https://www.audiosciencereview.com/forum/index.php?threads/jbl-305p-mkii-and-control-1-pro-monitors-review.10811/) 
to get a better insight on how to analyse a spinorama.

# Features

## Import

The library support 4 kinds of data:
1. ASR format provided by a [Klippel NFS](https://www.klippel.de/products/rd-system/modules/nfs-near-field-scanner.html): a set of CSV files
2. Princeton 3D3A files: they are IR data in [hdf5](https://www.hdfgroup.org/solutions/hdf5/) format
3. Scanned data from a picture with [WebPlotDigitizer](https://automeris.io/WebPlotDigitizer/) (takes 10 minutes per picture)
4. Export in text form from [REW](https://www.roomeqwizard.com/)

## Computations

1. Generate CEA2034 data from horizontal and vertical SPL data
2. Calculate contour plot, radar plot, isolines and isobands.
3. Estimate basic data for a speaker (-3dB output, flatness over a range)
4. Compute various parameters defined in a paper from Olive (ref. below).

## Generation

1. Webpages digestable on mobile but also on very large 4k screens
2. Graphs are interactive
3. Comparison between speakers
4. Some statistics


# Other ways to look at the graphs in a more interactive way.

## Linux or Mac user

### Using python3, ipython and Jupyter-Lab

```
pip3 install -r requirements.txt 
```
pip3 may also be pip depending on your system.

```
jupiter-lab &
```

Your browser will open, click on spinorama.ipynb and play around.

## Linux or Mac developer

You are very welcome to submit pull requests. Note that the license is GPLv3.

```
pip3 install -r requirements.txt 
pip3 install -r requirements-tests.txt 
```

For saving picture, you need either chromedriver or a set of nodejs packages
Linux:
```
apt install chromedriver
```
Mac:
```
brew install chromedriver
```
Both:
```
npm install vega-lite vega-cli canvas
```

Please add tests and
```
export PYTHONPATH=src
pytest --cov=src
```

## How to add a speaker?

0. Clone the repository with git.

1. Add your data

   a. it depends where your data come from:
      - if from ASR
        - add the unzip files to *datas/ASR/name of speaker/all text* files
      - if from Princeton/3d3a 
        - add the 2 IR files to *datas/Princeton/name of speaker/*, i have normally done all of them.
      - if you only have a picture of the spinorama:
        - please use WebPlotDigitizer to generate a parsed json file
        - add it to *datas/Vendors* if it comes from the manufacturers.
        - a complete [tutorial](tutorial/digitalization/Digitalisation-Tutorial.md) is available.

   b. add a picture of the speaker in datas/originals
   c. test it works with:
      - if from ASR
        - ```./generate_graphs --origin=ASR --speaker='name of speaker'```
      - if from a Vendor with brand Great
        - ```./generate_graphs --origin='Vendors/Great' --speaker='name of speaker'```
      - visualize results
        - ```docs/name of speaker/origin/default/CEA2034_large.png``` or
	- ```docs/name of speaker/origin/default/2cols_large.png```

2. Generate datas and webpages

   - ```sh .generate_docs.sh``` will generate both graphs and website. All files will end up in the ```docs``` directory`. This directory is ignored by git on the develop branch.

3. Add your files to git and push to github on master branch

   - ```git status``` you should see a long list of files that git doesn't now about yet.
   - ```git add all new files```
   - ```git commit -m 'add data for new speaker name' -a```
   - ```git push```


# Source of data and citations

## [AudioScienceReview *aka* ASR](https://www.audiosciencereview.com)
ASR is a fantastic source of speakers data thanks to [amirm@](https://www.audiosciencereview.com/forum/index.php?threads/a-bit-about-your-host.1906/). They also have a lot of data about DACs that you may found useful. There is little correlation between price and quality in the audio world and this data gives some objective criteria to decide what to buy.

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

## Speakers manufacturers.

- If you are a manufacturer of speakers, it would be great if you could provide spinorama datas.
- Manufactures with good datas usually in speaker's manual:
  - JBL
  - Revel
  - Genelec
  - Adam
  - Eve Audio
  - Buscard Audio
  - KEF
  - JTR




