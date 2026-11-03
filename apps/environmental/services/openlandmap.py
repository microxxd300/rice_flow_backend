"""
Soil at a point from the OpenLandMap-soildb maps (2020-2022, 0-30 cm, 120 m) saved for
the Panabo area by `manage.py load_openlandmap`. Local, so a scan never waits on a remote
soil service; SoilGrids is the backup when this file or a pixel has no data.

Values come back in SoilGrids' units, so get_soil_data() treats both sources the same.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np

OPENLANDMAP_FILE = Path(__file__).resolve().parent.parent / 'data' / 'panabo_openlandmap.npz'
LAYERS = ('ph', 'clay', 'sand', 'silt', 'soc', 'bd')

# OpenLandMap unit -> SoilGrids unit (pH x10; % -> g/kg; g/kg -> dg/kg; g/cm3 -> cg/cm3)
TO_SOILGRIDS = {'ph': ('phh2o', 10), 'clay': ('clay', 10), 'sand': ('sand', 10),
                'silt': ('silt', 10), 'soc': ('soc', 10), 'bd': ('bdod', 100)}


@lru_cache(maxsize=1)
def _grid():
    if not OPENLANDMAP_FILE.exists():
        return None
    d = np.load(OPENLANDMAP_FILE)
    return {k: d[k] for k in d.files}


def openlandmap_values(lat: float, lon: float) -> dict:
    """{SoilGrids property name: value} at the point; {} outside the saved area or the file."""
    g = _grid()
    if g is None:
        return {}
    row = int((float(g['north']) - lat) / float(g['res_y']))
    col = int((lon - float(g['west'])) / float(g['res_x']))
    shape = g['ph'].shape
    if not (0 <= row < shape[0] and 0 <= col < shape[1]):
        return {}
    props = {}
    for layer, (name, factor) in TO_SOILGRIDS.items():
        v = float(g[layer][row, col])
        if np.isfinite(v):
            props[name] = round(v * factor, 1)   # float32 grid: drop the 1e-7 noise
    return props
