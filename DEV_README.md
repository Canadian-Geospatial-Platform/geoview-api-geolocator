# geoview-api-geolocator

The Canadian Geospatial Platform (CGP) needs the ability to do Geocoding

>Geocoding is the process of converting addresses (like "1600 Amphitheatre Parkway, Mountain View, CA") into geographic coordinates (like latitude 37.423021 and longitude -122.083739), which you can use to place markers on a map, or position the map. Google Maps Geocoding API
There is many different APIs on the market to achieve this task. Each one of them has pros and cons and the use of only one API introduce limitations. The idea is the create a wrapper around many APIs and custom sources of geolocated features to be able to build a standard response for CGP tools to interact with.

__Simple diagram__
![geoview-api-geolocator-diagram](https://user-images.githubusercontent.com/3472990/198357917-ba7cb402-bb81-4e46-b42d-4e00e0bdbf16.png)

[Demo](https://jolevesq.github.io/geoview-api-geolocator/index.html)

Sample call to the API:
```
https://fr59c5usw4.execute-api.ca-central-1.amazonaws.com/dev?q=Meech lake&lang=en&keys=geonames,nominatim
```

html
The demo with embeded viewer is being loaded in public/index.html as a script tag
```
<script src="https://canadian-geospatial-platform.github.io/geoview/public/cgpv-main.js"></script>
```

## Running the project

### First clone this repo

```
$ git clone https://github.com/Canadian-Geospatial-Platform/geoview-api-geolocator.git
```

### Go to the directory of the cloned repo

```
cd geoview-api-geolocator
```

### Install dependencies

```
$ npm install
```

### Run the project

```
$ npm run serve
```

## Building the project

```
$ npm run build
```

## React and React DOM dependencies

These 2 librairies are included in the cgpv-main.js file that is referenced by the html page. To access it, add the lines below to your webpack file.
```
externals: {
    react: 'cgpv.react',
    'react-dom': 'cgpv.reactDOM',
  },
```