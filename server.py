from os import path
from threading import Thread

import dask.dataframe as ddf

import geopandas as gpd

from spatialpandas import GeoDataFrame

import pandas as pd
import datashader as ds
import fastparquet as fp

from flask import Flask, send_file, request, jsonify
from flask_cors import CORS

import boto3
from copy import copy

import datashader.transfer_functions as tf
from datashader.transfer_functions import shade
from datashader.transfer_functions import stack

from datashader.colors import Elevation
from datashader.colors import inferno
from datashader.colors import viridis
from datashader.colors import Greys9
from datashader.colors import Hot
from datashader.colors import Set1
from datashader.colors import Set2
from datashader.colors import Set3
from datashader.colors import Sets1to3

from pyproj import Proj, transform

app = Flask(__name__)
CORS(app)

s3 = boto3.client('s3')


cities = gpd.read_file('s3://makepath-reference/reference.gpkg',
                       layer='cities')

lngs, lats = transform(Proj(init='epsg:3857'),
                       Proj(init='epsg:4326'),
                       cities['geometry'].x.values,
                       cities['geometry'].y.values)

cities['latitude'] = lats
cities['longitude'] = lngs
cities['zoom'] = 9
cities['name'] = cities['CITY_NAME']

def load_census_demo():
    print('Loading Census Data')
    parquet_file = fp.ParquetFile(path.expanduser('~/census.parq'))
    df = parquet_file.to_pandas()
    df.race = df.race.astype('category')
    return df


def load_kinsa():
    print('Loading Kinsa Data')
    county_df = gpd.read_file(path.expanduser('~/kinsa_geometry.gpkg'),
                              layer='county')
    oneday_df = ddf.read_csv('s3://makepath-demo/kinsa/one_day.csv').compute()
    oneday_df['region_id'] = oneday_df['region_id'].astype(str).str.zfill(5)
    county_df['GEOID'] = county_df['GEOID'].astype(str).str.zfill(5)

    fields = ['GEOID', 'geometry', 'forecast_upper']
    county_df = county_df.join(oneday_df.set_index('region_id'), on='GEOID')[fields]
    return GeoDataFrame(county_df, geometry='geometry')

# should be read from s3 listing to find buckets with `tileshader.yml` file and then create the dictionary form that.
# dict(<s3_bucket>: dict(df, geometry, span)
datasets = {
    'census-demo': dict(df=load_census_demo(), geometry='point', span=None, name='Census Synthetic People'),
    'makepath-kinsa':  dict(df=load_kinsa(), geometry='polygon', span='min/max', name='Kinsa')
}

colors = {
    'race': dict((('w', 'aqua'),
             ('b', 'lime'),
             ('a', 'red'),
             ('h', 'fuchsia'),
             ('o', 'yellow'))),
    'inferno': inferno,
    'viridis': viridis,
    'elevation': Elevation,
    'greys9': Greys9,
    'hot': Hot,
    'set1': Set1,
    'set2': Set2,
    'set3': Set3,
    'sets1to3': Sets1to3,
    'hotspots': list(reversed(['#d53e4f', '#fc8d59',
                          '#fee08b', '#ffffbf', "#e6f598",
                          '#99d594', '#3288bd']))
}


def invert_y_tile(y, z):
    # Convert from TMS to Google tile y coordinate, and vice versa
    return (2 ** z) - 1 - y


