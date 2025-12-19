import json
from opensearchpy import OpenSearch, RequestsHttpConnection

def create_opensearch_index(os_client, index_name):
    """Create a new OpenSearch index if it doesn't exist."""
    if not os_client.indices.exists(index=index_name):
        # Define the mapping for the new index
        index_body = {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "lang": {"type": "keyword"},
                    "q": {"type": "keyword"},
                    "user_agent": {"type": "keyword"},
                    "http_method": {"type": "keyword"},
                    "referrer": {"type": "keyword"},
                    "ip2geo": {
                        "properties": {
                            "continent_name": {"type": "keyword"},
                            "region_iso_code": {"type": "keyword"},
                            "city_name": {"type": "keyword"},
                            "country_iso_code": {"type": "keyword"},
                            "country_name": {"type": "keyword"},
                            "region_name": {"type": "keyword"},
                            "location": {"type": "geo_point"},
                            "time_zone": {"type": "keyword"}
                        }
                    }
                }
            }
        }

        response = os_client.indices.create(index=index_name, body=index_body)
        print(f"Created new OpenSearch index: {index_name}")
        return response
    else:
        print(f"Index '{index_name}' already exists.")
        return None

def save_to_opensearch(os_client, index, document):
    """
    Loads the transformed log data into OpenSearch.
    """
    for doc in document:
        response = os_client.index(index=index, body=doc)


def parse_geo_point(ip2geo_data):
    if 'location' in ip2geo_data and isinstance(ip2geo_data['location'], str):
        try:
            lat, lon = map(float, ip2geo_data['location'].split(','))
            ip2geo_data['location'] = {"lat": lat, "lon": lon}  # Convert to geo_point format
        except ValueError:
            print("Invalid location format:", ip2geo_data['location'])
            ip2geo_data['location'] = None  # Handle errors gracefully
    return ip2geo_data

def ip2geo_handler(os_client, ip_address):
    
    ip2geo_payload = {
        "docs": [
            {
                "_index": "test",
                "_id": "1",
                "_source": {
                    "ip": ip_address
                }
            }
        ]
    }

    response = os_client.transport.perform_request(
        method="POST",
        url="/_ingest/pipeline/ip-to-geo-pipeline/_simulate",
        body=json.dumps(ip2geo_payload)
    )

    try:
        ip2geo_data = response["docs"][0]["doc"]["_source"].get("ip2geo", {})
        ip2geo_data = parse_geo_point(ip2geo_data) #ensure lat lon is a geo_point
    except (KeyError, json.JSONDecodeError) as e:
        print("Error extracting ip2geo data:", str(e))
    
    return ip2geo_data