import datashader as ds
import datashader.transfer_functions as tf

import fastparquet as fp

from flask import Flask, send_file, request

app = Flask(__name__)

parquet_file = fp.ParquetFile('census.parq')
df = parquet_file.to_pandas()
df.race = df.race.astype('category')


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


from functools import lru_cache

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


def create_agg(dataset, x, y, z):
    xmin, ymin, xmax, ymax = tile_def.get_tile_meters(x, y, z)
    width = 256
    height = 256
    cvs = ds.Canvas(plot_width=width,
                    plot_height=height,
                    x_range=(xmin, xmax),
                    y_range=(ymin, ymax))
    return cvs.points(df, 'meterswest', 'metersnorth', ds.count_cat('race'))


@lru_cache(None)
def create_tile(dataset, x, y, z, color_key):

    if isinstance(color_key, tuple):
        color_key = dict(color_key)

    agg = create_agg(dataset, x, y, z)
    img = tf.shade(agg, color_key=color_key, how='eq_hist')
    return img


@app.route('/<dataset>/tile/<z>/<x>/<y>')
def tile(dataset, x, y, z):
    x = int(x)
    y = int(y)
    z = int(z)

    color_key = (('w', 'aqua'),
                 ('b', 'lime'),
                 ('a', 'red'),
                 ('h', 'fuchsia'),
                 ('o', 'yellow'))

    return send_file(create_tile(dataset, x, y, z, color_key).to_bytesio(), mimetype='image/png')


@app.route('/<dataset>')
def serve_image(dataset):

    # parse params
    bounds = request.args.get('bounds')
    xmin, ymin, xmax, ymax = map(float, bounds.split(','))
    width = int(request.args.get('width'))
    height = int(request.args.get('height'))

    # shade image
    cvs = ds.Canvas(plot_width=width,
                    plot_height=height,
                    x_range=(xmin, xmax),
                    y_range=(ymin, ymax))
    agg = cvs.points(df, 'meterswest', 'metersnorth', ds.count_cat('race'))
    img = tf.shade(agg, color_key=color_key, how='eq_hist')
    img_io = img.to_bytesio()
    return send_file(img_io, mimetype='image/png')


if __name__ == "__main__":
    app.run()
