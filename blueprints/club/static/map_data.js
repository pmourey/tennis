mapboxgl.accessToken = 'pk.eyJ1IjoicG1vdXJleSIsImEiOiJjbHZ4dnJ3bGMwNDBzMmlxeXBnZDJtYzVrIn0.yxrohiV1L6c89UY6PvPHGw';

var latitude = document.getElementById('map').getAttribute('data-latitude');
var longitude = document.getElementById('map').getAttribute('data-longitude');
var myLngLat = [parseFloat(longitude), parseFloat(latitude)];


const map = new mapboxgl.Map({
    container: 'map', // container ID
    // Choose from Mapbox's core styles, or make your own style with Mapbox Studio
    style: 'mapbox://styles/mapbox/satellite-streets-v12', // style URL
    center: myLngLat, // starting position [lng, lat]
    zoom: 16 // starting zoom
});

const layerList = document.getElementById('menu');
const inputs = layerList.getElementsByTagName('input');

for (const input of inputs) {
    input.onclick = (layer) => {
        const layerId = layer.target.id;
        map.setStyle('mapbox://styles/mapbox/' + layerId);
    };
}