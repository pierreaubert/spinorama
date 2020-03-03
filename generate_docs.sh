echo "Starting Generation"
rm -fr docs
mkdir docs docs/assets docs/metadata
cd datas && ./convert.sh
python3 generate_graph.py
python3 generate_docs.py
find docs  -type f -name '*.png' -print | xargs -I % convert % -quality 25 %
echo "Done"
