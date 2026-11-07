"""
Is a farm pin on farmland? Checks the pin against two clipped datasets built by
`manage.py load_land_data`:
  - Google Open Buildings v3 footprints  -> is the pin on a roof?
  - ESA WorldCover 10 m 2021 land cover  -> is the pin in town, water, forest?
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA_DIR       = Path(__file__).resolve().parent / 'land_data'
LANDCOVER_FILE = DATA_DIR / 'panabo_landcover.npz'
BUILDINGS_FILE = DATA_DIR / 'panabo_buildings.npz'
# Panabo City administrative boundary (OpenStreetMap relation 11768007, ODbL). Small and
# committed, unlike the .npz files, so the outside-Panabo check also works in CI.
BOUNDARY_FILE  = DATA_DIR / 'panabo_boundary.geojson'

# (south, west, north, east): Panabo City extent from the MGB XI geohazard grid, plus ~1 km
BBOX = (7.21, 125.53, 7.465, 125.73)

# Below this, the detector often mistakes sheds and rice-drying slabs for buildings
MIN_BUILDING_CONFIDENCE = 0.70

LAND_COVER_NAMES = {
    10: 'Tree cover', 20: 'Shrubland', 30: 'Grassland', 40: 'Cropland',
    50: 'Built-up', 60: 'Bare / sparse vegetation', 70: 'Snow and ice',
    80: 'Permanent water', 90: 'Herbaceous wetland', 95: 'Mangroves',
    100: 'Moss and lichen',
}

# Only these classes warn. Tree cover does not: in Panabo, banana and coconut
# plantations surround the paddies (68-69% Tree cover even around Nanyo and
# Quezon, the top rice barangays in FIMS), so it would flag real rice farms.
# Flooded paddies often read as Herbaceous wetland, which is also fine.
WARN_REASON_BY_CLASS = {50: 'built_up', 80: 'water', 95: 'mangrove'}

MESSAGES = {
    'ok':          'This location looks like farmland.',
    'on_building': 'This pin is on a building. Move it to your rice field.',
    'built_up':    'This pin is in a built-up area (town, school, or roads). Move it to your rice field.',
    'water':       'This pin is on water. Move it to your rice field.',
    'mangrove':    'This pin is in a mangrove area. Move it to your rice field.',
    'unchecked':   'This location could not be checked.',
    'outside_panabo': 'This pin is outside Panabo City. RiceFlow is for rice farms in Panabo City. Move it to your farm.',
}


@lru_cache(maxsize=1)
def _landcover():
    if not LANDCOVER_FILE.exists():
        return None
    d = np.load(LANDCOVER_FILE)
    return {k: d[k] for k in d.files}


@lru_cache(maxsize=1)
def _panabo_boundary():
    if not BOUNDARY_FILE.exists():
        return None
    geometry = json.loads(BOUNDARY_FILE.read_text(encoding='utf-8'))['features'][0]['geometry']
    return np.array(geometry['coordinates'][0], dtype=float)  # outer ring, (lon, lat)


@lru_cache(maxsize=1)
def _buildings():
    if not BUILDINGS_FILE.exists():
        return None
    d = np.load(BUILDINGS_FILE)
    return {k: d[k] for k in d.files}


def in_coverage(lat: float, lon: float) -> bool:
    south, west, north, east = BBOX
    return south <= lat <= north and west <= lon <= east


def in_panabo(lat: float, lon: float) -> bool:
    """Inside the Panabo City boundary (the bounding box if the boundary file is missing)."""
    ring = _panabo_boundary()
    if ring is None:
        return in_coverage(lat, lon)
    return _inside_ring(lon, lat, ring)


def land_cover_at(lat: float, lon: float):
    """WorldCover class code at the point, or None when outside the data."""
    lc = _landcover()
    if lc is None:
        return None
    row = int((float(lc['north']) - lat) / float(lc['res_y']))
    col = int((lon - float(lc['west'])) / float(lc['res_x']))
    grid = lc['classes']
    if not (0 <= row < grid.shape[0] and 0 <= col < grid.shape[1]):
        return None
    code = int(grid[row, col])
    return code or None


def _inside_ring(x: float, y: float, ring: np.ndarray) -> bool:
    xi, yi = ring[:, 0], ring[:, 1]
    xj, yj = np.roll(xi, 1), np.roll(yi, 1)
    crosses = (yi > y) != (yj > y)
    with np.errstate(divide='ignore', invalid='ignore'):
        x_edge = (xj - xi) * (y - yi) / (yj - yi) + xi
    return bool(np.count_nonzero(crosses & (x < x_edge)) % 2)


def on_building(lat: float, lon: float):
    """True if the point is inside a building footprint; None when data is missing."""
    b = _buildings()
    if b is None:
        return None
    box = b['bounds']
    hits = np.flatnonzero((box[:, 0] <= lon) & (box[:, 2] >= lon)
                          & (box[:, 1] <= lat) & (box[:, 3] >= lat))
    offsets, coords = b['offsets'], b['coords']
    return any(_inside_ring(lon, lat, coords[offsets[i]:offsets[i + 1]]) for i in hits)


def check_pin(lat: float, lon: float) -> dict:
    """status is 'ok', 'warning', 'outside' or 'unchecked'; reason is the machine-readable code.

    'outside' means the pin is not in Panabo City; the app does not let the farmer keep it.
    """
    if not in_panabo(lat, lon):
        return _result('outside', 'outside_panabo', None, None)

    building = on_building(lat, lon)
    code = land_cover_at(lat, lon)
    land_cover = LAND_COVER_NAMES.get(code)

    if building is None and code is None:
        return _result('unchecked', None, land_cover, building)
    if building:
        return _result('warning', 'on_building', land_cover, building)
    if code in WARN_REASON_BY_CLASS:
        return _result('warning', WARN_REASON_BY_CLASS[code], land_cover, building)
    return _result('ok', None, land_cover, building)


def _result(status, reason, land_cover, building) -> dict:
    return {
        'status':      status,
        'reason':      reason,
        'land_cover':  land_cover,
        'on_building': building,
        'message':     MESSAGES[reason or ('ok' if status == 'ok' else 'unchecked')],
    }


def location_flag(result: dict) -> str:
    """Compact value stored on Farm.location_flag for admin review."""
    return result['reason'] or result['status']
