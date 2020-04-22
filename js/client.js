import React from "react";
import ReactDOM from "react-dom";
import { render } from 'react-dom';
import { Map, Marker, Popup, TileLayer, ImageOverlay } from 'react-leaflet';
import ReactCSSTransitionGroup from 'react-addons-css-transition-group';
import { Dropdown, Menu } from 'semantic-ui-react'
import { Slider } from "react-semantic-ui-range";



class SimpleMap extends React.Component {

  constructor() {
    super();

    this.state = {
      location_index: 0,
      cities: null,
      zoom: 11,
      transferFunction: 'count',
      hows: [{'key':'eq_hist','text':'Histogram Equalization','value':'eq_hist'},
             {'key':'linear','text':'Linear','value':'linear'},
             {'key':'log','text':'Log','value':'log'},
             {'key':'cbrt','text':'Cube Root','value':'cbrt'}],
      aggs: [{'key':'mean','text':'Mean','value':'mean'},
             {'key':'count_cat','text':'Categorical Count','value':'count_cat'},
             {'key':'sum','text':'Sum','value':'sum'},
             {'key':'max','text':'Maximum','value':'max'}],
      datasets: null,
      dataset: null,
      field: '',
      colors: [{'key':'inferno','text':'Inferno','value':'inferno'},
               {'key':'viridis','text':'Viridis','value':'viridis'},
               {'key':'hot','text':'Hot','value':'hot'},
               {'key':'race','text':'Race Categories','value':'race'},
               {'key':'elevation','text':'Elevation','value':'elevation'},
               {'key':'set1','text':'Set 1','value':'set1'},
               {'key':'set2','text':'Set 2','value':'set2'},
               {'key':'set3','text':'Set 3','value':'set3'},
               {'key':'greys9','text':'Greys','value':'greys9'}],
      agg: 'mean',
      how: 'eq_hist',
      color: 'inferno',
      city_lat: 0,
      city_lng: 0,
      city_title: '',
      tile_url:'http://tile.stamen.com/toner/{z}/{x}/{y}@2x.png',
      dataLoaded: false, 
      dynspread: 0,
      sliderSettings: {
        onChange: this.onChangeDynspreadSlider,
        start: 0,
        min: 0,
        max: 5,
        step: 1
      },
      active_transforms: [],
      transforms: [{'key':'hillshade','text':'Hillshade','value':'hillshade'},
                   {'key':'quantile','text':'Quantile','value':'quantile'}],
    };

    // setInterval(this.nextLocation, 1000 * 60);
    document.onkeydown = this.onKeyDown;
  }

  componentDidMount() {

    fetch('http://3.22.132.191:8080/datasets')
      .then(response => response.json())
      .then((data) => {
        this.setState({datasets:data,
                       dataset:data[0],
                       fields:data[0].fields,
                       dataLoaded:true,
                       field:data[0].fields[0].value})
  
          this.setupMapHandlers();
      });

    fetch('http://3.22.132.191:8080/scenes')
      .then(response => response.json())
      .then((data) => {
        this.setState({cities:data,
                       city_lat: data[0].latitude,
                       city_lng: data[0].longitude,
                       city_title: data[0].name,
        
        });
      });
  }

