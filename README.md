# Geoview API – Geolocator / Géolocaliseur

**La version française suit.**

Natural Resources Canada / Ressources naturelles Canada  
Part of **GEO.ca**

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


---------------------------------------------------------------------------------------------------


# API GeoView – Géolocaliseur / Geolocator

Ressources naturelles Canada / Natural Resources Canada
Fait partie de **GEO.ca**

---

## Aperçu

L’**API Géolocaliseur** est un service RESTful de géolocalisation et de géocodage pour les **lieux au Canada**. Elle agrège et normalise les résultats provenant de multiples sources de données ouvertes et faisant autorité afin d’offrir des capacités de recherche géographique riches et bilingues (anglais/français).

Cette API s’intègre au widget de recherche géographique **GeoView**. Voir : [https://github.com/Canadian-Geospatial-Platform/geoview](https://github.com/Canadian-Geospatial-Platform/geoview)

Le service prend en charge :

* La recherche par nom de lieu (villes, municipalités, entités géographiques)
* Le géocodage d’adresses et le géocodage général
* La recherche par région de tri d’acheminement (RTA)
* La recherche par feuillet du Système national de référence cartographique (SNRC)
* Les recherches de type inverse basées sur des coordonnées

Les résultats sont regroupés par source de données, ce qui facilite la consommation sélective des ensembles de données les plus pertinents pour votre application.

---

## Point d’accès de base

```text
https://geolocator.api.geo.ca/
```

Toutes les requêtes doivent être effectuées via **HTTPS**.

---

## Paramètres de requête

| Paramètre | Type   | Requis | Description                                                                                                 |
| --------- | ------ | ------ | ----------------------------------------------------------------------------------------------------------- |
| `q`       | string | Oui    | Requête de recherche. Peut être un nom de lieu, une adresse, un code postal ou des coordonnées (`lat,lon`). |
| `lang`    | string | Non    | Langue de la réponse. Valeurs prises en charge : `en` (par défaut), `fr`.                                   |
| `keys`    | string | Non    | Liste de sources de données à interroger, séparées par des virgules. Par défaut : **toutes les sources**.   |

### Valeurs prises en charge pour `keys`

| Clé         | Description                                                                                                     |
| ----------- | --------------------------------------------------------------------------------------------------------------- |
| `geonames`  | Base de données toponymiques du Canada (BDTC) de la Commission de toponymie du Canada (noms de lieux officiels) |
| `nominatim` | Nominatim d’OpenStreetMap (géocodage d’adresses et de lieux)                                                    |
| `locate`    | Service Géolocalisation de RNCan (données géographiques supplémentaires)                                        |
| `fsa`       | Régions de tri d’acheminement (les 3 premiers caractères des codes postaux)                                     |
| `nts`       | Système national de référence cartographique (références de feuillets cartographiques)                          |

---

## Exemple d’appel à l’API

```http
GET https://geolocator.api.geo.ca/?q=ottawa&lang=en&keys=geonames,nominatim,locate,fsa,nts
```

---

## Structure de la réponse

L’API Géolocaliseur retourne un **tableau JSON plat** d’objets de résultats. Chaque objet représente une correspondance provenant d’une source de données spécifique et inclut un champ `key` identifiant son origine.

```json
[
  { "key": "geonames", ... },
  { "key": "nominatim", ... },
  { "key": "locate", ... }
]
```

Cette conception permet de fusionner, classer, filtrer ou regrouper côté client les résultats provenant de plusieurs sources.

---

### Champs communs (tous les résultats)

| Champ      | Type         | Description                                                                           |
| ---------- | ------------ | ------------------------------------------------------------------------------------- |
| `key`      | string       | Identifiant de la source de données (`geonames`, `nominatim`, `locate`, `fsa`, `nts`) |
| `name`     | string       | Nom ou libellé du lieu                                                                |
| `province` | string       | Nom de la province ou du territoire                                                   |
| `category` | string       | Type d’entité ou de résultat (p. ex. Ville, Rivière, Rue, Intersection)               |
| `lat`      | number       | Latitude (WGS84)                                                                      |
| `lng`      | number       | Longitude (WGS84)                                                                     |
| `bbox`     | array | null | Boîte englobante `[ouest, sud, est, nord]`, lorsque disponible                        |
| `tag`      | array | null | Qualificatifs ou métadonnées supplémentaires provenant de la source                   |

---

## Exemples complets de réponses

### Exemple : recherche multi-sources (`q=ottawa`)

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

### Exemple : recherche par code postal / RTA (`q=k1s&keys=locate`)

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

## Exemples d’utilisation

### Recherche par nom de ville

```http
GET https://geolocator.api.geo.ca/?q=vancouver&lang=en&keys=geonames,nominatim
```

### Recherche par code postal / RTA

Remarque : lorsque des codes postaux complets sont fournis, l’API tronque automatiquement vers la région de tri d’acheminement (les 3 premiers caractères).

```http
GET https://geolocator.api.geo.ca/?q=K1A&lang=en&keys=fsa
```

### Résultats en français

```http
GET https://geolocator.api.geo.ca/?q=montreal&lang=fr&keys=geonames,nominatim,locate,fsa,nts
```

---

## CORS et utilisation côté client

* CORS est activé, permettant l’utilisation directe à partir d’applications web
* Conçu pour prendre en charge des clients frontaux et cartographiques légers

---

## Limites de taux et bonnes pratiques

* Le service est fourni **gratuitement** pour une utilisation raisonnable par le public, le secteur public et la recherche
* Des réponses mises en cache sont utilisées lorsque possible afin de réduire les requêtes répétées
* Utilisez le paramètre `keys` pour limiter les requêtes aux ensembles de données requis
* Pour des cas d’utilisation à volume élevé ou de géocodage en masse, veuillez communiquer avec les responsables à l’adresse [geo@nrcan-rncan.gc.ca](mailto:geo@nrcan-rncan.gc.ca)

---

## Structure du dépôt (vue d’ensemble)

* `backend/{api-lambda,api-forward-sortation-area,api-nts-grid,api-geolocation-mock}` – Implémentation backend de l’API à l’aide d’AWS Lambda
* `backend/jupyter-notebooks` – Indexation de recherche et ajustement de la pertinence dans AWS OpenSearch
* `helpers / services` – Adaptateurs spécifiques aux sources et logique de normalisation

---

## Ressources connexes

* **Dépôt GitHub** : Canadian-Geospatial-Platform/geoview-api-geolocator
* **GEO.ca** : [https://app.geo.ca](https://app.geo.ca)

---

## Soutien et contributions

* Signalez des bogues ou proposez des fonctionnalités via les **issues GitHub**
* Les contributions sont les bienvenues conformément aux lignes directrices open source du gouvernement du Canada

**Contact** :
`geo@nrcan-rncan.gc.ca`

---

## Licence et attribution

© Sa Majesté le Roi du chef du Canada, représenté par le ministre des Ressources naturelles.

Ce projet est publié sous la licence open source applicable du gouvernement du Canada.

---

*Dernière mise à jour : décembre 2025*
