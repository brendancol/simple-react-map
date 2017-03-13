# simple-react-map
Simple Map Scaffolding using React, ES6, Webpack


# Setup Datashader Demo w/ flask server

```bash
# grab the code
git clone git@github.com:brendancol/simple-react-map.git
cd simple-react-map

# install py libs
conda env create
source activate datashader

# install js libs
npm install

# download census parquet file
bash download_census_parquet.sh

# in a separate terminal, run server
python server.py

# in a separate terminal, run client
webpack-dev-server


# if you get an error saying SNAPPY is not available, try:
brew install snappy
pip install python-snappy
```
