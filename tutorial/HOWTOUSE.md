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
```








