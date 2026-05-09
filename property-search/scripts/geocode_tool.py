import os
import sys
import json
import argparse
import requests

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode(address: str, api_key: str) -> dict:
    params = {"address": address, "key": api_key}
    resp = requests.get(GEOCODE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        return {"success": False, "error": data.get("status"), "raw": data}

    result = data["results"][0]
    location = result["geometry"]["location"]
    return {
        "success": True,
        "formatted_address": result["formatted_address"],
        "location": {
            "lat": location["lat"],
            "lon": location["lng"],
        },
        "place_id": result.get("place_id"),
        "types": result.get("types"),
    }


def main():
    parser = argparse.ArgumentParser(description="Geocode an address")
    parser.add_argument("--address", help="Address to geocode")
    args = parser.parse_args()

    try:
        if not sys.stdin.isatty():
            payload = json.load(sys.stdin)
            address = payload.get("address")
        else:
            address = args.address

        if not address:
            raise ValueError("Missing address (provide via --address or stdin JSON)")

        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("Missing GOOGLE_MAPS_API_KEY environment variable")

        result = geocode(address, api_key)
        print(json.dumps(result))
        sys.exit(0 if result["success"] else 1)

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
