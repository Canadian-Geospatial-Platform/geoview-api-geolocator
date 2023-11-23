# Lookup tables configuration

For the geonames key, 2 csv files (generic.csv, province.csv) contain generic location and province names.
The urls for the source of the lookup tables are stored in another csv file, tableurl.csv

The generic.csv and province.csv files are loaded into tables, to reduce API calls to the geonames service.
The geonames urls in tableurl.csv are used when tables need to be updated. 