# Lookup tables configuration

For the geonames key, 2 csv files (generic.csv, province.csv) contain generic location and province names.

The generic.csv and province.csv files are loaded into tables, to reduce API calls to the geonames service.
The geonames urls in tableurl.csv are used when tables need to be updated.

For the locate key, the component.csv file is used for province code lookup
The province.csv and component.csv files both contain province data.  Province.csv has the numeric geonames province code.  Component.csv has the province name abbreviation.

For the nominatim key, the category.csv file is used to provide French translation for the category field