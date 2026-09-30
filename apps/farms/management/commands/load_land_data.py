"""
Clip ESA WorldCover and Google Open Buildings to Panabo City and save compact
arrays in apps/farms/land_data/, which location_check.py reads at runtime.

Sources (both CC BY 4.0):
  ESA WorldCover 10 m 2021 v200, tile N06E123 — https://doi.org/10.5281/zenodo.7254221
  Google Open Buildings v3, S2 cell 32f      — https://sites.research.google/gr/open-buildings/

Needs `rasterio` (one-time tool only; the runtime check needs just numpy):
  pip install rasterio
  python manage.py load_land_data --worldcover <tif> --buildings <csv.gz>
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from apps.farms.location_check import (BBOX, BUILDINGS_FILE, DATA_DIR,
                                       LANDCOVER_FILE, MIN_BUILDING_CONFIDENCE)

RING_RE = re.compile(r'\(\(([^()]+)\)')


def _outer_rings(wkt: str):
    """Outer ring of each polygon in a POLYGON / MULTIPOLYGON WKT string."""
    for body in RING_RE.findall(wkt):
        pts = [p.split() for p in body.split(',')]
        yield np.array(pts, dtype=np.float64)


class Command(BaseCommand):
    help = 'Clip ESA WorldCover + Google Open Buildings to Panabo for farm-pin checks.'

    def add_arguments(self, parser):
        parser.add_argument('--worldcover', required=True, help='ESA WorldCover GeoTIFF tile (N06E123)')
        parser.add_argument('--buildings', required=True, help='Open Buildings v3 CSV.gz (cell 32f)')
        parser.add_argument('--min-confidence', type=float, default=MIN_BUILDING_CONFIDENCE)

    def handle(self, *args, **opts):
        wc, bl = Path(opts['worldcover']), Path(opts['buildings'])
        for p in (wc, bl):
            if not p.exists():
                raise CommandError(f'File not found: {p}')
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._clip_worldcover(wc)
        self._clip_buildings(bl, opts['min_confidence'])

    def _clip_worldcover(self, path: Path):
        try:
            import rasterio
            from rasterio.windows import from_bounds
        except ImportError as e:
            raise CommandError('rasterio is required: pip install rasterio') from e

        south, west, north, east = BBOX
        with rasterio.open(path) as src:
            win = from_bounds(west, south, east, north, transform=src.transform).round_offsets().round_lengths()
            data = src.read(1, window=win)
            t = src.window_transform(win)
        np.savez_compressed(LANDCOVER_FILE, classes=data.astype(np.uint8),
                            west=t.c, north=t.f, res_x=t.a, res_y=-t.e)
        counts = dict(zip(*np.unique(data, return_counts=True)))
        self.stdout.write(f'WorldCover: {data.shape[1]}x{data.shape[0]} px -> {LANDCOVER_FILE.name}')
        self.stdout.write(f'  class pixel counts: { {int(k): int(v) for k, v in counts.items()} }')

    def _clip_buildings(self, path: Path, min_conf: float):
        south, west, north, east = BBOX
        bounds, conf, offsets, coords = [], [], [0], []
        seen = 0
        for chunk in pd.read_csv(path, chunksize=500_000,
                                 usecols=['latitude', 'longitude', 'confidence', 'geometry']):
            seen += len(chunk)
            keep = chunk[chunk.latitude.between(south, north)
                         & chunk.longitude.between(west, east)
                         & (chunk.confidence >= min_conf)]
            for c, wkt in zip(keep.confidence.to_numpy(), keep.geometry.to_numpy()):
                for ring in _outer_rings(wkt):
                    coords.append(ring)
                    offsets.append(offsets[-1] + len(ring))
                    bounds.append((ring[:, 0].min(), ring[:, 1].min(), ring[:, 0].max(), ring[:, 1].max()))
                    conf.append(c)
            self.stdout.write(f'  scanned {seen:,} buildings, kept {len(conf):,}')

        if not conf:
            raise CommandError('No buildings found inside the Panabo box — wrong file?')
        np.savez_compressed(BUILDINGS_FILE,
                            bounds=np.array(bounds, dtype=np.float64),
                            confidence=np.array(conf, dtype=np.float32),
                            offsets=np.array(offsets, dtype=np.int64),
                            coords=np.concatenate(coords))
        self.stdout.write(f'Open Buildings: {len(conf):,} buildings (confidence >= {min_conf}) -> {BUILDINGS_FILE.name}')
