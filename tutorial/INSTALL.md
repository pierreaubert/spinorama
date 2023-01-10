## Linux or Mac user

First install a few packages:

```
apt install imagemagick npm
```

On a Mac you can replace all `apt` calls by `brew`.

### Using python3, ipython and Jupyter-Lab

```
pip3 install -r requirements.txt
```

pip3 may also be pip depending on your system.

```
export PYTHONPATH=src:src/website
jupiter-lab &
```

Your browser will open, go to _experiments_ directitory and click on _spinorama.ipynb_ and play around.

## Linux or Mac developer

You are very welcome to submit pull requests. Note that the license is GPLv3.

Start with launching that should install a lot of software:

```
./setup.sh
```

If it doesn't work out of the box which is likely, please go step by step:

```
pip3 install -r requirements.txt
pip3 install -r requirements-tests.txt
```

For linting the python, html and javascript code:

```
npm install pyright html-validate standard flow flow-remove-types
```

You may have to update your npm version above 12.0:

```
nvm install lts/fermium
```

Please add tests and

```
export PYTHONPATH=src
python3 -m pytest --cov=src .
```

Before committing, please check that the various checks are fine:

1. `./check_html.sh` : check that HTML generated files are conforming.
2. `./check_meta.py` : check that the metadata file looks sane.
3. `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude spinorama-venv` should report 0
4. `black .` will take care of formatting all the python files.

and also (but WIP):

5. `./check_404.sh` : check we do not have missing links.
6. `./node_modules/.bin/pyright` : should not report new type error.
7. Check that notebook are cleaned up before committing.

Tests 1. to 4. should be in the pre-submit.
