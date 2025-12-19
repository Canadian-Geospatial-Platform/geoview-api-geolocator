import os
import re
import requests
import boto3
from geolocator import Geolocator
from params_manager import *
from model_manager import *
from constants import *
from exceptions import *
from datetime import datetime
from dashboard import *

cache = {} # temporary cache of query results
AOS_HOST = os.environ['OS_ENDPOINT']
NEW_INDEX_NAME = os.environ['NEW_INDEX_NAME']
REGION = 'ca-central-1'

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

    search_index_name = NEW_INDEX_NAME
    os_client = connect_to_opensearch(REGION, AOS_HOST)
    event_copy_for_opensearch = event #previous logic removes (pops) variables from event variable (not sure why)

    event = {'params': {'querystring': event}}
    
    # Initilize variables and objects
    loads = []
    item_keys = {} # keep item keys to check for duplicates
    geolocator = Geolocator()
    date_time = datetime.utcnow().now()

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
        response = {"statusCode": 200, "body": '{"message_en": "Mandatory \'/?q= or table=\' parameter not provided", "message_fr": "Paramètre obligatoire \'/?q= or table=\' non fourni"}'}
        return response

    postal_code = extract_postal_prefix(params_full_list.get("q"))
    postal_code_detected = False

    if(postal_code and key_in_params("locate", params_full_list)):
        #print("Postal code detected, using locate api for forward sortation area")
        q = extract_postal_prefix(params_full_list.get("q"))
        params_full_list.update({"q": q}) #need to update this variable as only q and lang are used for caching
        postal_code_detected = True
    elif(postal_code and key_in_params("fsa", params_full_list)):
        #print("Postal code detected, using opensearch api for forward sortation area ")
        q = extract_postal_prefix(params_full_list.get("q"))
        params_full_list.update({"q": q}) #need to update this variable as only q and lang are used for caching
        postal_code_detected = True
    else:
        q = params_full_list.get("q")

    keys = params_full_list.pop("keys")
    key = params_full_list.get("key")
    lang = params_full_list.get("lang")
    q_lang = q + lang # compound key for cache results
    table_parameter = params_full_list.pop("table")
    dev = params_full_list.pop("dev")
    dev = True if dev == 'true' else False
    # Only required for lookup tables
    table_update = {'generic': {}, 'province': {}}  # missing codes from tables
    table_params = (tables, lang, table_update)

    # if table url parameter set, return table
    if table_parameter != 'none':
        loads = tables[table_parameter]
    else:
        # check if result in cache
        if cached_result(q, lang, keys, dev, date_time):
            loads = cache.get(q_lang).get('loads')
        else:
            # services to call
            response_ok = True
            for service_id in keys:
                # The schema for this service
                service_schema = schemas.get(service_id)
                # Adjust the parameters to the service's schema
                url, params, code_table_urls = assemble_url(service_schema, params_full_list.copy())
                temp_keys = params.get("key", "")
                if service_id == "locate" and "q" in params:
                    if params["q"].endswith("*"):
                        params["q"] = params["q"][:-1]  # remove last character
                #print("service_id", service_id)
                #print("url", url)
                print("params", params)
                if code_table_urls:
                    tables.update(code_table_urls) # add urls to table
                # At this point the query must be complete
                service_load = url_request(url, params,service_id)
                #print("service_load", service_load)
                if service_load == [{}]:
                    continue # Skip this iteration and move to the next one

                # check response status
                if 'key' in service_load and service_load.get('key') == 'unsuccess':
                    response_ok = False
                    if dev:
                        loads = [service_load] + loads  # add message to beginning
                else:
                    # At this point is where the 'out' part of each model applies
                    items = items_from_service(service_id,
                                               table_params,
                                               service_schema,
                                               output_schema_items,
                                               service_load,
                                               item_keys,
                                               dev)
                    #print("items", items)
                    loads.extend(items)
            
            if postal_code_detected:
                try:
                    service_id = "nominatim"
                    service_schema = schemas.get(service_id)
                    lat_lon = f"{loads[0]['lat']},{loads[0]['lng']}"
                    params_full_list.update({"q": lat_lon})
                    # Adjust the parameters to the service's schema
                    url, params, code_table_urls = assemble_url(service_schema, params_full_list.copy())
                    service_load = url_request(url, params, service_id)
                    items = items_from_service(service_id,
                                            table_params,
                                            service_schema,
                                            output_schema_items,
                                            service_load,
                                            item_keys,
                                            dev)
                    loads.extend(items)

                    service_id = "geonames"
                    service_schema = schemas.get(service_id)
                    params_full_list.pop("q")
                    params_full_list.update({"lat": f"{loads[0]['lat']}", "lon": f"{loads[0]['lng']}"})
                    # Adjust the parameters to the service's schema
                    url, params, code_table_urls = assemble_url(service_schema, params_full_list.copy())
                    service_load = url_request(url, params, service_id)
                    items = items_from_service(service_id,
                                            table_params,
                                            service_schema,
                                            output_schema_items,
                                            service_load,
                                            item_keys,
                                            dev)
                    #print("items", items)
                    loads.extend(items)
                except:
                    pass # try is experimental so continue if it fails

            # add query result to cache
            if q_alphanumeric(q) and response_ok:
                cache.update({q_lang: {'datetime': str(date_time), 'keys': keys, 'dev': dev, 'loads': loads }})

            # write csv files if table updated
            for table_name in table_update:
                if any(table_update[table_name]):
                    print(table_name, ' table updates:', table_update[table_name])
                    geolocator.write_table(table_name, tables)
            
            #OpenSearch DashBoard code
            if os_client:
                write_to_opensearch (os_client, event_copy_for_opensearch, search_index_name)
            else:
                print("OpenSearch is not available. Skipping write.")
    
    response = loads
    """
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
    """

    return response


