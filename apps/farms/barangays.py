"""
Which Panabo barangay a farm pin is in, from the official barangay boundaries saved by
`manage.py load_barangays`. Farmers no longer choose their barangay: it follows the pin.

The boundaries are simplified (~550 m), so a pin can land in a gap between two
barangays; it then gets the nearest one.
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from .location_check import DATA_DIR, _inside_ring

BARANGAYS_FILE = DATA_DIR / 'panabo_barangays.geojson'

# Metres per degree near Panabo (7.3 N): longitude degrees are shorter by cos(lat)
_M_PER_DEG_LAT = 110_574
_M_PER_DEG_LON = 111_320 * np.cos(np.radians(7.3))


@lru_cache(maxsize=1)
def _barangays():
    """[(name, [outer ring, ...]), ...]; rings are (lon, lat) arrays."""
    path = Path(BARANGAYS_FILE)
    if not path.exists():
        return []
    out = []
    for f in json.loads(path.read_text(encoding='utf-8'))['features']:
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        out.append((f['properties']['name'], [np.array(p[0], dtype=float) for p in polys]))
    return out


def _distance_m(lon: float, lat: float, ring: np.ndarray) -> float:
    """Shortest distance from the point to the ring's edges, in metres."""
    xy = np.column_stack(((ring[:, 0] - lon) * _M_PER_DEG_LON, (ring[:, 1] - lat) * _M_PER_DEG_LAT))
    a, b = xy[:-1], xy[1:]
    ab = b - a
    t = np.clip(-(a * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-12), 0, 1)
    nearest = a + ab * t[:, None]
    return float(np.sqrt((nearest ** 2).sum(1)).min())


def barangay_at(lat: float, lon: float):
    """The barangay name at the pin (the nearest one if the pin is between barangays),
    or None when the boundaries file is missing."""
    barangays = _barangays()
    if not barangays:
        return None
    for name, rings in barangays:
        if any(_inside_ring(lon, lat, r) for r in rings):
            return name
    return min(barangays, key=lambda b: min(_distance_m(lon, lat, r) for r in b[1]))[0]
