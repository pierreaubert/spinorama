# Spinorama : a library to display Spinorama and similar graphs

What's a spinorama graph? It is a way to understand quickly a speaker properties.

Here is an example:

![image](https://github.com/pierreaubert/spinorama/blob/master/docs/Neumann%20KH%2080/CEA2034.png)

- On Axis: this the frequency response. You expect it to be as flat as possible after 100Hz.
- Listening Window: an average of various measurements around on axis. Expected to be close to the previous one.
- Sound power: expected to be a smooth, slowy growing line.

The speaker above is *very* good.

Please read this [post](https://www.audiosciencereview.com/forum/index.php?threads/jbl-305p-mkii-and-control-1-pro-monitors-review.10811/) 
to get a better insight on how to analyse a spinorama.

# Browse the [gallery](https://pierreaubert.github.com/spinorama) of all ASR speaker measurements.

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
pip3 install -r requirements-tests.txt 
```

Please add tests and
```
pytest
```

