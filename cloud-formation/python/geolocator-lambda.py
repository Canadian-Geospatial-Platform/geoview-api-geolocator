from geolocator import Geolocator
from params_manager import *
from model_manager import *
from constants import *

def lambda_handler(event, context):
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
    # Initilize variables and objects
    loads = []
    geolocator = Geolocator()
    # Read schemas from Geolocator
    schemas = geolocator.get_schemas()
    # Extract IO schemas
    in_api_schema = schemas.get(IN_API)
    out_api_schema = schemas.get(OUT_API)
    output_schema = out_api_schema.get("definitions").get("output")
    schema_items = output_schema.get("items").get("properties")
    schema_required = output_schema.get("items").get("required")
    # 0. Read and Validate the parameters
    params_full_list = validate_querystring_against_schema(event,in_api_schema)
    keys = params_full_list.pop("keys")
    # services to call
    for service_id in keys:
        model = schemas.get(service_id)
        schema = model.get_schema()
        # Adjust the parameters to the service's schema
        url = assemble_url(schema, params_full_list.copy())
        # At this point the query must be complete
        service_load= url_request(url)
        # At this point is where the 'out' part of each model applies
        items = items_from_service(service_id,
                                   model,
                                   schema_items,
                                   schema_required,
                                   service_load)
        loads.extend(items)

    return loads
