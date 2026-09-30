from types import SimpleNamespace

import numpy as np
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.farms import location_check as lc
from apps.farms.serializers import FarmSerializer
from apps.farms.views import FarmLocationCheckView


def _pixel_center(code: int, skip_buildings: bool = True):
    """Centre of a land-cover pixel with the given class, away from any building."""
    L = lc._landcover()
    rows, cols = np.nonzero(L['classes'] == code)
    for i in np.linspace(0, len(rows) - 1, 200).astype(int):
        lat = float(L['north']) - (rows[i] + 0.5) * float(L['res_y'])
        lon = float(L['west']) + (cols[i] + 0.5) * float(L['res_x'])
        if lc.in_coverage(lat, lon) and not (skip_buildings and lc.on_building(lat, lon)):
            return lat, lon
    raise AssertionError(f'no usable pixel for class {code}')


def _building_center():
    b = lc._buildings()
    ring = b['coords'][b['offsets'][0]:b['offsets'][1]]
    lon, lat = ring[:-1].mean(axis=0)
    return float(lat), float(lon)


class CheckPinTests(SimpleTestCase):
    def test_data_files_present(self):
        self.assertIsNotNone(lc._landcover())
        self.assertIsNotNone(lc._buildings())

    def test_outside_panabo_is_unchecked(self):
        r = lc.check_pin(14.5995, 120.9842)  # Manila
        self.assertEqual(r['status'], 'unchecked')
        self.assertEqual(lc.location_flag(r), 'unchecked')

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
        force_authenticate(req, user=SimpleNamespace(is_authenticated=True))
        return FarmLocationCheckView.as_view()(req)

    def test_requires_lat_lon(self):
        self.assertEqual(self._get({'lat': '7.3'}).status_code, 400)
        self.assertEqual(self._get({'lat': 'x', 'lon': '125.6'}).status_code, 400)
        self.assertEqual(self._get({'lat': '95', 'lon': '125.6'}).status_code, 400)

    def test_returns_check_result(self):
        lat, lon = _building_center()
        res = self._get({'lat': lat, 'lon': lon})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['reason'], 'on_building')
        self.assertIn('message', res.data)
