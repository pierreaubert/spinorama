![Spinorama](https://github.com/pierreaubert/spinorama/workflows/Spinorama/badge.svg?branch=master)

# Spinorama : a library to display Spinorama and similar graphs

## Jump to the [gallery](https://pierreaubert.github.com/spinorama) of all speakers measurements.

# What is a spinorama graph?

It is a way to understand quickly a speaker properties.

Here is an example:

![image](https://github.com/pierreaubert/spinorama/blob/master/docs/Neumann%20KH%2080/ASR/default/CEA2034.png)

- On Axis: this the frequency response. You expect it to be as flat as possible after 100Hz.
- Listening Window: an average of various measurements around on axis. Expected to be close to the previous one.
- Sound power DI: expected to be a smooth, slowy growing line.

The speaker above is *very* good.

Please read this [post](https://www.audiosciencereview.com/forum/index.php?threads/jbl-305p-mkii-and-control-1-pro-monitors-review.10811/) 
to get a better insight on how to analyse a spinorama.

# Features

## Import

The library support 3 kinds of data:
1. ASR format provided by klippel: a set of CSV files
2. Princeton 3D3A files: they are IR data in hdf5 format
3. Scanned data from a picture with WebPlotDigitizer (takes 10 minutes per picture)

## Computations

1. Generate CEA2034 data from horizontal and vertical SPL data (in beta)
2. Calculate contour plot, radar plot
3. Estimate basic data for a speaker (-3dB output, flatness over a range)

## Generation

1. Webpages digestable on mobile but also on very large 4k screens
2. Graphs are interactive
4. Comparison between speakers (in beta)

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
      - if you only have a picture of the spinorame:
        - please use WebPlotDigitizer to generate a parsed json file
        - add it to *datas/Vendors* if it comes from the manufacturers.

   b. add a picture of the speaker in datas/originals

2. Generate datas and webpages

   - ```cd datas && ./convert.sh``` will generate a thumbnail picture
   - ```./generate_docs.py``` will generate both graphs and website

3. Add your files to git and push to github on master branch

   - ```git status``` you should see a long list of files that git doesn't now about yet.
   - ```git add all new files```
   - ```git commit -m 'add data for new speaker name' -a```
   - ```git push```


# Source of data and citations

# ASR is a fantastic source of speakers data

# 3D3A is a research organisation at Princeton: they provided a set of measurements.

# Others and gathered from the web and manually translated into graphs.

If you are a manufacturer of speakers, it would be great if you could provide
