echo "Starting Generation"
export PYTHONPATH=src:.
rm -fr docs
mkdir docs docs/assets docs/pictures
python3 ./generate_graphs.py
./minimise_pictures.sh
python3 ./generate_meta.py
python3 ./generate_html.py
echo "Done"