def cached_result(q, lang, keys, dev, date_time):
    """
    check if result in temporary cache and within expiry days
    """
    if not q_alphanumeric(q):
        return False

    q_lang = q + lang

    if q_lang not in cache:
        return False

    # keys and dev parameters must match
    if keys != cache.get(q_lang).get('keys') or \
        dev != cache.get(q_lang).get('dev'):
        return False

    format_string = "%Y-%m-%d %H:%M:%S.%f"
    #convert datetime str to obj
    cached_datetime_obj = datetime.strptime(cache.get(q_lang).get('datetime'), format_string)

    diff = date_time - cached_datetime_obj
    days = diff.days #calculate the difference in days

    #Compare current curr day with cached date_time
    if days > EXPIRY_DAYS:
        return False

    return True


def q_alphanumeric(q):
    """
    Verify q parameter:
        - alphanumeric
        - + or * characters allowed
        - length > 0 and < 30
    """

    q = q.replace('+', '')
    q = q.replace('*', '')

    if (q.isalnum()):
        if len(q) > 0 and len(q) < 30:
            return True

    return False


def extract_postal_prefix(postal_code):
    """
    Extracts the first three characters of a valid Canadian postal code.
    Supports:
    - Standard format: "A1B 2C3"
    - Plus sign separator (+ is appended by API Gateway): "A1B+2C3"
    - No separator: "A1B2C3"
    - FSA-only input: "A1B"
    - Optional '*' at the end: "A1B2C3*"
    - New groups for (A1B2 or A1B2C) and (A1B2* or A1B2C*)
    """

    match = re.match(r'^([A-Za-z]\d[A-Za-z])(?:[\s\+]?\d[A-Za-z]\d)?\*?$|^([A-Za-z]\d[A-Za-z]\d)\*?$|^([A-Za-z]\d[A-Za-z]\d[A-Za-z])\*?$', postal_code)
    
    # Extract the first three characters from the match group
    if match:
        # group(1) handles A1B2C3, A1B 2C3, A1B+2C3, A1B, and optional '*' at the end e.g., "A1B2C3*"
        # group(2) handles A1B2 or A1B2*
        # group(3) handles A1B2C or A1B2C*
        return match.group(1) or match.group(2) or match.group(3)  
    return None

def key_in_params(key, params_full_list):
    """
    Check if key is in keys parameter
    """
    keys = params_full_list.get("keys", [])    
    if isinstance(keys, str):
        keys = keys.split(",")
    if key in keys:
        return True
    else:
        return False