# How to use the various sripts?

Hello, welcome to Spinorama. Here is the documentation for the scripts that generates data and pictures (and if you want a copy of the website).

## First time use

Let's try first it installation did work:
```
./generate_graphs.py --help
```
You should see a long help with all the options. If not, please open a ticket [here]() to ask for help.

## Check metadata

```
./check_meta.py
```
Should return 0 and if not will explain to you what is incorrect in the metadata file.
This file is a json file but the checker enforce more constraints.

## Update pictures (of speakers)


```
./update_picture.sh
```

Takes all the pictures of speakers, resizes them and generates multiple formats for web consumption.

## Generate all graphs

```
./generate_graphs.py --help
```
will show you a lot of options. If you start with:
```
./generate_graphs.py --help
```
The script will generate all the graphs for all speakers in parallel. It will use all your CPU for some time (5 min on a large machine, 30 min on a laptop).

### Generate graph for 1 speaker


```
export SPEAKER='Genelec S360'
./generate_graphs.py --speaker="$SPEAKER"
```

will generate all the graphs for the current speaker. Outputs are in `./docs/speakers/$SPEAKER/*'.

## Generate metadata for the website

```
./generate_meta.py
```
generates a metadata file in json format for web consumption. It merges manual data in './data/metadata.py' with computed data.

## Generate statistics for the website

```
./generate_statistics.py
```
generates a metadata file in json format for web consumption. It can also output txt or csv data.


## Generate radar graphs for the website

```
./generate_radar.py
```
generates a picture per speaker showning the improvement to the speaker if you use the automatically computed EQ.


## Generate HTML files


```
./generate_html.py
```

will generate all HTML files. If you want to generate a dev site you can change the default URL with

```
./generate_html.py --dev --sitedev=https://spinorama.internet-box.ch
```
and I usually copy all generated files to where the httpd daemon can use them:
```
rsync -arv --delete docs/* /var/www/html/spinorama/
```


## Generate EQ

Let's focus on 1 speaker for example the Genelec S360.
```
export SPEAKER='Genelec S360'
```

Then let's run the autoEQ:

```
./generate_peqs.py --speaker="$SPEAKER" --force --verbose
```
output should looks like:
```
Reading cache ... (loaded 1 speakers)
2022-08-12 13:33:17,720 INFO services.py:1470 -- View the Ray dashboard at http://127.0.0.1:8265
Queing 1 speakers for EQ computations
(optim_save_peq pid=28676)          SPK auEQ
(optim_save_peq pid=28676) -----------------
(optim_save_peq pid=28676) NBD  ON 0.33 0.32
(optim_save_peq pid=28676) NBD  LW 0.31 0.28
(optim_save_peq pid=28676) NBD PIR 0.33 0.22
(optim_save_peq pid=28676) SM  PIR 0.88 0.95
(optim_save_peq pid=28676) SM   SP 0.93 0.97
(optim_save_peq pid=28676) LFX       35   35
(optim_save_peq pid=28676) LFQ     1.26 1.26
(optim_save_peq pid=28676) -----------------
(optim_save_peq pid=28676) Score    6.3  6.8
(optim_save_peq pid=28676) w/sub    7.9  8.4
(optim_save_peq pid=28676) -----------------
(optim_save_peq pid=28676) +6.28 +6.76 Genelec S360
```

So what's happening?

- The system read the cache of precomputed data for each speaker.
- It start a parallel evaluation running on a Ray cluster (your machine by default)
- Since we are optimising 1 speaker only, it just queued 1 job.
- Results shows the various parameters of the tonality score with and without EQ, with and without a large subwoofer.
- It also generate a picture in './docs/speaker/$SPEAKER/*/filters_eq.png' that shows the current results on the speaker.
![image](https://github.com/pierreaubert/spinorama/blob/develop/tutorial/picts/autoEQ/genelec_s360_v1.png)








