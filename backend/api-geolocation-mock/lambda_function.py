import os
import re
import json
import math
import boto3
import requests
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

from address_interpolator import *
from helper import *
from analytics import *
from bbox_handler import *

# Load geoname translations into memory once
with open("geonames_translation.json") as f:
    geonames = json.load(f)

# Load synonyms into memory once
with open("synonyms.json") as f:
    SYNONYMS = json.load(f)

# Create reverse lookup map: synonym -> canonical
REVERSE_MAP = {}

for canonical, syn_list in SYNONYMS.items():
    canonical_lower = canonical.lower()
    REVERSE_MAP[canonical_lower] = canonical  # canonical maps to itself
    
    for s in syn_list:
        REVERSE_MAP[s.lower()] = canonical

def normalize_query(query: str) -> str:
    """
    Replace tokens in querystring using synonym canonical forms
    E.g., Ave -> Avenue
    """
    # Split on anything non-alphanumeric
    tokens = re.split(r"([^a-zA-Z0-9]+)", query)

    normalized = []

    for token in tokens:
        t = token.lower()
        if t in REVERSE_MAP:
            normalized.append(REVERSE_MAP[t])
        else:
            normalized.append(token)

    return "".join(normalized)

def lambda_handler(event, context):
    """
    Lambda that mimics the old Geolocation API but queries OpenSearch under the hood.
    """
    # Environment variables
    region               = os.environ['MY_AWS_REGION']
    aos_host             = os.environ['OS_ENDPOINT']
    os_secret_id         = os.environ['OS_SECRET_ID']
    index_name           = os.environ['INDEX_NAME']
    address_range_index  = os.environ['ADDRESS_RANGE_INDEX']
    analytics_table_name = os.environ['ANALYTICS_TABLE_NAME']

    # Use get_language from helper.py to get language from API PATH (e.g., /en/geolocation or /fr/geolocation)
    lang = get_language(event)

    # Get ?q= parameter
    q           = None
    bbox_param  = None
    user_bbox   = None
    ip_address  = None
    timestamp   = None
    user_agent  = None
    http_method = None
    referrer    = None

    # Use IAM credentials
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'es',
        session_token=credentials.token
    )

    # Initialize OpenSearch client
    os_client = OpenSearch(
        hosts=[{'host': aos_host, 'port': 443}],
        http_auth=aws_auth,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection
    )

    if isinstance(event, dict):
        if "queryStringParameters" in event and event["queryStringParameters"]:
            q            = event["queryStringParameters"].get("q")
            bbox_param   = event["queryStringParameters"].get("bbox")
            callback     = event["queryStringParameters"].get("callback")
            ip_address   = event["queryStringParameters"].get("ip_address")
            timestamp    = event["queryStringParameters"].get('timestamp')
            user_agent   = event["queryStringParameters"].get('user_agent')
            http_method  = event["queryStringParameters"].get('http_method')
            referrer     = event["queryStringParameters"].get('referrer')
        else:
            q            = event.get("q")
            bbox_param   = event.get("bbox")
            callback     = event.get("callback")
            ip_address   = event.get('ip_address', '') or ''
            timestamp    = event.get('timestamp', '') or ''
            user_agent   = event.get('user_agent', '') or ''
            http_method  = event.get('http_method', '') or ''
            referrer     = event.get('referrer', '') or ''

    if bbox_param:
            try:
                parts = [float(x.strip()) for x in bbox_param.split(",")]
                if len(parts) == 4:
                    min_lon, min_lat, max_lon, max_lat = parts
                    user_bbox = {
                        "min_lon": min_lon,
                        "min_lat": min_lat,
                        "max_lon": max_lon,
                        "max_lat": max_lat
                    }
            except:
                pass

    if q:
        q = normalize_query(q)
    
    if is_suggest_request(event):
        if not q:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing q"})}
        return run_suggest_query(os_client, index_name, q)

    if is_autocomplete_request(event):
        if not q:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing q"})}
        return run_autocomplete_query(os_client, index_name, q)

    if not q and not user_bbox:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing query parameter 'q'"})
        }
    
    # If q is None but bbox exists, set q to empty string
    if not q:
        q = ""



    # Parse q
    parsed = parse_query(q)

    # Build a flexible search query
    should_clauses = []

    ##############################################
    # BEGIN ANALYTICS
    ##############################################

    # Creates new OpenSearch index if it doesn't exist
    create_opensearch_index(os_client, analytics_table_name)



    # Use existing ip2geo on opensearch instance to convert user ip_address to location
    # note: we not save or index user IP addresses but collect aggregate data
    ip2geo_data = ip2geo_handler(os_client, ip_address)

    document = [
            {
                "timestamp": timestamp,
                "lang": lang,
                "q": q,
                "user_agent": user_agent,
                "http_method": http_method,
                "referrer": referrer,
                "ip2geo": ip2geo_data
            }
        ]
    
    print(document)    
    save_to_opensearch(os_client, analytics_table_name, document)
    ##############################################
    # END ANALYTICS
    ##############################################

    ##############################################
    # CASE 1: bbox search: geo_bounding_box on centroid
    ##############################################
    if user_bbox:
        query = {
            "size": 25,
            "query": {
                "geo_bounding_box": {
                    "geometry": {
                        "top_left": {
                            "lat": user_bbox["max_lat"],
                            "lon": user_bbox["min_lon"]
                        },
                        "bottom_right": {
                            "lat": user_bbox["min_lat"],
                            "lon": user_bbox["max_lon"]
                        }
                    }
                }
            }
        }
        # Skip text search entirely
        print(query)
        return run_bbox_search(os_client, index_name, query, q, lang, geonames)
    ##############################################
    # CASE 2: TEXT SEARCH
    ##############################################
    else:
        # TEXT SEARCH
        # detect wildcard
        is_wildcard = "*" in parsed or "?" in parsed

        should_clauses = []

        if is_wildcard:
            # still allow keyword wildcard for legacy support
            should_clauses.append({
                "wildcard": {
                    "title.keyword": {
                        "value": parsed.lower(),
                        "case_insensitive": True
                    }
                }
            })
        else:
            # Use ngram field for partial matches
            fuzziness = "AUTO" if len(parsed) <= 10 else 0

            should_clauses.append({
                "multi_match": {
                    "query": parsed,
                    "fields": [
                        #"title.ngram",       # ngram autocomplete
                        "title^2.75",             # full title exact match
                        "type"
                    ],
                    "type": "best_fields",
                    "operator": "OR",
                    "slop": 0,
                    "fuzziness": fuzziness,
                    "prefix_length": 0,
                    "max_expansions": 10,
                    "zero_terms_query": "NONE",
                    "auto_generate_synonyms_phrase_query": "false",
                    "fuzzy_transpositions": "true",
                }
            })

        # REMOVE top-level Geoname term from should: let function_score handle boosts
        # Only add Streets/Intersections types minimally
        should_clauses.append({"term": {"type": {"value": "ca.gc.nrcan.geoloc.data.model.Geoname", "boost": 1.05}}})
        should_clauses.append({"term": {"type": {"value": "ca.gc.nrcan.geoloc.data.model.Street", "boost": 1.05}}})
        should_clauses.append({"term": {"type": {"value": "ca.gc.nrcan.geoloc.data.model.Intersection", "boost": 1.045}}})

        query = {
            "size": 25,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": should_clauses,
                            "minimum_should_match": 1
                        }
                    },
                    "functions": [
                        # Boost Streets strongly
                        {
                            "filter": {
                                "bool": {
                                    "should": [
                                        {"term": {"type": "ca.gc.nrcan.geoloc.data.model.Street"}},
                                        {"wildcard": {"type": "*.Street"}}
                                    ]
                                }
                            },
                            "weight": 2.2
                        },
                        # Slightly reduce Intersections
                        {
                            "filter": {"term": {"type": "ca.gc.nrcan.geoloc.data.model.Intersection"}},
                            "weight": 2.15
                        },
                        # Geonames: only moderate boost, keep under streets
                        {
                            "filter": {"term": {"type": "ca.gc.nrcan.geoloc.data.model.Geoname"}},
                            "weight": 1.8
                        },
                        # Postal code: boost heavily
                        {
                            "filter": {"term": {"type": "ca.gc.nrcan.geoloc.data.model.PostalCode"}},
                            "weight": 1.9
                        },
                        # NTS: boost heavily
                        {
                            "filter": {"term": {"type": "ca.gc.nrcan.geoloc.data.model.NTS"}},
                            "weight": 1.9
                        },
                        # Geonames feature-based boosts
                        {
                            "filter": {
                                "bool": {
                                    "must": [
                                        {"term": {"type": "ca.gc.nrcan.geoloc.data.model.Geoname"}},
                                        {"bool": {
                                            "should": [
                                                {"match_phrase": {"title": "City"}},
                                                {"match_phrase": {"title": "Province"}},
                                                {"match_phrase": {"title": "Territory"}}
                                            ],
                                            "minimum_should_match": 1
                                        }}
                                    ]
                                }
                            },
                            "weight": 2
                        },
                        {
                            "filter": {
                                "bool": {
                                    "must": [
                                        {"term": {"type": "ca.gc.nrcan.geoloc.data.model.Geoname"}},
                                        {"bool": {
                                            "should": [
                                                {"match_phrase": {"title": "Town"}},
                                                {"match_phrase": {"title": "Village"}},
                                                {"match_phrase": {"title": "District municipality"}},
                                                {"match_phrase": {"title": "Lake"}}
                                            ],
                                            "minimum_should_match": 1
                                        }}
                                    ]
                                }
                            },
                            "weight": 1.2
                        },
                        {
                            "filter": {
                                "bool": {
                                    "must": [
                                        {"term": {"type": "ca.gc.nrcan.geoloc.data.model.Geoname"}},
                                        {"bool": {
                                            "should": [
                                                {"match_phrase": {"title": "Hamlet"}},
                                                {"match_phrase": {"title": "Unincorporated area"}}
                                            ],
                                            "minimum_should_match": 1
                                        }}
                                    ]
                                }
                            },
                            "weight": 0.5
                        },
                        {
                            "filter": {
                                "bool": {
                                    "must": [
                                        {"term": {"type": "ca.gc.nrcan.geoloc.data.model.Geoname"}},
                                        {"bool": {
                                            "should": [
                                                {"match_phrase": {"title": "Underwater Features"}},
                                                {"match_phrase": {"title": "International Waters"}},
                                                {"match_phrase": {"title": "Conservation area"}}
                                            ],
                                            "minimum_should_match": 1
                                        }}
                                    ]
                                }
                            },
                            "weight": 0.1
                        }
                    ],
                    "score_mode": "sum",     #within the functions array
                    "boost_mode": "multiply" #applied to base score
                }
            }
        }
        print(query)

    try:
        response = os_client.search(index=index_name, body=query)
        hits = response.get('hits', {}).get('hits', [])

        transformed = []
        house_number = extract_house_number_from_query(q)  # may be None

        for hit in hits:
            src = hit.get('_source', {})

            geom = src.get('geometry', {})
            # many of your documents store centroid as {"lon":..., "lat":...}
            lat = geom.get("lat")
            lon = geom.get("lon")

            bbox = src.get('bbox')

            doc_type = src.get("type", "")
            # if it's a Street and we found a house number, attempt interpolation
            if doc_type.endswith("Street") or doc_type.endswith(".Street"):
                # find a join key (try common fields)
                street_id = src.get("street_id") or src.get("feature_id") or src.get("bdg_id")
                if street_id and house_number:
                    ranges = find_address_ranges_for_street(os_client, street_id, house_number, address_range_index)
                    if ranges:
                        # prefer exact range where min<=num<=max and numbering_method maybe relevant
                        interp_point = None
                        for r in ranges:
                            interp = interpolate_from_range_v2(r, house_number)
                            if interp:
                                interp_point = interp
                                # keep first successful one for now
                                break
                        if interp_point:
                            lon_i, lat_i = interp_point[0], interp_point[1]
                        orig_title = src.get("title", "")
                        new_title = f"{house_number} {orig_title}"

                        transformed.append({
                            "title": new_title,
                            "qualifier": "INTERPOLATED_POSITION",
                            "type": src.get("type", "ca.gc.nrcan.geoloc.data.model.Street"),
                            "geometry": {
                                "type": "Point",
                                "coordinates": [lon_i, lat_i]
                            }
                        })
                        continue   # go to next hit (we've added interpolated version)
                # if we couldn't interpolate, fall through to append centroid as-is

            # --- default/centroid handling (non-street or fallback) ---
            if not bbox:
                transformed.append({
                    "title": src.get("title"),
                    "qualifier": src.get("qualifier"),
                    "type": src.get("type", "ca.gc.nrcan.geoloc.data.model.Geoname"),
                    "geometry": {
                        "type": geom.get("type", "Point"),
                        "coordinates": [lon, lat]
                    }
                })
            else:
                min_lon = bbox.get("min_lon")
                max_lon = bbox.get("max_lon")
                min_lat = bbox.get("min_lat")
                max_lat = bbox.get("max_lat")
                transformed.append({
                    "title": src.get("title"),
                    "qualifier": src.get("qualifier"),
                    "type": src.get("type", "ca.gc.nrcan.geoloc.data.model.Geoname"),
                    "bbox": [min_lon, min_lat, max_lon, max_lat],
                    "geometry": {
                        "type": geom.get("type", "Point"),
                        "coordinates": [lon, lat]
                    }
                })
        
        transformed = move_first_interpolated_to_top(transformed)

        transformed = translate_titles(geonames, transformed, lang=lang)

        if callback and is_valid_callback(callback):
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/javascript; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization"
                },
                "body": f"{callback}({json.dumps(transformed, ensure_ascii=False)});",
                "isBase64Encoded": False
            }
        
        return {
            "statusCode": 200,
            "headers": {
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization",
                    "Cache-Control": "no-store"
            },
            "body": json.dumps(transformed, ensure_ascii=False),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        print("Search failed:", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

def run_suggest_query(os_client, index_name, q):
    body = {
        "size": 0,
        "suggest": {
            "title_suggest": {
                "prefix": q,
                "completion": {
                    "field": "title_suggest",
                    "fuzzy": { "fuzziness": 2 },
                    "size": 50  # request more results to get unique values
                }
            }
        },
        "_source": ["type"]
    }

    resp = os_client.search(index=index_name, body=body)
    options = resp["suggest"]["title_suggest"][0]["options"]

    # 🔧 remove duplicates by text
    unique = []
    seen = set()
    for opt in options:
        text = opt["text"]
        if text not in seen:
            seen.add(text)
            unique.append(opt)

    # Put Geonames first (optional)
    unique = sorted(
        unique,
        key=lambda s: 0 if s.get("_source", {}).get("type") == "ca.gc.nrcan.geoloc.data.model.Geoname" else 1
    )

    # Return only top 5 unique values
    return { "suggestions": [opt["text"] for opt in unique[:5]] }

def run_autocomplete_query(os_client, index_name, q):
    # Use completion suggester
    body = {
        "size": 0,
        "suggest": {
            "title_suggest": {
                "prefix": q,
                "completion": {
                    "field": "title_suggest",
                    "fuzzy": {"fuzziness": 0},
                    "size": 20  # request more to ensure unique results
                }
            }
        },
        "_source": ["type", "title"]
    }

    resp = os_client.search(index=index_name, body=body)
    options = resp["suggest"]["title_suggest"][0]["options"]

    seen = set()
    suggestions = []

    for opt in options:
        src = opt.get("_source", {})
        text = src.get("title", opt["text"])

        # Only take the first part for Geonames
        if src.get("type") == "ca.gc.nrcan.geoloc.data.model.Geoname":
            text = text.split(",")[0].strip()

        if text not in seen:
            seen.add(text)
            suggestions.append(text)

        if len(suggestions) >= 5:
            break

    return {"suggestions": suggestions}

def is_valid_callback(callback_name: str) -> bool:
    """
    Allow only valid JS function names to prevent XSS.
    e.g. jQuery123_456
    """
    return bool(re.match(r'^[a-zA-Z_$][0-9a-zA-Z_$\.]*$', callback_name))