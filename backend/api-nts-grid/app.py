import os
import re
import json
import boto3
import requests
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


def lambda_handler(event, context):
    """
    Lambda function handler to process logs from a CloudWatch log group and index them into OpenSearch.
    """
    # Environment variable configuration
    region         = os.environ['MY_AWS_REGION']
    aos_host       = os.environ['OS_ENDPOINT']
    os_secret_id   = os.environ['OS_SECRET_ID']
    nts_index_name = os.environ['INDEX_NAME']

    # Get event variables
    q = event.get("q")

    # Use IAM credentials instead
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)

    # Initialize OpenSearch client
    os_client = OpenSearch(
        hosts=[{'host': aos_host, 'port': 443}],
        http_auth=aws_auth,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname = False,
        ssl_show_warn = False,
        connection_class=RequestsHttpConnection
    )

    try:
        response = os_client.info()
        print("OpenSearch Connected:", response)
    except Exception as e:
        print("OpenSearch Connection Failed:", e)

    parsed = parse_query(q)
    print(parsed)
    
    should_clauses = []

    # Case 1: q parsed as a geo_point
    if isinstance(parsed, dict) and "type" in parsed:
        should_clauses.append({
            "geo_shape": {
                "location": {
                    "shape": parsed,
                    "relation": "intersects"
                }
            }
        })

    # Case 2: q parsed as a NTS_SNRC
    else:
        should_clauses.append({
            "term": {
                "attributes.NTS_SNRC.keyword": parsed
            }
        })

    query = {
        "query": {
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1
            }
        }
    }

    url = f"https://{aos_host}/{nts_index_name}/_search"
    print(url)
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            url,
            auth=aws_auth,
            headers=headers,
            data=json.dumps(query)
        )

        json_object = json.loads(response.text)

        try:
            name = json_object['hits']['hits'][0]['_source']['attributes']['NTS_SNRC']
            if json_object['hits']['hits'][0]['_source']['attributes']['NAME_ENG']:
                desc = str(json_object['hits']['hits'][0]['_source']['attributes']['NAME_ENG']) + ", " + str(json_object['hits']['hits'][0]['_source']['attributes']['NOM_FRA'])
            else:
                desc = ''
            long = (json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][0][0] + json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][1][0]) / 2.0
            lat  = (json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][1][1] + json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][0][1]) / 2.0
            area = json_object['hits']['hits'][0]['_source']['attributes']['SHAPE_AREA']

            bbox_array = [
                json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][0][0],  # minX (top-left X)
                json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][1][1],  # minY (bottom-right Y)
                json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][1][0],  # maxX (bottom-right X)
                json_object['hits']['hits'][0]['_source']['bbox']['coordinates'][0][1],  # maxY (top-left Y)
            ]

            response_json = {
                "key": "nts-grid",
                "name": name,
                "description": desc,
                "category": "NTS Grid 1:250000",
                "long": long,
                "lat": lat,
                "bbox": bbox_array,
                "tag": str(area) + " degrees of longituge and 1 degree of latitude"
            }

            return [ 
                response_json
                ]
        
        except IndexError:
            return {
                "statusCode": 404,
                "body": json.dumps("No results found in OpenSearch")
            }
    
    except requests.RequestException as e:
        return {
            "statusCode": 500,
            "body": json.dumps(f"Request error: {str(e)}")
        }

def parse_query(q):
    q = q.strip().upper()
    if "," in q:
        try:
            lon, lat = map(float, q.split(","))
            return {"type": "Point", "coordinates": [lon, lat]}
        except ValueError:
            pass  # fall back to treat as code

    # If q starts with two digits and a letter prefix with '0'
    if re.match(r"^\d{2}[A-Z]$", q):
        q = '0' + q
    return q