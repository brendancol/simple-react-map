import datashader as ds
import datashader.transfer_functions as tf
import pandas as pd

from flask import Flask, send_file, request


app = Flask(__name__)
app.debug = True
CACHE = True


df = pd.read_hdf('census.h5', 'census')
df.race = df.race.astype('category')
color_key = {'w': 'aqua',
             'b': 'lime',
             'a': 'red',
             'h': 'fuchsia',
             'o': 'yellow'}

@app.route('/<dataset>')
def serve_image(dataset):

    # parse params
    bounds = request.args.get('bounds')
    xmin, ymin, xmax, ymax =  map(float, bounds.split(','))
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
