import json
from typing import Any


def geojson_feature(geometry_json: str | dict, properties: dict[str, Any]) -> dict:
    geometry = json.loads(geometry_json) if isinstance(geometry_json, str) else geometry_json
    return {"type": "Feature", "geometry": geometry, "properties": properties}


def geojson_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def geojson_geometry(geometry_json: str | None) -> dict | None:
    if geometry_json is None:
        return None
    return json.loads(geometry_json) if isinstance(geometry_json, str) else geometry_json


def paginate_query(query: str, params: tuple, page: int, per_page: int) -> tuple[str, tuple]:
    """Append LIMIT/OFFSET to a SQL string and return the updated params tuple."""
    offset = (page - 1) * per_page
    return f"{query} LIMIT %s OFFSET %s", params + (per_page, offset)