# TODO: change name from source to definition
class MercatorTileDefinition(object):
    ''' Implementation of mercator tile source
    In general, tile sources are used as a required input for ``TileRenderer``.
    Parameters
    ----------
    x_range : tuple
      full extent of x dimension in data units
    y_range : tuple
      full extent of y dimension in data units
    max_zoom : int
      A maximum zoom level for the tile layer. This is the most zoomed-in level.
    min_zoom : int
      A minimum zoom level for the tile layer. This is the most zoomed-out level.
    max_zoom : int
      A maximum zoom level for the tile layer. This is the most zoomed-in level.
    x_origin_offset : int
      An x-offset in plot coordinates.
    y_origin_offset : int
      An y-offset in plot coordinates.
    initial_resolution : int
      Resolution (plot_units / pixels) of minimum zoom level of tileset
      projection. None to auto-compute.
    format : int
      An y-offset in plot coordinates.
    Output
    ------
    tileScheme: MercatorTileSource
    '''

    def __init__(self, x_range, y_range, tile_size=256, min_zoom=0, max_zoom=30,
                 x_origin_offset=20037508.34, y_origin_offset=20037508.34,
                 initial_resolution=156543.03392804097):
        self.x_range = x_range
        self.y_range = y_range
        self.tile_size = tile_size
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.x_origin_offset = x_origin_offset
        self.y_origin_offset = y_origin_offset
        self.initial_resolution = initial_resolution
        self._resolutions = [self._get_resolution(z) for z in range(self.min_zoom, self.max_zoom+1)]

    def to_ogc_tile_metadata(self, output_file_path):
        '''
        Create OGC tile metadata XML
        '''
        pass


    def to_esri_tile_metadata(self, output_file_path):
        '''
        Create ESRI tile metadata JSON
        '''
        pass


    def is_valid_tile(self, x, y, z):

        if x < 0 or x >= math.pow(2, z):
            return False

        if y < 0 or y >= math.pow(2, z):
            return False

        return True


    # TODO ngjit?
    def _get_resolution(self, z):
        return self.initial_resolution / (2 ** z)


    def get_resolution_by_extent(self, extent, height, width):
        x_rs = (extent[2] - extent[0]) / width
        y_rs = (extent[3] - extent[1]) / height
        return [x_rs, y_rs]


    def get_level_by_extent(self, extent, height, width):
        x_rs = (extent[2] - extent[0]) / width
        y_rs = (extent[3] - extent[1]) / height
        resolution = max(x_rs, y_rs)

        # TODO: refactor this...
        i = 0
        for r in self._resolutions:
            if resolution > r:
                if i == 0:
                    return 0
                if i > 0:
                    return i - 1
            i += 1
        return (i-1)


    def pixels_to_meters(self, px, py, level):
        res = self._get_resolution(level)
        mx = (px * res) - self.x_origin_offset
        my = (py * res) - self.y_origin_offset
        return (mx, my)


    def meters_to_pixels(self, mx, my, level):
        res = self._get_resolution(level)
        px = (mx + self.x_origin_offset) / res
        py = (my + self.y_origin_offset) / res
        return (px, py)


    def pixels_to_tile(self, px, py, level):
        tx = math.ceil(px / self.tile_size)
        tx = tx if tx == 0 else tx - 1
        ty = max(math.ceil(py / self.tile_size) - 1, 0)
        # convert from TMS y coordinate
        return (int(tx), invert_y_tile(int(ty), level))


    def pixels_to_raster(self, px, py, level):
        map_size = self.tile_size << level
        return (px, map_size - py)


    def meters_to_tile(self, mx, my, level):
        px, py = self.meters_to_pixels(mx, my, level)
        return self.pixels_to_tile(px, py, level)


    def get_tiles_by_extent(self, extent, level):

        # unpack extent and convert to tile coordinates
        xmin, ymin, xmax, ymax = extent
        # note y coordinates are reversed since they are in opposite direction to meters
        txmin, tymax = self.meters_to_tile(xmin, ymin, level)
        txmax, tymin = self.meters_to_tile(xmax, ymax, level)

        # TODO: vectorize?
        tiles = []
        for ty in range(tymin, tymax + 1):
            for tx in range(txmin, txmax + 1):
                if self.is_valid_tile(tx, ty, level):
                    t = (tx, ty, level, self.get_tile_meters(tx, ty, level))
                    tiles.append(t)

        return tiles


    def get_tile_meters(self, tx, ty, level):
        ty = invert_y_tile(ty, level) # convert to TMS for conversion to meters
        xmin, ymin = self.pixels_to_meters(tx * self.tile_size, ty * self.tile_size, level)
        xmax, ymax = self.pixels_to_meters((tx + 1) * self.tile_size, (ty + 1) * self.tile_size, level)
        return (xmin, ymin, xmax, ymax)


class DataSource:
    @classmethod
    def from_json(props):
        src = DataSource()
        for k, v in props.items():
            if hasattr(src, k):
                setattr(src, k, v)
            else:
                raise ValueError('Invalid JSON attribute: {}'.format(k))


