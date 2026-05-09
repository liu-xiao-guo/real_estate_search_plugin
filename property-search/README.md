# property-search

A Claude-agent-plugin-spec compliant package providing property search capabilities for Elasticsearch. Installable into Elastic Agent Builder (which accepts plugins built to the Claude agent plugin specification) and into Claude Code itself.

Please refer to the the repo at [elastic-property-mcp](https://github.com/justincastilla/elastic-property-mcp) on how to ingest data into Elasticsearch.

## What it provides

- **Skill `/property-search:search`** — natural-language property search against an Elasticsearch index. Includes strict ES|QL conversion rules (semantic-text scoring, correct operators per field, sort order).
- **Geocoding helper** — `geocode_tool.py` converts a street address to `{lat, lon}` via Google Maps so location-radius filters work.

## Layout

```
property-search/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── search/
│       └── SKILL.md
├── scripts/
│   └── geocode_tool.py
└── README.md
```

## Prerequisites

- An Elasticsearch index named `properties` with a `body_content_semantic_text` (`semantic_text` type) field, plus `location` (`geo_point`), `bedrooms`, `bathrooms`, `home_price`, `square_footage`, `tax`, `maintenance_fee`, `property_features`.
- Python 3.9+ with `requests` available, if the geocoder script is invoked locally.
- `GOOGLE_MAPS_API_KEY` environment variable in the agent's runtime, with the Geocoding API enabled.

## Build the installable .zip

The Claude agent plugin format is just a directory; distribute it as a zip of the plugin folder's contents:

```bash
cd /Users/liuxg/python/plugins/property-search
zip -r ../property-search-1.0.0.zip . -x "*.DS_Store" "__pycache__/*"
```

The resulting `property-search-1.0.0.zip` is the installable artifact.

## Install

### Into Elastic Agent Builder

1. Open Kibana → AI Agent Builder → Plugins (Library).
2. Upload `property-search-1.0.0.zip`.
3. Once it appears in the library, assign it to an agent in the current space.

### Into Claude Code (for local testing)

```bash
claude --plugin-dir /Users/liuxg/python/plugins/property-search
```

Then invoke the skill via `/property-search:search` (or let the model auto-invoke based on the skill description).

To test from a hosted zip:

```bash
claude --plugin-url https://your-host/property-search-1.0.0.zip
```

## Versioning

Bump `version` in `.claude-plugin/plugin.json` for each release. Without an explicit `version` and when distributed via git, every commit counts as a new version.

## Security notes

- The geocoder reads `GOOGLE_MAPS_API_KEY` from the environment. Do **not** hardcode the key into `scripts/geocode_tool.py` before zipping — the zip ships to every install.
- Elasticsearch credentials are not handled by this plugin; the agent runtime (Agent Builder) is expected to provide an authenticated ES client/connection.
