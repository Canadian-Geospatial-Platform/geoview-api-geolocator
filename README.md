# Geoview API – Geolocator

Natural Resources Canada / Ressources naturelles Canada  
Part of the **Canadian Geospatial Platform (CGP)**

---

## Overview

The **Geolocator API** is a RESTful geolocation and geocoding service for **Canadian locations**. It aggregates and normalizes results from multiple authoritative and open data sources to provide rich, bilingual (English/French) location search capabilities.

This API integrates with the **GeoView** geolocation search widget. See: https://github.com/Canadian-Geospatial-Platform/geoview

The service supports:

- Place name search (cities, towns, features)
- Address and general geocoding
- Forward Sortation Area (FSA) lookup
- National Topographic System (NTS) map sheet lookup
- Coordinate-based reverse-style searches

Results are grouped by data source, making it easy to selectively consume the datasets most relevant to your application.

---

## Base Endpoint

```text
https://geolocator.api.geo.ca/
```

All requests must be made over **HTTPS**.

---

## Request Parameters

| Parameter | Type   | Required | Description |
|----------|--------|----------|-------------|
| `q`      | string | Yes | Search query. Can be a place name, address, postal code, or coordinates (`lat,lon`). |
| `lang`   | string | No  | Response language. Supported values: `en` (default), `fr`. |
| `keys`   | string | No  | Comma-separated list of data sources to query. Defaults to **all sources**. |

### Supported `keys`

| Key | Description |
|----|-------------|
| `geonames` | Canadian Geographical Names Database (CGNDB) from the Geographic Names Board of Canada (official place names) |
| `nominatim` | OpenStreetMap Nominatim (address & place geocoding) |
| `locate` | NRCan Geolocate service (additional location data) |
| `fsa` | Forward Sortation Areas (first 3 characters of postal codes) |
| `nts` | National Topographic System (map sheet references) |

---

## Example API Call

```http
GET https://geolocator.api.geo.ca/?q=ottawa&lang=en&keys=geonames,nominatim,locate,fsa,nts
```

---

## Response Structure

The Geolocator API returns a **flat JSON array** of result objects. Each object represents a match from a specific data source and includes a `key` field identifying its origin.

```json
[
  { "key": "geonames", ... },
  { "key": "nominatim", ... },
  { "key": "locate", ... }
]
```

This design allows results from multiple sources to be merged, ranked, filtered, or regrouped client-side.

---

### Common Fields (All Results)

| Field | Type | Description |
|------|------|-------------|
| `key` | string | Data source identifier (`geonames`, `nominatim`, `locate`, `fsa`, `nts`) |
| `name` | string | Name or label of the location |
| `province` | string | Province or territory name |
| `category` | string | Feature or result type (e.g. City, River, Street, Intersection) |
| `lat` | number | Latitude (WGS84) |
| `lng` | number | Longitude (WGS84) |
| `bbox` | array \| null | Bounding box `[west, south, east, north]` when available |
| `tag` | array \| null | Additional qualifiers or metadata from the source |

---

## Full Response Examples

### Example: Multi-source Search (`q=ottawa`)

```json
[
  {
    "key": "geonames",
    "name": "Ottawa",
    "province": "Ontario",
    "category": "City",
    "lat": 45.33339,
    "lng": -75.58429,
    "bbox": [-76.3631149, 44.9445516, -75.2324963, 45.544859],
    "tag": ["Carleton; Russell"]
  },
  {
    "key": "nominatim",
    "name": "Ottawa, Eastern Ontario",
    "province": "Ontario",
    "category": "Boundary",
    "lat": 45.4208777,
    "lng": -75.6901106,
    "bbox": [-76.3555857, 44.9617738, -75.2465783, 45.5376502],
    "tag": ["boundary"]
  },
  {
    "key": "locate",
    "name": "Ottawa, Carleton; Russell, Ontario (City)",
    "province": "Ontario",
    "category": "City",
    "lat": 45.24470527547184,
    "lng": -75.79780558380465,
    "bbox": [-76.3631149, 44.9445516, -75.2324963, 45.544859],
    "tag": ["LOCATION"]
  }
]
```

### Example: Postal Code / FSA Search (`q=k1s&keys=locate`)

```json
[
  {
    "key": "locate",
    "name": "K1S",
    "province": null,
    "category": "PostalCode",
    "lat": 45.39602100000002,
    "lng": -75.68769450000002,
    "bbox": null,
    "tag": [
      "INTERPOLATED_CENTROID"
    ]
  }
```

---

## Usage Examples

### Search by City Name

```http
GET https://geolocator.api.geo.ca/?q=vancouver&lang=en&keys=geonames,nominatim
```

### Search by Postal Code / FSA
Note: when full postal code are provided, the API will truncate to the forward soration area (first 3 characters)

```http
GET https://geolocator.api.geo.ca/?q=K1A&lang=en&keys=fsa
```
### French Language Results

```http
GET https://geolocator.api.geo.ca/?q=montreal&lang=fr&keys=geonames,nominatim,locate,fsa,nts
```

---

## CORS and Client-Side Use

- CORS is enabled, allowing use directly from web applications
- Designed to support lightweight frontend and mapping clients

---

## Rate Limits & Best Practices

- The service is provided **free of charge** for reasonable public, public-sector and research use
- Cache responses are used where possible to minimize repeat requests
- Use the `keys` parameter to limit queries to required datasets
- For high-volume or bulk geocoding use cases, please contact the maintainers at geo@nrcan-rncan.gc.ca

---

## Repository Structure (High-Level)

- `backend/{api-lambda,api-forward-sortation-area,api-nts-grid,api-geolocation-mock}` – Backend AWS Lambda implementation of the API
- `backend/jupyter-notebooks` – Search indexing and relevance tuning on AWS OpenSearch
- `helpers / services` – Source-specific adapters and normalization logic

---

## Related Resources

- **GitHub Repository**: Canadian-Geospatial-Platform/geoview-api-geolocator
- **GEO.ca**: https://app.geo.ca

---

## Support & Contributions

- Report bugs or request features via **GitHub Issues**
- Contributions are welcome following Government of Canada open-source guidelines

**Contact**:  
`geo@nrcan-rncan.gc.ca`

---

## License & Attribution

© His Majesty the King in Right of Canada, as represented by the Minister of Natural Resources.

This project is released under the applicable Government of Canada open-source license.

---

*Last updated: Dec 2025*

