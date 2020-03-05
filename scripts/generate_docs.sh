echo "Starting Generation"
export PYTHONPATH=src:.
rm -fr docs
mkdir docs docs/assets docs/metadata
python3 ./scripts/generate_graph.py
python3 ./scripts/generate_html.py
./scripts/minimise_pictures.sh
echo "Done"
