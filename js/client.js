import React from "react";
import ReactDOM from "react-dom";
import { render } from 'react-dom';
import { Map, Marker, Popup, TileLayer, ImageOverlay } from 'react-leaflet';



class SimpleMap extends React.Component {

  constructor() {
    super();
    this.state = {
      lat: 51.505,
      lng: -0.09,
      zoom: 13,
    };
  }

  render() {

    const position = [this.state.lat, this.state.lng];


		var params = {
        url: "http://wfs-kbhkort.kk.dk/k101/wms",
				layers: 'k101:theme-startkort',
				format: 'image/png',
				transparent: true,
				version: '1.1.0',
				attribution: "myattribution"
		};

    return (

      <Map center={position} zoom={this.state.zoom}>

        <TileLayer
          attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
          url='http://tile.stamen.com/toner-lite/{z}/{x}/{y}@2x.png'
        />

        <ImageOverlay url='http://www.lib.utexas.edu/maps/historical/newark_nj_1922.jpg' imageBounds={[[40.712216, -74.22655], [40.773941, -74.12544]]} />


      </Map>

    );
}
}

ReactDOM.render(<SimpleMap />, document.getElementById('app'));
