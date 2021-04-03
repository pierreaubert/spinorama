# generate docs
rm -fr ./docs
rm -f *.log */*.log
# sometimes ray left things behind
rm -fr /tmp/ray
# various cache files
rm -fr ./__pycache__ ./*/__pycache__ ./*/*/__pycache__
rm -fr ./.mypy_cache ./*/.mypy_cache ./*/*/.mypy_cache
rm -fr ./.pytest_cache ./*/.pytest_cache ./*/*/.pytest_cache
rm -f cache.*.h5
rm -fr **/results_*.csv
# node stuff
rm -fr ./node_modules
# emacs stuff
rm -f ./TAGS ./*/*/TAGS
rm -f **/.*~ **/.#* **/*~
# python venv
rm -fr spinorama-venv
rm -fr **/*.pyc
rm -fr **/.ipynb_checkpoints
# latex stuff
rm -fr ./book/.pytest_cache ./book/*.aux ./book/*.bbl ./book/*.blg ./book/*.lof ./book/*.out ./book/*.pdf ./book/*.toc ./book/*.back ./book/tmp ./book/*~
# Mac stuff
rm -fr .DS_Store
