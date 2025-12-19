import re



############################################################
# parse_query() supporting: BBOX, TEXT
############################################################
def parse_query(q):
    q = q.strip().upper()
    parts = [p.strip() for p in q.split(",")]

    # BBOX: 4 numbers: minLon, minLat, maxLon, maxLat
    if len(parts) == 4:
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, parts)
            return {
                "type": "Envelope",
                "coordinates": [
                    [min_lon, max_lat],  # upper-left
                    [max_lon, min_lat]   # lower-right
                ]
            }
        except:
            pass

    return q  # fallback to text

############################################################
# get_language() Returns 'en' or 'fr' if those substrings appear in the path.
############################################################
def get_language(event):
    # Get path (REST API) or HTTP API v2 path
    path = (
        event.get("requestContext", {})
             .get("http", {})
             .get("path")
        or event.get("path")
    )

    if not path:
        return None

    path = path.lower()

    if "/en/" in path or path.endswith("/en"):
        return "en"

    if "/fr/" in path or path.endswith("/fr"):
        return "fr"

    return None

############################################################
# Detect /suggest and /autocomplete
############################################################
def is_suggest_request(event):
    path = (
        event.get("requestContext", {})
             .get("http", {})
             .get("path")
        or event.get("path")
        or ""
    ).lower()
    return "/suggest" in path


def is_autocomplete_request(event):
    path = (
        event.get("requestContext", {})
             .get("http", {})
             .get("path")
        or event.get("path")
        or ""
    ).lower()
    return "/autocomplete" in path

############################################################
# Translation handler for en and fr paths
# Translate geoname features and provinces/territories in titles.
#    - Replaces text inside parentheses (e.g., City -> Ville)
#    - Replaces province/territory names anywhere in the title
############################################################

def translate_titles(geonames, records, lang="en"):
    if lang != "fr":
        return records

    paren_pattern = re.compile(r"\((.*?)\)")

    for rec in records:
        title = rec.get("title")
        if not title:
            continue

        # 1. Replace parenthetical text
        def replace_paren(match):
            inner = match.group(1).strip()
            translation = geonames.get(inner)
            if translation:
                return f"({translation['fr']})"
            else:
                return match.group(0)

        title = paren_pattern.sub(replace_paren, title)

        # 2. Replace provinces/territories outside parentheses
        # Go through all known English province/territory names
        for eng, mapping in geonames.items():
            if eng in title:
                title = title.replace(eng, mapping["fr"])

        rec["title"] = title

    return records