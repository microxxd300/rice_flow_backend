from types import SimpleNamespace
from unittest import skipUnless

import numpy as np
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.farms import location_check as lc
from apps.farms.serializers import FarmSerializer
from apps.farms.views import FarmLocationCheckView

# The clipped land-data files are gitignored (rebuild with `manage.py load_land_data`),
# so tests that read them skip where the files are absent, e.g. in CI.
HAS_LAND_DATA = lc.LANDCOVER_FILE.exists() and lc.BUILDINGS_FILE.exists()
needs_land_data = skipUnless(HAS_LAND_DATA, 'land data missing: run manage.py load_land_data')


def _pixel_center(code: int, skip_buildings: bool = True):
    """Centre of a land-cover pixel with the given class, away from any building."""
    L = lc._landcover()
    rows, cols = np.nonzero(L['classes'] == code)
    for i in np.linspace(0, len(rows) - 1, 200).astype(int):
        lat = float(L['north']) - (rows[i] + 0.5) * float(L['res_y'])
        lon = float(L['west']) + (cols[i] + 0.5) * float(L['res_x'])
        if lc.in_panabo(lat, lon) and not (skip_buildings and lc.on_building(lat, lon)):
            return lat, lon
    raise AssertionError(f'no usable pixel for class {code}')


def _building_center():
    """Centre of the first building inside Panabo City."""
    b = lc._buildings()
    for i in range(len(b['offsets']) - 1):
        ring = b['coords'][b['offsets'][i]:b['offsets'][i + 1]]
        lon, lat = ring[:-1].mean(axis=0)
        if lc.in_panabo(float(lat), float(lon)):
            return float(lat), float(lon)
    raise AssertionError('no building inside Panabo')


@needs_land_data
class CheckPinTests(SimpleTestCase):
    def test_data_files_present(self):
        self.assertIsNotNone(lc._landcover())
        self.assertIsNotNone(lc._buildings())

    def test_outside_panabo_is_outside(self):
        r = lc.check_pin(14.5995, 120.9842)  # Manila
        self.assertEqual((r['status'], r['reason']), ('outside', 'outside_panabo'))
        self.assertEqual(lc.location_flag(r), 'outside_panabo')

    def test_pin_on_building_warns(self):
        r = lc.check_pin(*_building_center())
        self.assertEqual((r['status'], r['reason']), ('warning', 'on_building'))
        self.assertTrue(r['on_building'])

    def test_pin_on_water_warns(self):
        r = lc.check_pin(*_pixel_center(80))
        self.assertEqual((r['status'], r['reason']), ('warning', 'water'))

    def test_pin_on_cropland_is_ok(self):
        r = lc.check_pin(*_pixel_center(40))
        self.assertEqual(r['status'], 'ok')
        self.assertEqual(r['land_cover'], 'Cropland')
        self.assertFalse(r['on_building'])

    def test_tree_cover_does_not_warn(self):
        r = lc.check_pin(*_pixel_center(10))
        self.assertEqual(r['status'], 'ok')

    def test_serializer_flag(self):
        self.assertEqual(FarmSerializer._flag(*_building_center()), 'on_building')
        self.assertEqual(FarmSerializer._flag(*_pixel_center(40)), 'ok')


class CheckLocationEndpointTests(SimpleTestCase):
    def _get(self, params):
        req = APIRequestFactory().get('/api/farms/check-location/', params)
        force_authenticate(req, user=SimpleNamespace(is_authenticated=True, pk=1))
        return FarmLocationCheckView.as_view()(req)

    def test_requires_lat_lon(self):
        self.assertEqual(self._get({'lat': '7.3'}).status_code, 400)
        self.assertEqual(self._get({'lat': 'x', 'lon': '125.6'}).status_code, 400)
        self.assertEqual(self._get({'lat': '95', 'lon': '125.6'}).status_code, 400)

    @needs_land_data
    def test_returns_check_result(self):
        lat, lon = _building_center()
        res = self._get({'lat': lat, 'lon': lon})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['reason'], 'on_building')
        self.assertIn('message', res.data)


class PanaboBoundaryTests(SimpleTestCase):
    """Uses the committed boundary file, so it runs in CI too."""

    def test_boundary_file_present(self):
        self.assertIsNotNone(lc._panabo_boundary())

    def test_points_inside_and_outside_panabo(self):
        self.assertTrue(lc.in_panabo(7.3086, 125.6830))       # city center
        self.assertTrue(lc.in_panabo(7.3300, 125.6200))       # rice area, west
        self.assertFalse(lc.in_panabo(7.46496, 125.57712))    # Balagunan, Santo Tomas (inside the old box)
        self.assertFalse(lc.in_panabo(37.4220, -122.0840))    # emulator default GPS (California)
        self.assertFalse(lc.in_panabo(7.0700, 125.6100))      # Davao City

    def test_outside_pin_is_reported_as_outside(self):
        r = lc.check_pin(7.46496, 125.57712)
        self.assertEqual((r['status'], r['reason']), ('outside', 'outside_panabo'))
        self.assertIn('outside Panabo City', r['message'])


class FarmOutsidePanaboTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from apps.accounts.models import User
        self.user = User.objects.create_user(username='farmer', password='pass12345')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def farm(self, lat, lon):
        return {'name': 'Test', 'barangay': 'Gredu', 'latitude': lat, 'longitude': lon, 'area_hectares': 1}

    def test_farm_outside_panabo_is_refused(self):
        r = self.client.post('/api/farms/', self.farm(37.422, -122.084), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('outside Panabo City', str(r.json()['latitude']))

    def test_farm_inside_panabo_is_saved(self):
        r = self.client.post('/api/farms/', self.farm(7.33, 125.62), format='json')
        self.assertEqual(r.status_code, 201)

    def test_moving_a_farm_outside_panabo_is_refused(self):
        farm_id = self.client.post('/api/farms/', self.farm(7.33, 125.62), format='json').json()['id']
        r = self.client.patch(f'/api/farms/{farm_id}/', {'latitude': 7.46496, 'longitude': 125.57712}, format='json')
        self.assertEqual(r.status_code, 400)
