import json
from opensearchpy import OpenSearch, RequestsHttpConnection
from helper import translate_titles

def run_bbox_search(os_client, index_name, query, q, lang, geonames):
    try:
        response = os_client.search(index=index_name, body=query)
        hits = response.get('hits', {}).get('hits', [])

        transformed = []

        for hit in hits:
            src = hit.get('_source', {})
            geom = src.get('geometry', {})

            lat = geom.get("lat")
            lon = geom.get("lon")

            bbox = src.get('bbox')
            doc_type = src.get("type", "")

            # No address interpolation logic here — bbox searches skip it

            # default centroid-only record
            if not bbox:
                transformed.append({
                    "title": src.get("title"),
                    "qualifier": src.get("qualifier"),
                    "type": doc_type,
                    "geometry": {
                        "type": "Point",
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
                    "type": doc_type,
                    "bbox": [min_lon, min_lat, max_lon, max_lat],
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
                })

        # This still runs — harmless for bbox since nothing is interpolated
        transformed = move_first_interpolated_to_top(transformed)

        # Localize/translate titles
        transformed = translate_titles(geonames, transformed, lang=lang)

        return transformed

    except Exception as e:
        print("Search failed:", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# Ensure top interpolated position is the top records returned 
def move_first_interpolated_to_top(records):
    """
    Moves the first record with qualifier 'INTERPOLATED_POSITION' to the top of the list.
    Other records remain in their original order.
    """
    for i, rec in enumerate(records):
        if rec.get("qualifier") == "INTERPOLATED_POSITION":
            if i != 0:
                records.insert(0, records.pop(i))
            break
    return records