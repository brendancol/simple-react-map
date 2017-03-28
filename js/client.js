import React from "react";
import ReactDOM from "react-dom";
import { render } from 'react-dom';
import { Map, Marker, Popup, TileLayer, GeoJSON } from 'react-leaflet';
import ReactCSSTransitionGroup from 'react-addons-css-transition-group';
import geojson from 'json-loader!./ucdmc_building_footprints_wgs84.geojson';

class SimpleMap extends React.Component {

  constructor() {
    super();

    const cities = [{
        "city": "UC Davis Medical Center", 
        "growth_from_2000_to_2013": "24.5%", 
        "latitude": 38.5547161, 
        "longitude": -121.4579738, 
        "population": "603488", 
        "rank": "30", 
        "state": "Nevada"
    }];

    this.state = {
      location_index: 0,
      cities: cities,
      buildings: geojson,
      zoom: 17,
      transferFunction: 'count',
      city_lat: cities[0].latitude,
      city_lng: cities[0].longitude,
      city_title: cities[0].city,
      tile_url:'http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    };

    // setInterval(this.nextLocation, 1000 * 60);
    document.onkeydown = this.onKeyDown;
  }





  nextLocation = () => {

    const leafletMap = this.leafletMap.leafletElement;
    leafletMap.eachLayer(function(layer) {
        if (layer.hasOwnProperty('_image')) {
          layer.setOpacity(0);
        }
    });

    var nextCityIndex = (this.state.location_index + 1) % this.state.cities.length;
    var nextCityTitle = this.state.cities[nextCityIndex].city;
    var nextCityLat = this.state.cities[nextCityIndex].latitude;
    var nextCityLng = this.state.cities[nextCityIndex].longitude;
    var nextCityPopulation = parseInt(this.state.cities[nextCityIndex].population).toLocaleString();

    this.setState({
      location_index: nextCityIndex,
      city_lat: nextCityLat,
      city_lng: nextCityLng,
      city_title: nextCityTitle,
      population: nextCityPopulation
    });

    this.render();

  }

  previousLocation = () => {
    const leafletMap = this.leafletMap.leafletElement;
    leafletMap.eachLayer(function(layer) {
        if (layer.hasOwnProperty('_image')) {
          layer.setOpacity(0);
        }
    });

    var nextCityIndex = (this.state.location_index - 1) % this.state.cities.length;
    if (nextCityIndex < 0) {
      nextCityIndex = this.state.cities.length - (Math.abs(nextCityIndex) % this.state.cities.length);
    }

    var nextCityTitle = this.state.cities[nextCityIndex].city;
    var nextCityLat = this.state.cities[nextCityIndex].latitude;
    var nextCityLng = this.state.cities[nextCityIndex].longitude;
    var nextCityPopulation = parseInt(this.state.cities[nextCityIndex].population).toLocaleString();

    this.setState({
      location_index: nextCityIndex,
      city_lat: nextCityLat,
      city_lng: nextCityLng,
      city_title: nextCityTitle,
      population: nextCityPopulation
    });

    this.render();

  }

  onKeyDown = (e) => {
    e = e || window.event;
    switch(e.which || e.keyCode) {
        case 82: // r
        setInterval(this.nextLocation, 1000 * 20);
        break;

        case 84: // t
        if (this.state.transferFunction === 'cat') {
          this.setState({transferFunction:'count'});
          this.leafletMap.leafletElement.trigger('moveend');
          console.log('count');
        } else {
          this.setState({transferFunction:'cat'});
          this.leafletMap.leafletElement.trigger('moveend');
          console.log('cat');
        }

        this.setState({transferFunction:'cat'});
        break;

        case 37: // left
        this.previousLocation();
        break;

        case 39: // right
        this.nextLocation();
        break;

        default:
        return;
    }
    e.preventDefault();
  }

componentDidMount() {
  const leafletMap = this.leafletMap.leafletElement;
  //leafletMap.dragging.disable();
  //leafletMap.touchZoom.disable();
  //leafletMap.doubleClickZoom.disable();
  //leafletMap.scrollWheelZoom.disable();
  //leafletMap.boxZoom.disable();
  leafletMap.keyboard.disable();
}


onEachFeature = (feature, layer) => {
  const popupContent = `<h3>${feature.properties.BldgName}</h3>`;
  layer.bindPopup(popupContent);
}


  render() {

    const position = [this.state.city_lat, this.state.city_lng];

    var title_styles = {
      position: 'absolute',
      zIndex: 10000,
      top: 0,
      right: 0,
      backgroundColor: 'black',
      background:'rgba(0,0,0,0.4)',
      color: 'white',
      paddingLeft: '30px',
      paddingRight: '30px',
      paddingTop: 0,
      paddingBottom: 0,
      margin: 0,
      textAlign: 'right'
    };

    var small_text = {
      fontSize:'9pt',
      letterSpacing: '3px',
      margin:0,
      paddingTop: '6px',
      paddingBottom: '6px'
    };

    return (
      <div>

        <Map center={position}
             zoom={this.state.zoom}
             zoomControl={false}
             ref={m => { this.leafletMap = m; }}>

          <TileLayer
            url={this.state.tile_url}
            attribution={this.state.attribution}
            opacity={.7}
          />
          <GeoJSON
            data={this.state.buildings || ""}
            onEachFeature={this.onEachFeature}
          />

        </Map>


      </div>

    );

  }


}

ReactDOM.render(<SimpleMap />, document.getElementById('app'));
