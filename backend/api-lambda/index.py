from geolocator import Geolocator
from params_manager import *
from model_manager import *
from constants import *
from exceptions import *

def handler(event, context):
    """
    Main function. When called, performs specific actions in order to
          extract, adapt, and return REST data from several specific services.

    Those actions are:
    - Initialize. Defines variables and services, reads schemas and validates
                 parameters
    - Query assembling. Based on the schema for each required service, a valid
                        url is assembled before calling the REST service
    - Service output. the response is adapted to the expected structure
    - Validation. The resulting data is validated against an output schema to
                  be 'conformed' before be handed to the front-end

    Params:
      event: Contiens the query parameters
      context: Not required for this function

    Return: Standarized, validated data from REST services related to
             geolocation to be handed to the front-end
    """

    event = {'params': {'querystring': event["queryStringParameters"]}}

    # Initilize variables and objects
    loads = []
    geolocator = Geolocator()
    # Read schemas from Geolocator
    schemas = geolocator.get_schemas()
    tables = geolocator.get_tables()
    # Extract IO schemas
    in_api_schema = schemas.get(IN_API)
    output_schema_items = schemas.get(OUT_API). \
                            get("definitions"). \
                            get("output"). \
                            get("items")
    # 0. Read and Validate the parameters
    try:
        params_full_list = validate_querystring_against_schema(event,in_api_schema)
    except MissingParameterException as e:
        response = {"statusCode": 200, "body": '{ "message_en": "Mandatory \'/?q=\' parameter not provided", "message_fr": "Paramètre obligatoire \'/?q=\' non fourni" }'}
        return response
        
    keys = params_full_list.pop("keys")
    lang = params_full_list.get("lang")
    # Only required for lookup tables
    table_params = (tables, lang)
    # services to call
    for service_id in keys:
        # The schema for this service
        service_schema = schemas.get(service_id)
        # Adjust the parameters to the service's schema
        url, params = assemble_url(service_schema, params_full_list.copy())
        # At this point the query must be complete
        service_load = url_request(url, params)
        # At this point is where the 'out' part of each model applies
        items = items_from_service(service_id,
                                   table_params,
                                   service_schema,
                                   output_schema_items,
                                   service_load)
        loads.extend(items)
    response = {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(
            loads
        )
    }

    return response

def nonesafe_loads(obj):
    if obj is not None:
        return json.loads(obj)