tile_def = MercatorTileDefinition(x_range=(-20037508.34, 20037508.34),
                                  y_range=(-20037508.34, 20037508.34))


def freezeargs(func):
    """Transform mutable dictionnary
    Into immutable
    Useful to be compatible with cache
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        args = tuple([frozendict(arg) if isinstance(arg, dict) else arg for arg in args])
        kwargs = {k: frozendict(v) if isinstance(v, dict) else v for k, v in kwargs.items()}
        return func(*args, **kwargs)
    return wrapped


def create_agg(dataset, xfield, yfield, zfield, agg_func, x, y, z, height=256, width=256):

    xmin, ymin, xmax, ymax = tile_def.get_tile_meters(x, y, z)

    cvs = ds.Canvas(plot_width=width,
                    plot_height=height,
                    x_range=(xmin, xmax),
                    y_range=(ymin, ymax))

    if zfield == 'None':
        zfield = None

    if dataset['geometry'] == 'point':
        if zfield:
            return cvs.points(dataset['df'], xfield, yfield, getattr(ds, agg_func)(zfield))
        else:
            return cvs.points(dataset['df'], xfield, yfield)

    elif dataset['geometry'] == 'polygon':
        if zfield:
            return cvs.polygons(dataset['df'], xfield, agg=getattr(ds, agg_func)(zfield))
        else:
            return cvs.polygons(dataset['df'], xfield)


def create_tile(dataset_name, xfield, yfield, zfield, agg_func, cmap, how, z, x, y):
    '''
    span: dict<zoom_level_int:(min_value, max_value)
    cmap: 
    '''
    import numpy as np
    global datasets
    dataset = datasets[dataset_name]
    agg = create_agg(dataset, xfield, yfield, zfield, agg_func, x, y, z)
    span = dataset.get('span')

    if isinstance(cmap, dict):
        return tf.shade(agg, color_key=cmap)
    else:
        if span:
            if span == 'min/max':
                return tf.shade(agg, cmap=cmap, how=how, span=(np.nanmin(dataset['df'][zfield]),
                                                               np.nanmax(dataset['df'][zfield])))
        else:
            return tf.shade(agg, cmap=cmap, how=how)


def _upload_tile(img, bucket, url):
    s3.upload_fileobj(img, bucket, url,
                      ExtraArgs={'ACL': 'public-read',
                                 'ContentType': 'image/png'})


@app.route('/<dataset>/tile/<xfield>/<yfield>/<zfield>/<agg_func>/<cmap>/<how>/<z>/<x>/<y>')
def tile(dataset, xfield, yfield, zfield, agg_func, cmap, how, z, x, y):
    x = int(x)
    y = int(y)
    z = int(z)

    img = create_tile(dataset, xfield, yfield, zfield, agg_func, colors[cmap], how, z, x, y).to_bytesio()
    url = f'tile/{xfield}/{yfield}/{zfield}/{agg_func}/{cmap}/{how}/{z}/{x}/{y}'

    thread = Thread(target=_upload_tile, args=(copy(img), dataset, url))
    thread.daemon = True
    thread.start()

    return send_file(img, mimetype='image/png')


@app.route('/datasets')
def get_datasets():

    resp = [{'key':'census-demo',
             'text':'Synthetic People',
             'value':'census-demo/tile/meterswest/metersnorth',
             'fields': [{'key':'None','text':'None','value':'None'},
                        {'key':'race','text':'Race / Ethnicity','value':'race'}]},
             {'key':'makepath-kinsa',
              'text':'Kinsa Forecast',
              'value':'makepath-kinsa/tile/geometry/geometry',
              'fields': [{'key':'forecast_upper',
                          'text':'Upper Forecast',
                          'value':'forecast_upper'}]}]
    return jsonify(resp)


@app.route('/scenes')
@app.route('/scenes/count')
def get_scenes(count=10):
    cities = cities[cities['FIPS_CNTRY'] == 'US'].nlargest(count, 'POP')
    outfields = ['zoom', 'latitude', 'longitude', 'name']
    return jsonify(cities[outfields].to_dict(orient='records'))

if __name__ == "__main__":
    app.run(host='0.0.0.0')
