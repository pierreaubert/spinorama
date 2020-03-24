echo "Starting Generation"
export PYTHONPATH=src:.
rm -fr docs
mkdir docs docs/assets docs/pictures
# generates all graphs per speaker
python3 ./generate_graphs.py
# save some space
./minimise_pictures.sh
# all metadata (computed)
python3 ./generate_meta.py
# some stats for all speakers
python3 ./generate_stats.py
# static website generation
python3 ./generate_html.py
echo "Done"
