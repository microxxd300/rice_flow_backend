"""
Clip the BSWM Philippine Soil Series map to Panabo City and save it as a small GeoJSON
in apps/environmental/data/, which services/soil_series.py reads at runtime.

Source: Bureau of Soils and Water Management (DA), Philippine Soil Series (shapefile),
https://www.bswm.da.gov.ph/download/philippine-soil-series/ (BSWM content is public domain
unless stated otherwise). The shapefile is in Luzon 1911 (EPSG:4253); the output is WGS 84.

Needs `pyshp`, `shapely` and `rasterio` (one-time tool only; the runtime lookup needs just numpy):
  pip install pyshp shapely rasterio
  python manage.py load_soil_series --shapefile "<path>/PhilSoilSeries.shp"
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.environmental.services.soil_series import SOIL_SERIES_FILE
from apps.farms.location_check import BOUNDARY_FILE

# ~20 m: well below the 1:50,000 map's own detail, and keeps the file small
SIMPLIFY_DEG = 0.0002


class Command(BaseCommand):
    help = 'Clip the BSWM soil series shapefile to Panabo City (apps/environmental/data/).'

    def add_arguments(self, parser):
        parser.add_argument('--shapefile', required=True, help='PhilSoilSeries.shp from BSWM')

    def handle(self, *args, **opts):
        try:
            import shapefile
            from rasterio.warp import transform_geom
            from shapely.geometry import mapping, shape
            from shapely.ops import unary_union
        except ImportError as e:
            raise CommandError(f'{e}. Run: pip install pyshp shapely rasterio')

        panabo = shape(json.loads(BOUNDARY_FILE.read_text(encoding='utf-8'))['features'][0]['geometry'])
        reader = shapefile.Reader(opts['shapefile'])
        features = []
        for sr in reader.iterShapeRecords():
            geom = shape(transform_geom('EPSG:4253', 'EPSG:4326', sr.shape.__geo_interface__))
            if not geom.intersects(panabo):
                continue
            part = geom.intersection(panabo).simplify(SIMPLIFY_DEG, preserve_topology=True)
            if part.is_empty or part.area == 0:
                continue
            if part.geom_type == 'GeometryCollection':
                # Clipping can leave stray lines or points along the boundary; keep the areas
                part = unary_union([g for g in part.geoms if g.geom_type in ('Polygon', 'MultiPolygon')])
                if part.is_empty:
                    continue
            rec = sr.record.as_dict()
            geo = mapping(part)
            # 5 decimals ~ 1 m
            geo['coordinates'] = json.loads(json.dumps(geo['coordinates']),
                                            parse_float=lambda v: round(float(v), 5))
            features.append({
                'type': 'Feature',
                'properties': {'series': rec['SoilSeries'], 'description': rec['SOILDESC']},
                'geometry': geo,
            })

        if not features:
            raise CommandError('No soil series polygons fall inside Panabo City.')
        SOIL_SERIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        SOIL_SERIES_FILE.write_text(json.dumps({
            'type': 'FeatureCollection',
            'source': 'BSWM Philippine Soil Series, clipped to Panabo City (OSM relation 11768007)',
            'features': features,
        }, separators=(',', ':')), encoding='utf-8')
        names = sorted({f['properties']['description'] for f in features})
        self.stdout.write(self.style.SUCCESS(
            f'Saved {len(features)} polygons ({SOIL_SERIES_FILE.stat().st_size // 1024} KB): {", ".join(names)}'))
