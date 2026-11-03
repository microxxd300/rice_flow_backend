"""
Save OpenLandMap-soildb soil maps (2020-2022, 0-30 cm, 120 m, CC BY 4.0) for the Panabo
City area in apps/environmental/data/panabo_openlandmap.npz, which services/openlandmap.py
reads at runtime. Only the Panabo window is read from each global map (HTTP range reads).

Source: OpenLandMap-soildb (OpenGeoHub), https://doi.org/10.5281/zenodo.15608972
  pH in water ............ https://zenodo.org/records/15471105
  clay / sand / silt % ... https://zenodo.org/records/15528401 / 15528413 / 15528425
  organic carbon g/kg .... https://zenodo.org/records/15535760
  bulk density ........... https://zenodo.org/records/15471055

Needs `rasterio` (one-time tool only; the runtime lookup needs just numpy):
  pip install rasterio
  python manage.py load_openlandmap
"""
import json
import os
import urllib.request

import numpy as np
from django.core.management.base import BaseCommand, CommandError

from apps.environmental.services.openlandmap import LAYERS, OPENLANDMAP_FILE
from apps.farms.location_check import BBOX

# Zenodo record of each layer's 2020-2022 0-30 cm map
RECORDS = {'ph': 15471105, 'clay': 15528401, 'sand': 15528413, 'silt': 15528425,
           'soc': 15535760, 'bd': 15471055}


def _mean_map_url(record_id):
    with urllib.request.urlopen(f'https://zenodo.org/api/records/{record_id}', timeout=60) as r:
        files = json.load(r)['files']
    mean = next((f for f in files if '_m_' in f['key']), None)
    if mean is None:
        raise CommandError(f'No mean map in Zenodo record {record_id}')
    return mean['key'], mean['links']['self']


class Command(BaseCommand):
    help = 'Save OpenLandMap-soildb soil maps for Panabo City (apps/environmental/data/).'

    def handle(self, *args, **opts):
        try:
            import rasterio
            from rasterio.windows import from_bounds
        except ImportError:
            raise CommandError('Needs rasterio. Run: pip install rasterio')
        os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')

        south, west, north, east = BBOX
        arrays, grid = {}, None
        for layer in LAYERS:
            key, url = _mean_map_url(RECORDS[layer])
            with rasterio.open('/vsicurl/' + url) as ds:
                window = from_bounds(west, south, east, north, ds.transform).round_offsets().round_lengths()
                raw = ds.read(1, window=window)
                t = ds.window_transform(window)
                values = raw.astype(np.float32) * (ds.scales[0] or 1.0) + (ds.offsets[0] or 0.0)
                if ds.nodata is not None:
                    values[raw == ds.nodata] = np.nan
                this_grid = (round(t.c, 9), round(t.f, 9), round(t.a, 12), round(-t.e, 12), raw.shape)
            if grid is None:
                grid = this_grid
            elif this_grid != grid:
                raise CommandError(f'{layer} is on a different grid than ph: {this_grid} vs {grid}')
            arrays[layer] = values
            finite = values[np.isfinite(values)]
            self.stdout.write(f'{layer:<5} {key[:58]}  {raw.shape}  '
                              f'median {np.median(finite) if finite.size else float("nan"):.2f}')

        west0, north0, res_x, res_y, _ = grid
        OPENLANDMAP_FILE.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(OPENLANDMAP_FILE, west=west0, north=north0, res_x=res_x, res_y=res_y,
                            **{k: v.astype(np.float32) for k, v in arrays.items()})
        self.stdout.write(self.style.SUCCESS(
            f'Saved {OPENLANDMAP_FILE.name} ({OPENLANDMAP_FILE.stat().st_size // 1024} KB).'))
