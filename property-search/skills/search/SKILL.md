---
description: Search Elasticsearch property listings by natural-language query plus optional filters (location radius, bedrooms, bathrooms, price ceiling, features). Geocodes addresses via Google Maps when coordinates are not supplied. Use when the user asks to find homes, apartments, or properties matching criteria.
---

# Property Search

This skill performs property search against an Elasticsearch index using semantic text scoring (`body_content_semantic_text`) plus strict ES|QL filter rules. It also includes a geocoding helper that converts a street address into latitude/longitude so location-radius filters work.

## Geocoding Tool

`geocode_tool.py` (bundled at the plugin root under `scripts/`) converts an address into geographic coordinates using the Google Maps Geocoding API.

### Environment variable

- `GOOGLE_MAPS_API_KEY` — Google Maps API key with Geocoding API enabled.

### Usage

```bash
python scripts/geocode_tool.py --address "1600 Amphitheatre Parkway, Mountain View, CA"
```

Returns JSON of the form:

```json
{
  "success": true,
  "formatted_address": "...",
  "location": { "lat": 37.4224, "lon": -122.0842 },
  "place_id": "...",
  "types": [...]
}
```

The `location.lon` field uses Elasticsearch's naming (Google returns `lng`).

## DSL Search Template

> WARNING: All property searches MUST use the `body_content_semantic_text` field
> for semantic search via `MATCH(body_content_semantic_text, "<user query>")`.
> Do NOT omit this field. It is the primary relevance scoring mechanism.

Reference: https://www.elastic.co/docs/solutions/search/search-templates

```mustache
{
    "_source": false,
    "size": 5,
    "fields": ["title", "tax", "maintenance_fee", "bathrooms", "bedrooms", "square_footage", "home_price", "property_features"],
    "retriever": {
        "standard": {
            "query": {
                "semantic": {
                    "field": "body_content_semantic_text",
                    "query": "{{query}}"
                }
            },
            "filter": {
                "bool": {
                    "must": [
                        {{#distance}}{
                            "geo_distance": {
                                "distance": "{{distance}}",
                                "location": {
                                    "lat": {{latitude}},
                                    "lon": {{longitude}}
                                }
                            }
                        }{{/distance}}
                        {{#bedrooms}},{
                            "range": { "bedrooms": { "gte": {{bedrooms}} } }
                        }{{/bedrooms}}
                        {{#bathrooms}},{
                            "range": { "bathrooms": { "gte": {{bathrooms}} } }
                        }{{/bathrooms}}
                        {{#tax}},{
                            "range": { "tax": { "lte": {{tax}} } }
                        }{{/tax}}
                        {{#maintenance}},{
                            "range": { "maintenance_fee": { "lte": {{maintenance}} } }
                        }{{/maintenance}}
                        {{#square_footage_max}},{
                            "range": {
                                "square_footage": {
                                    "gte": {{#square_footage_min}}{{square_footage_min}}{{/square_footage_min}}{{^square_footage_min}}0{{/square_footage_min}},
                                    "lte": {{square_footage_max}}
                                }
                            }
                        }{{/square_footage_max}}
                        {{#home_price_max}},{
                            "range": {
                                "home_price": {
                                    "gte": {{#home_price_min}}{{home_price_min}}{{/home_price_min}}{{^home_price_min}}0{{/home_price_min}},
                                    "lte": {{home_price_max}}
                                }
                            }
                        }{{/home_price_max}}
                        {{#feature}},{
                            "bool": {
                                "should": [
                                    { "match": { "property_features": { "query": "{{feature}}", "operator": "or" } } }
                                ],
                                "minimum_should_match": 1
                            }
                        }{{/feature}}
                    ]
                }
            }
        }
    }
}
```

---

# MANDATORY ES|QL CONVERSION RULES

When converting the DSL template above to an ES|QL query, follow ALL rules below without exception. Violating any rule produces incorrect results.

## Rule 1 — ALWAYS include `MATCH(body_content_semantic_text, ...)`

