import re
import math

def extract_house_number_from_query(q: str):
    """Return first integer found in the query (or None)."""
    if not q:
        return None
    m = re.search(r"\b(\d{1,5})\b", q)   # adjust pattern if you need other formats
    return int(m.group(1)) if m else None

def haversine_meters(a, b):
    """Return haversine distance (meters) between two [lon,lat] points."""
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    R = 6371000.0
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(min(1, math.sqrt(h)))

def interpolate_along_linestring(coords, target_distance):
    """
    Walk the linestring coords (list of [lon,lat]) and return point [lon,lat]
    at distance (meters) from start. If target_distance >= total length returns last point.
    """
    if not coords or len(coords) == 0:
        return None
    # compute cumulative distances
    cum = [0.0]
    total = 0.0
    for i in range(1, len(coords)):
        seg = haversine_meters(coords[i-1], coords[i])
        total += seg
        cum.append(total)
    if total == 0:
        return coords[0]
    # clamp
    if target_distance <= 0:
        return coords[0]
    if target_distance >= total:
        return coords[-1]
    # find segment containing target_distance
    for i in range(1, len(cum)):
        if cum[i] >= target_distance:
            seg_start = coords[i-1]
            seg_end = coords[i]
            seg_len = cum[i] - cum[i-1]
            if seg_len == 0:
                return seg_end
            seg_target = target_distance - cum[i-1]
            frac = seg_target / seg_len
            # linear interpolation in lon/lat (ok for small fractions)
            lon = seg_start[0] + (seg_end[0] - seg_start[0]) * frac
            lat = seg_start[1] + (seg_end[1] - seg_start[1]) * frac
            return [lon, lat]
    return coords[-1]

def find_address_ranges_for_street(os_client, street_id, house_number, address_range_index):
    """
    Query ADDRESS_RANGE_INDEX for ranges that match street_id and contain house_number.
    Returns list of matching _source dicts.
    """
    if not street_id or house_number is None:
        return []
    body = {
        "size": 100,
        "query": {
            "bool": {
                "must": [
                    {"term": {"street_id": {"value": street_id}}}
                ],
                "filter": [
                    {"range": {"min_house_number": {"lte": house_number}}},
                    {"range": {"max_house_number": {"gte": house_number}}}
                ]
            }
        }
    }
    try:
        resp = os_client.search(index=address_range_index, body=body)
        hits = resp.get("hits", {}).get("hits", [])
        #print(hits)
        return [h.get("_source", {}) for h in hits]
    except Exception as e:
        print("Address-range search failed:", e)
        return []

def interpolate_from_range_v2(range_src, house_number):
    """
    Given an address-range _source dict and house_number, return interpolated [lon,lat] or None.
    """
    try:
        minn = range_src.get("min_house_number")
        maxx = range_src.get("max_house_number")

        if minn is None or maxx is None:
            return None

        minn = int(minn)
        maxx = int(maxx)

        delta = maxx - minn
        if delta != 0:
            offset = house_number - minn
            ratio = offset / delta
        else:
            ratio = 0.5

        # ------------------------------------------------------------
        # Correct digitizing_direction logic:
        # - 32 = DO NOT FLIP (normal direction)
        # - 33 = FLIP (reverse direction)
        # ------------------------------------------------------------
        digdir = range_src.get("digitizing_direction")
        if digdir == 33:
            ratio = 1 - ratio

        # Clamp ratio 0–1
        ratio = max(0.0, min(1.0, ratio))

        geom = range_src.get("geometry") or {}
        coords = geom.get("coordinates") or []

        if not coords:
            return None

        # Compute full length
        total = 0.0
        for i in range(1, len(coords)):
            total += haversine_meters(coords[i - 1], coords[i])

        target_distance = ratio * total

        point = interpolate_along_linestring(coords, target_distance)
        return point  # [lon, lat]

    except Exception as e:
        print("Interpolation error:", e)
        return None

def interpolate_from_range(range_src, house_number):
    """
    Given an address-range _source dict and house_number, return interpolated [lon,lat] or None.
    """
    try:
        minn = range_src.get("min_house_number")
        maxx = range_src.get("max_house_number")
        # ensure integers
        if minn is None or maxx is None:
            return None
        minn = int(minn)
        maxx = int(maxx)
        delta = maxx - minn
        if delta != 0:
            offset = house_number - minn
            ratio = offset / delta
        else:
            ratio = 0.5
        # handle digitizing_direction flip if required (ASSUMPTION: code 33 means reversed)
        digdir = range_src.get("digitizing_direction")
        # Adjust rules here if you know the actual mapping
        if digdir in (32,):  # <-- adjust this if your code mapping differs
            ratio = 1 - ratio
        geom = range_src.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if not coords:
            return None
        # compute total length in meters and target distance
        # convert ratio -> meters
        # get segment cumulative distances then pick point
        # total length:
        total = 0.0
        for i in range(1, len(coords)):
            total += haversine_meters(coords[i-1], coords[i])
        target_distance = max(0.0, min(1.0, ratio)) * total
        point = interpolate_along_linestring(coords, target_distance)
        return point  # [lon, lat]
    except Exception as e:
        print("Interpolation error:", e)
        return None