  nextLocation = () => {

    const leafletMap = this.leafletMap.leafletElement;
    leafletMap.eachLayer(function(layer) {
        if (layer.hasOwnProperty('_image')) {
          layer.setOpacity(0);
        }
    });

    var nextCityIndex = (this.state.location_index + 1) % this.state.cities.length;
    var nextCityTitle = this.state.cities[nextCityIndex].name;
    var nextCityLat = this.state.cities[nextCityIndex].latitude;
    var nextCityLng = this.state.cities[nextCityIndex].longitude;
    var nextCityZoom = parseInt(this.state.cities[nextCityIndex].zoom);

    this.setState({
      location_index: nextCityIndex,
      city_lat: nextCityLat,
      city_lng: nextCityLng,
      city_title: nextCityTitle,
      zoom: nextCityZoom,
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
    var nextCityZoom = parseInt(this.state.cities[nextCityIndex].zoom);

    this.setState({
      location_index: nextCityIndex,
      city_lat: nextCityLat,
      city_lng: nextCityLng,
      city_title: nextCityTitle,
      population: nextCityPopulation,
      zoom: nextCityZoom,
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

  onChangeHow = (e, data) => {
    this.setState({how: data.value});
    console.log(e);
  }


  onChangeAdditionalTransforms = (e, { value }) => {
    this.setState({ active_transforms: value });
  };


  onChangeAgg = (e, data) => {
    this.setState({agg: data.value});
    console.log(e);
  }

  onChangeDatasetChange = (e, data) => {

    let d = this.state.datasets.filter(function(item){
      return item.value === data.value;
    })[0];

    this.setState({dataset: d,
                   field: d.fields[0].value});
    console.log(e);
  }

  onChangeColors = (e, data) => {
    this.setState({color: data.value});
    console.log(e);
  }

  onChangeField = (e, data) => {
    this.setState({field: data.value});
    console.log(e);
  }

  onChangeDynspreadSlider = (e) => {
    let value = parseInt(e);
    this.setState({dynspread: value});
  };

  toOptions = (objectArray) => {

    const allowed = ['text', 'value', 'key'];

    return objectArray.map(option => Object.keys(option)
                                           .filter(key => allowed.includes(key))
                                           .reduce((obj, key) => {
                                             obj[key] = option[key];
                                             return obj;
                                           }, {}))
    }

  setupMapHandlers() {
    const leafletMap = this.leafletMap.leafletElement;
    //leafletMap.dragging.disable();
    //leafletMap.touchZoom.disable();
    //leafletMap.doubleClickZoom.disable();
    //leafletMap.scrollWheelZoom.disable();
    //leafletMap.boxZoom.disable();
    leafletMap.keyboard.disable();

    leafletMap.on('zoomstart', () => {
      leafletMap.eachLayer(function(layer) {
          if (layer.hasOwnProperty('_image')) {
            layer.setOpacity(0);
          }
      });
    });

    leafletMap.on('movestart', () => {
      leafletMap.eachLayer(function(layer) {
          if (layer.hasOwnProperty('_image')) {
            layer.setOpacity(0);
          }
      });

    });



    leafletMap.on('moveend', () => {

      leafletMap.eachLayer(function(layer) {
          if (layer.hasOwnProperty('_image')) {
            var width = leafletMap.getSize()['x'].toString();
            var height = leafletMap.getSize()['y'].toString();
            var xmin = window.L.CRS.EPSG3857.project(leafletMap.getBounds()._southWest)['x'].toString();
            var ymin = window.L.CRS.EPSG3857.project(leafletMap.getBounds()._southWest)['y'].toString();
            var xmax = window.L.CRS.EPSG3857.project(leafletMap.getBounds()._northEast)['x'].toString();
            var ymax = window.L.CRS.EPSG3857.project(leafletMap.getBounds()._northEast)['y'].toString();
            var bounds = [xmin, ymin, xmax, ymax].join(',');
            /*

            var nurl = `http://localhost:5000/census?width=${width}&height=${height}&bounds=${bounds}`;
            layer.setBounds(leafletMap.getBounds());
            layer.setUrl(nurl);
            layer.on('load', function() {
              layer.setOpacity(1);
            });
            */

          }
      });

    });
  }


  render() {

    if (!this.state.dataLoaded) {
      return null;
    }

    const position = [this.state.city_lat, this.state.city_lng];

    var title_styles = {
      position: 'absolute',
      zIndex: 10000,
      top: 0,
      left: 0,
      right: 0,
      backgroundColor: 'black',
      background:'rgba(0,0,0,0.4)',
      color: 'white',
      marginLeft: '10px',
      marginRight: '10px',
      marginTop: '10px',

      margin: 0,
      textAlign: 'left'
    };

    var main_menu = {
      background:'rgba(0,0,0,0.4)',
    };

    var logo_styles = {
      position: 'fixed',
      zIndex: 10000,
      bottom: '20px',
      left: '20px',
      background:'rgba(0,0,0,0.0)',
      paddingLeft: '10px',
      paddingRight: '10px',
      paddingTop: 0,
      paddingBottom: 0,
      margin: 0,
      width: 250,
      textAlign: 'left'
    };
    var logo_styles2 = {
      position: 'fixed',
      zIndex: 10000,
      bottom: '20px',
      left: '20px',
      background:'rgba(0,0,0,0.0)',
      paddingLeft: '10px',
      paddingRight: '10px',
      paddingTop: 0,
      paddingBottom: 0,
      margin: 0,
      width: 250,
      textAlign: 'left',
      filter: 'blur(5px)'
    };

    var small_text = {
      fontSize:'9pt',
      letterSpacing: '3px',
      margin:0,
      paddingTop: '6px',
      paddingBottom: '6px'
    };

    var dynspreadSliderStyle = {
      position: 'fixed',
      zIndex: 10000,
      bottom: '20px',
      right: '20px',
      background:'rgba(0,0,0,0.0)',
      paddingLeft: '10px',
      paddingRight: '10px',
      paddingTop: 0,
      paddingBottom: 0,
      margin: 0,
      width: 250,
    }

    let tile_url = `http://3.22.132.191:8080/${this.state.dataset.value}/${this.state.field}`; 
    tile_url += `/${this.state.agg}/${this.state.color}/${this.state.how}/{z}/{x}/{y}/${this.state.dynspread}`;

    if (this.state.active_transforms.length > 0) {
      tile_url += `/${this.state.active_transforms.join(',')}`;
    } else {
      tile_url += `/None`;
    }

      return (
      <div>

        <Map center={position}
             zoom={this.state.zoom}
             zoomControl={false}
             ref={m => { this.leafletMap = m; }}>

          <TileLayer
            attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            url={this.state.tile_url}
            opacity={.1}
          />

          <TileLayer
            url={tile_url}
            opacity={1}
          />

        </Map>

        <div style={title_styles}>
     <Menu size='huge' inverted>

        <h1 style={{margin:0, marginLeft:6, marginTop:6}}>{this.state.dataset.text}</h1>

        <Menu.Menu position='right' >
          <Dropdown item placeholder='Dataset'
                    value={this.state.dataset.value} search selection options={this.toOptions(this.state.datasets)} onChange={this.onChangeDatasetChange} />
          <Dropdown item placeholder='Column' value={this.state.field} search selection options={this.toOptions(this.state.dataset.fields)} onChange={this.onChangeField} />
          <Dropdown item placeholder='Aggregate How?' value={this.state.agg} search selection options={this.state.aggs} onChange={this.onChangeAgg} />
          <Dropdown item placeholder='Color Map' value={this.state.color} search selection options={this.state.colors} onChange={this.onChangeColors} />
          <Dropdown item placeholder='Shade How?' search selection  value={this.state.how} options={this.state.hows} onChange={this.onChangeHow} />
          <Dropdown item placeholder='Additional Transforms' multiple selection  values={this.state.active_transforms} options={this.state.transforms} onChange={this.onChangeAdditionalTransforms} />

        </Menu.Menu>
      </Menu>
        </div>

          <img style={logo_styles} id="logo" src="https://secureservercdn.net/198.71.233.197/hb9.c63.myftpupload.com/wp-content/uploads/2020/01/cropped-makepath_Logo-2.png" />
          <img style={logo_styles2} id="logo" src="https://secureservercdn.net/198.71.233.197/hb9.c63.myftpupload.com/wp-content/uploads/2020/01/cropped-makepath_Logo-2.png" />
        <Slider className="dynspreadSlider" discrete color="red" style={dynspreadSliderStyle}settings={this.state.sliderSettings} />
        </div>

      )
    }
  }


ReactDOM.render(<SimpleMap />, document.getElementById('app'));
