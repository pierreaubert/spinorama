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

Here the generated EQ:
```
EQ for Genelec S360 computed from ASR data
Preference Score 6.3 with EQ 6.8
Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v0.16
Dated: 2022-08-12-13:33:25

Preamp: -3.2 dB

Filter  1: ON PK Fc  1426 Hz Gain +2.58 dB Q 5.04
Filter  2: ON PK Fc  1961 Hz Gain +0.92 dB Q 5.65
Filter  3: ON PK Fc   314 Hz Gain -1.37 dB Q 1.52
Filter  4: ON PK Fc  6648 Hz Gain -0.80 dB Q 5.79
Filter  5: ON PK Fc  1687 Hz Gain +0.83 dB Q 5.94
Filter  6: ON PK Fc  1274 Hz Gain +0.75 dB Q 5.93
Filter  7: ON PK Fc   896 Hz Gain -1.48 dB Q 4.01
Filter  8: ON PK Fc   592 Hz Gain +0.72 dB Q 5.86
Filter  9: ON PK Fc 10314 Hz Gain +0.64 dB Q 0.53
```

Looking at the graphs, you see that the error around the crossover as decreased on the PIR but increased on the LW.
Looking at the EQ, you see that the default Q is 6 which is high.

Let's change both parameters:
```
rm -f docs/speakers/"$SPEAKER"/*/filters_eq.png
./generate_peqs.py --speaker="$SPEAKER" --force --verbose --curves=LW --max-Q=3
```
and results is now:
```
Reading cache ... (loaded 1 speakers)
2022-08-12 13:44:48,353 INFO services.py:1470 -- View the Ray dashboard at http://127.0.0.1:8265
Queing 1 speakers for EQ computations
(optim_save_peq pid=38248)          SPK auEQ
(optim_save_peq pid=38248) -----------------
(optim_save_peq pid=38248) NBD  ON 0.33 0.29
(optim_save_peq pid=38248) NBD  LW 0.31 0.26
(optim_save_peq pid=38248) NBD PIR 0.33 0.25
(optim_save_peq pid=38248) SM  PIR 0.88 0.93
(optim_save_peq pid=38248) SM   SP 0.93 0.96
(optim_save_peq pid=38248) LFX       35   35
(optim_save_peq pid=38248) LFQ     1.26 1.26
(optim_save_peq pid=38248) -----------------
(optim_save_peq pid=38248) Score    6.3  6.7
(optim_save_peq pid=38248) w/sub    7.9  8.4
(optim_save_peq pid=38248) -----------------
(optim_save_peq pid=38248) +6.28 +6.73 Genelec S360
```
Score varied by .1 which is not significative.
![image](https://github.com/pierreaubert/spinorama/blob/develop/tutorial/picts/autoEQ/genelec_s360_v2.png)
and new EQ:
```
EQ for Genelec S360 computed from ASR data
Preference Score 6.3 with EQ 6.7
Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v0.16
Dated: 2022-08-12-13:44:55

Preamp: -2.1 dB

Filter  1: ON PK Fc 10341 Hz Gain +1.03 dB Q 0.71
Filter  2: ON PK Fc  6731 Hz Gain -1.09 dB Q 2.83
Filter  3: ON PK Fc   321 Hz Gain -1.60 dB Q 1.61
Filter  4: ON PK Fc  1596 Hz Gain +1.47 dB Q 3.00
Filter  5: ON PK Fc   875 Hz Gain -1.27 dB Q 3.00
Filter  6: ON PK Fc  1714 Hz Gain -0.64 dB Q 2.99
Filter  7: ON PK Fc 10966 Hz Gain -0.52 dB Q 2.92
Filter  8: ON PK Fc  1385 Hz Gain +1.15 dB Q 2.82
Filter  9: ON PK Fc  2168 Hz Gain +0.76 dB Q 2.97
```

This time the LW is flatter, we still have a bump for the low frequency, and by default autoEQ does not touch frequencies below 120Hz since they will be changed too much by your room.
We also see some small fluctuations of the EQ and it could benefit from some smoothing.
rm -f docs/speakers/"$SPEAKER"/*/filters_eq.png
./generate_peqs.py --speaker="$SPEAKER" --force --verbose --curves=LW --smooth-order=3 --smooth-measurements=11 --max-Q=3 --slope-listening-window=-0.5 --min-freq=40
```
This time the bump at low frequency is gone, EQ is smoother.
![image](https://github.com/pierreaubert/spinorama/blob/develop/tutorial/picts/autoEQ/genelec_s360_v3.png)
and the new EQ v3
```
EQ for Genelec S360 computed from ASR data
Preference Score 6.3 with EQ 6.7
Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v0.16
Dated: 2022-08-12-13:51:41

Preamp: -1.7 dB

Filter  1: ON PK Fc  1741 Hz Gain +1.30 dB Q 1.53
Filter  2: ON PK Fc    59 Hz Gain -1.30 dB Q 0.73
Filter  3: ON PK Fc 10707 Hz Gain +1.12 dB Q 0.59
Filter  4: ON PK Fc   328 Hz Gain -1.03 dB Q 1.93
Filter  5: ON PK Fc   885 Hz Gain -0.80 dB Q 2.91
Filter  6: ON PK Fc  6704 Hz Gain -0.73 dB Q 2.99
Filter  7: ON PK Fc   156 Hz Gain +0.53 dB Q 2.98
Filter  8: ON PK Fc  1352 Hz Gain +0.50 dB Q 2.98
Filter  9: ON PK Fc  8293 Hz Gain +0.50 dB Q 2.97
```
Next step is to see if we can decrease the max Q for the speaker. The lower it is the more likely it will be usefull and less dependant on the speaker itself. Remember that there is fair amount of difference between 2 speakers from the same series. Sometimes manufacturers provide tolerance between 2 speakers but most don't. You do not want to optimise for a speaker which is far from yours. Adding smoothing and lowering the Q should improve the results.

Here are the results with max Q=2:
![image](https://github.com/pierreaubert/spinorama/blob/develop/tutorial/picts/autoEQ/genelec_s360_v4.png)
and EQ v4
```
EQ for Genelec S360 computed from ASR data
Preference Score 6.3 with EQ 6.6
Generated from http://github.com/pierreaubert/spinorama/generate_peqs.py v0.16
Dated: 2022-08-12-13:53:42

Preamp: -1.8 dB

Filter  1: ON PK Fc  1714 Hz Gain +1.31 dB Q 1.72
Filter  2: ON PK Fc    60 Hz Gain -1.31 dB Q 0.69
Filter  3: ON PK Fc 10549 Hz Gain +1.11 dB Q 0.64
Filter  4: ON PK Fc   333 Hz Gain -0.99 dB Q 1.95
Filter  5: ON PK Fc   867 Hz Gain -0.74 dB Q 1.99
Filter  6: ON PK Fc  6753 Hz Gain -0.70 dB Q 1.98
Filter  7: ON PK Fc   155 Hz Gain +0.50 dB Q 1.98
Filter  8: ON PK Fc  1327 Hz Gain +0.57 dB Q 1.98
Filter  9: ON PK Fc  8258 Hz Gain +0.59 dB Q 1.95

```
If you decrease the max Q to 1, then the score doesn't improve. In this case, 2 or 3 looks like to be the correct value. Listening to the various EQ is the best way to see which one your prefer.








