"""
Keep Panabo City's 40 barangays from the national barangay boundaries and save them in
apps/farms/land_data/panabo_barangays.geojson, which barangays.py reads at runtime.

Source: barangay-boundaries-repository v2026.4.13.0 (snapshot 2023-10-24), built from NAMRIA
administrative-boundary shapefiles (v2023-11-06) and PSA PSGC codes:
  https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases
The national file is simplified at 0.005 deg (~550 m), so borders are approximate; a pin in a
gap between barangays gets the nearest one.

  python manage.py load_barangays --geojson <path>/barangays.geojson
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.farms.barangays import BARANGAYS_FILE

PANABO_PSGC = 'PH1102315'   # City of Panabo, Davao del Norte


class Command(BaseCommand):
    help = "Save Panabo City's barangay boundaries (apps/farms/land_data/)."

    def add_arguments(self, parser):
        parser.add_argument('--geojson', required=True, help='barangays.geojson from the release')

    def handle(self, *args, **opts):
        with open(opts['geojson'], encoding='utf-8') as f:
            national = json.load(f)
        features = [
            {
                'type': 'Feature',
                'properties': {'name': ft['properties']['psgc_name'], 'psgc': ft['properties']['psgc_code']},
                'geometry': ft['geometry'],
            }
            for ft in national['features']
            if ft['properties'].get('ADM3_PCODE') == PANABO_PSGC
        ]
        if not features:
            raise CommandError(f'No barangays of {PANABO_PSGC} (Panabo City) in the file.')
        features.sort(key=lambda ft: ft['properties']['name'])
        BARANGAYS_FILE.write_text(json.dumps({
            'type': 'FeatureCollection',
            'source': 'NAMRIA boundaries v2023-11-06 + PSA PSGC, via barangay-boundaries-repository v2026.4.13.0',
            'features': features,
        }, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(
            f'Saved {len(features)} barangays ({BARANGAYS_FILE.stat().st_size // 1024} KB).'))
