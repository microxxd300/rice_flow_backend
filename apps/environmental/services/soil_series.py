"""
Soil series at a farm pin from the BSWM Philippine Soil Series map, clipped to Panabo City
by `manage.py load_soil_series`. BSWM's soil survey names the soil and its texture
("Cabangan clay loam"), so it gives the scan its texture even when SoilGrids is down.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from apps.farms.location_check import _inside_ring

SOIL_SERIES_FILE = Path(__file__).resolve().parent.parent / 'data' / 'panabo_soil_series.geojson'

# The texture classes the suitability rule scores, longest first so "silty clay loam"
# is not read as "clay loam"
TEXTURES = ('sandy clay loam', 'silty clay loam', 'clay loam', 'silty clay', 'silt loam',
            'sandy loam', 'clay', 'loam')


def texture_of(description):
    """'Cabangan clay loam' -> 'clay loam' (None when no known texture is named)."""
    text = description.lower()
    return next((t for t in TEXTURES if text.endswith(t)), None)


@lru_cache(maxsize=1)
def _polygons():
    """[(properties, bounds, [outer ring, *holes]), ...] for every polygon part."""
    if not SOIL_SERIES_FILE.exists():
        return []
    parts = []
    for f in json.loads(SOIL_SERIES_FILE.read_text(encoding='utf-8'))['features']:
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in polys:
            rings = [np.array(r, dtype=float) for r in poly]
            outer = rings[0]
            bounds = (outer[:, 0].min(), outer[:, 1].min(), outer[:, 0].max(), outer[:, 1].max())
            parts.append((f['properties'], bounds, rings))
    return parts


def soil_series_at(lat: float, lon: float):
    """{'series', 'description', 'texture'} for the soil series under the point, or None."""
    for props, (w, s, e, n), rings in _polygons():
        if not (w <= lon <= e and s <= lat <= n):
            continue
        if _inside_ring(lon, lat, rings[0]) and not any(_inside_ring(lon, lat, h) for h in rings[1:]):
            return {**props, 'texture': texture_of(props['description'])}
    return None