`body_content_semantic_text` is a `semantic_text` field and is the primary relevance scoring mechanism. It MUST appear in every query's WHERE clause.

CORRECT:
```esql
FROM properties METADATA _score
| WHERE MATCH(body_content_semantic_text, "<full natural language user query here>")
  AND ...
| SORT _score DESC, home_price ASC
```

WRONG — omitting it causes loose matching and unreliable filter enforcement:
```esql
FROM properties
| WHERE ST_DISTANCE(...) <= 16093
  AND bedrooms == 2
```

## Rule 2 — Use `>=` for `bedrooms` and `bathrooms` (NEVER `==`)

The user specifies a minimum. A property with MORE than the minimum still satisfies the requirement.

CORRECT:
```esql
| WHERE bedrooms >= 2
  AND bathrooms >= 2
```

WRONG — `==` excludes valid properties with 3+ beds/baths:
```esql
| WHERE bedrooms == 2
  AND bathrooms == 2
```

## Rule 3 — Use `<=` for `home_price` (price ceiling, not exact match)

The user specifies a maximum budget. Any property at or below that price qualifies.

CORRECT:
```esql
| WHERE home_price <= 300000
```

WRONG:
```esql
| WHERE home_price == 300000
```

## Rule 4 — Use `OR` operator for `property_features` (NEVER `AND`)

Property feature strings are free-text and rarely contain every keyword. `AND` is overly restrictive.

CORRECT:
```esql
| WHERE MATCH(property_features, "central air tile floors", {"operator": "OR"})
```

WRONG — `AND` requires ALL terms to match simultaneously:
```esql
| WHERE MATCH(property_features, "central air tile", {"operator": "AND"})
```

## Rule 5 — Always sort by `_score DESC` first, then `home_price ASC`

Most semantically relevant results appear first, with price as a tiebreaker.

```esql
| SORT _score DESC, home_price ASC
```

## Canonical Correct ES|QL Template

```esql
FROM properties METADATA _score
| WHERE MATCH(body_content_semantic_text, "<full natural language user query>")
  AND ST_DISTANCE(location, TO_GEOPOINT("POINT(<lon> <lat>)")) <= <distance_in_meters>
  AND bedrooms >= <bedrooms>
  AND bathrooms >= <bathrooms>
  AND home_price <= <home_price_max>
  AND MATCH(property_features, "<feature1> <feature2> ...", {"operator": "OR"})
| KEEP title, url, bedrooms, bathrooms, home_price, square_footage, property_features, location
| SORT _score DESC, home_price ASC
| LIMIT 4
```

### Notes on optional parameters

- Omit `ST_DISTANCE(...)` if no location/distance is specified.
- Omit `bedrooms >= ...` if no bedroom count is specified.
- Omit `bathrooms >= ...` if no bathroom count is specified.
- Omit `home_price <= ...` if no price ceiling is specified.
- Omit `MATCH(property_features, ...)` if no features are specified.
- Distance conversion: 1 mile = 1,609.34 meters (e.g., 10 miles = 16,093 meters).

## Operator Cheat Sheet

| Field                        | Operator           | Reason                                  |
|------------------------------|--------------------|-----------------------------------------|
| `bedrooms`                   | `>=`               | Minimum requirement                     |
| `bathrooms`                  | `>=`               | Minimum requirement                     |
| `home_price`                 | `<=`               | Maximum budget                          |
| `tax`                        | `<=`               | Maximum tax                             |
| `maintenance_fee`            | `<=`               | Maximum fee                             |
| `square_footage`             | `>=` min, `<=` max | Range filter                            |
| `property_features`          | `OR`               | Free-text, partial match valid          |
| `body_content_semantic_text` | `MATCH`            | ALWAYS required, never omit             |

## Workflow

1. If the user's request mentions a place name or address but no coordinates, run `geocode_tool.py` first to obtain `lat`/`lon`.
2. Build the ES|QL query following Rules 1–5 above.
3. Execute against the `properties` index in Elasticsearch.
4. Return up to 4 results sorted by `_score DESC, home_price ASC`.
