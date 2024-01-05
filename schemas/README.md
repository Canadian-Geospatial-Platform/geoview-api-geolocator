# Schemas and Metadata Structure

Geolocator API is based on 'schemas' to define the way the application interacts with data. Different schemas are required to define the following tasks:
    • Read and validate the parameters passed to the API-geolocator application. This include the keys (the available services), the query and the language (when it's needed)

    • Build valid url and parameters for consuming data on each specific geo-service

    • Extract the required information from the query and build standard response from it   

    • Validate that the extracted data falls into valid parameters (mainly numeric values)


### Geolocator API Schemas
The Geolocator API has schemas for [input](./api/in-api-schema.json), [output](./api-out-schema.json) and several specific services schemas [./services/__service_id__-schema.json]

The __input__ schema identifies the expected parameters to query the API.
    - "q": The query to parse and send to supported API's.
    - "lang": The language on wich to filter the query (fr or en).
    - "keys": The list of supported API key to query. Optional parameter, if missing, all
            supported key will be queryied. Every time we support a new API or services, a new key will be added to this array of accepted values.

The __output__ schemas validates the obtained values match type and limits for each field.
    - "key": The service Id for the source of the data
    - "name": The generic name of the feature.
    - "lat": The latitude coordinate.
    - "lng": The longitude coordinate.
    - "bbox": The bbox [minX, minY, maxX, maxY].
    - "province": The province the item belongs to. Optional return value.
    - "tag": The tag value of the item. Optional return value. tags may be different from one API to
             the other, it is a value to help understand what type of item it is.
    It also includes a key ["properties"] with the list of valid 'services'.

each __service_id__ schema contains the rules to extract, adapt and validate the load data obtained after querying from that specific service.

### Supported API and services Metadata
Each supported APIs and services may have differents input and output signatures. To help the parsing of these signatures, the Geolocator API will rely on JSON metadata file. This metadata file will also holds connection information like urls. The name of this file is the value of the key item (<__service_id__>-schema.json).

The structure of this files is:
```
{
    "url": "https://.../_PARAM1_/...?", //API url with optional parameters
    "urlParams": {
        "param1": "lang" // Optional parameter to substitue in urls
    },
    "staticParams":
        "countrycodes=CA", // Fixed parameters required by the service,
        "format=jsonv2"    // they will be added to the url before execution
    },
    "urlCodeTables": { // Additional urls required to extract data tables for specific fields
        "province" : {
            "url": "https://geogratis.gc.ca/services/geoname/en/codes/province.json",
            // other keys/values here
        }
    }
    "lookup": {
        "in": { // Paramaters replacements specific for the current service
            "q": "q",
            "lang": "accept-language"
        },
        "out": { // Output lookup information
            "type": "array", // the type of data structure retrieved from the service
            "items": { // Set of attributes to be fullfiled by the input data with
                       // specific rules each
                "name": {
                    "field": "name", // Return JSON item to look for
                    "lookup": "" // Lookup to apply if needed
                },
                "lat": {  // field path to get access to the data value for this field
                    "field":"geometry.location.lat",
                    "lookup": ""
                }
                "bbox": {
                    "field": "bbox",
                    "lookup": ""
                },
                "province": {
                    "field": "province.code",
                    "lookup": { // describes the structure and attributes to obtain the data value
                        "type": "table",
                        "field": "description"
                    }
                },
                "tag": [ // Can contains many field values separated by comma ','
                         // For optional parameter like "tag", the field value
                         // can be left empty if no value is found
                    {
                        "field": "location",
                        "lookup": ""
                    },
                    {
                        "field": "generic.code",
                        "lookup": {
                            "type": "table",
                            "field": "term"
                        }
                    }
                ]
            }
        }
    }
}
```

### Lookup
Lookup can have several signatures:
    * None. The field is directly accesible
    * table. The data value must be extracted from a key-value table
    * array. The data value comes from an specific position in an array of values
    * search. The data should be found by searching in a data field containing
              a list of dictionaries where one must match an specific key/value tuple
	* average. Calculate the average of a subset of numeric values from a field
               containing a list of numerics (such as bbox)
    * url. The data value comes from a table obtained from a url (deprecated)
    * csv. The data value is extracted from a csv (comma separated values) string
    * type. The data value is extracted from different fields or tables depending on
              the value in the type field
### Response time
The response time for the query depends on several factors:
  - The service required. Different services perform different based on the
    complexity to adapt the load to the standard output format.
    Several services at once will ad up to the final delay.
  - The size of the load. More items required more time to process.
    The more specific the query, the fewer features will be processed. (it was
    already improved by keeping a list of micro-schemas asociated to each field.
    Even though the list must be cleared and rebuild for each service, the
    computing time is close to O(N) instead of O(N2)).
  - A delay of 5 minutes without performing any requests, will increase the
    response time in about 3 seconds for the next one, due to
    the life time of objects in memory.

  * An url to tests concurrencial calls can be used for performance validation.
    https://3wdd7ausil.execute-api.ca-central-1.amazonaws.com/dev?iterations=1000


### Google API's
    To test Google services such as 'findplace' and 'geocode' without the key.
    Simulate the return from the service by bypassing the url_request with a condition
    and the expected returns.
    ```
    https://maps.googleapis.com/maps/api/geocode/json?address=confederation%20park&key=AIzaSyASQcYTDCw4fRr_GY5WHxIAqeTsDmvAh_8
    ```
        * Add the service in in-api-schema.json:
    ```
        "enum": ["geonames", "nominatim", "locate", "nts", "geocode"]
    ```
        * Add the service in out-api-schema.json:
    ```
        "properties": {
            "geocode": {
            "type": "array",
            "uniqueItems": true,
            "items": { "$ref": "#/definitions/output" },
            "description": "The Geocode api result set."
            },
        }
    ```
        * geolocator_lambda.py should be 'temporarily' modified in this way:
    ```
    if service_id != "geocode":
        service_load = url_request(url, params)
    else:
        service_load = {
            "results" : [
                {
                    "address_components" : [
                    {
                        "long_name" : "Confederation Park",
                        "short_name" : "Confederation Park",
                        "types" : [ "establishment", "park", "point_of_interest", "tourist_attraction" ]
                    },
                    {
                        "long_name" : "Elgin Street",
                        "short_name" : "Elgin St",
                        "types" : [ "route" ]
                    },
                    {
                        "long_name" : "Downtown",
                        "short_name" : "Downtown",
                        "types" : [ "neighborhood", "political" ]
                    },
                    {
                        "long_name" : "Ottawa",
                        "short_name" : "Ottawa",
                        "types" : [ "locality", "political" ]
                    },
                    {
                        "long_name" : "Ottawa",
                        "short_name" : "Ottawa",
                        "types" : [ "administrative_area_level_2", "political" ]
                    },
                    {
                        "long_name" : "Ontario",
                        "short_name" : "ON",
                        "types" : [ "administrative_area_level_1", "political" ]
                    },
                    {
                        "long_name" : "Canada",
                        "short_name" : "CA",
                        "types" : [ "country", "political" ]
                    },
                    {
                        "long_name" : "K1P 5J2",
                        "short_name" : "K1P 5J2",
                        "types" : [ "postal_code" ]
                    }
                    ],
                    "formatted_address" : "Confederation Park, Elgin St, Ottawa, ON K1P 5J2, Canada",
                    "geometry" : {
                        "location" : {
                            "lat" : 45.422394,
                             "lng" : -75.692452
                        },
                        "location_type" : "GEOMETRIC_CENTER",
                        "viewport" : {
                            "northeast" : {
                                "lat" : 45.4235181802915,
                                "lng" : -75.69165646970849
                            },
                            "southwest" : {
                                "lat" : 45.4208202197085,
                                "lng" : -75.69435443029151
                            }
                        }
                    },
                    "partial_match" : true,
                    "place_id" : "ChIJ55USI_mq0kwR0mbQ4LTQyU4",
                    "plus_code" : {
                    "compound_code" : "C8C5+X2 Somerset Ward, Ottawa, ON, Canada",
                    "global_code" : "87Q6C8C5+X2"
                    },
                    "types" : [ "establishment", "park", "point_of_interest", "tourist_attraction" ]
                }
            ],
            "status" : "OK"
        }
    ```
