from unittest import mock

import requests

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.environmental.services import cache as cache_service
from apps.environmental.services.soilgrids import get_soil_data

LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
FORECAST = {'current': {'temperature_2m': 30, 'wind_speed_10m': 7.2}, 'hourly': {'time': []}}


def fake_response(payload):
    resp = mock.Mock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


@override_settings(CACHES=LOCMEM)
class WeatherCacheTests(TestCase):
    URL = '/api/environmental/weather/'

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user(username='farmer', password='pass12345'))

    @mock.patch('requests.get', return_value=fake_response(FORECAST))
    def test_second_request_is_a_hit(self, get):
        first = self.client.get(self.URL, {'lat': 7.3, 'lng': 125.68})
        second = self.client.get(self.URL, {'lat': 7.3, 'lng': 125.68})

        self.assertEqual(first['X-Cache'], 'MISS')
        self.assertEqual(second['X-Cache'], 'HIT')
        self.assertEqual(second.json(), first.json())
        get.assert_called_once()

    @mock.patch('requests.get', return_value=fake_response(FORECAST))
    def test_other_location_is_a_miss(self, get):
        self.client.get(self.URL, {'lat': 7.3, 'lng': 125.68})
        other = self.client.get(self.URL, {'lat': 7.5, 'lng': 125.68})

        self.assertEqual(other['X-Cache'], 'MISS')
        self.assertEqual(get.call_count, 2)

    @mock.patch('requests.get', side_effect=[Exception('timeout'), fake_response(FORECAST)])
    def test_errors_are_not_cached(self, get):
        failed = self.client.get(self.URL, {'lat': 7.3, 'lng': 125.68})
        retry = self.client.get(self.URL, {'lat': 7.3, 'lng': 125.68})

        self.assertEqual(failed.status_code, 502)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry['X-Cache'], 'MISS')


class WeatherOutlookTests(TestCase):
    """The rain and wind ahead that the planting guide's weather advice reads."""

    def test_rain_and_wind_are_summed_from_the_current_hour(self):
        from apps.environmental.views import weather_outlook
        hourly = {
            'precipitation':             [9, 1, 2, None] + [0.5] * 50,   # the first hour has passed
            'precipitation_probability': [99, 40, 80, 10] + [20] * 50,
            'wind_speed_10m':            [50, 10, 22.4, 5] + [3] * 50,
        }
        out = weather_outlook(hourly, start=1)
        self.assertEqual(out['rain_mm_6h'], 1 + 2 + 0.5 * 3)
        self.assertEqual(out['rain_prob_6h'], 80)
        self.assertEqual(out['rain_mm_24h'], 1 + 2 + 0.5 * 21)
        self.assertEqual(out['rain_mm_48h'], 1 + 2 + 0.5 * 45)
        self.assertEqual(out['wind_kph_max_12h'], 22)

    def test_no_hourly_data_means_no_rain(self):
        from apps.environmental.views import weather_outlook
        self.assertEqual(weather_outlook({}, 0)['rain_mm_24h'], 0)
        self.assertEqual(weather_outlook({}, 0)['wind_kph_max_12h'], 0)


@override_settings(CACHES=LOCMEM)
class LocationCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        # These tests exercise SoilGrids: leave out the OpenLandMap file saved on this machine
        olm = mock.patch('apps.environmental.services.soilgrids.openlandmap_values', return_value={})
        olm.start()
        self.addCleanup(olm.stop)

    @mock.patch('requests.get', return_value=fake_response({'properties': {'layers': [
        {'name': 'phh2o', 'depths': [{'label': '0-5cm', 'values': {'Q0.5': 64}}]}]}}))
    def test_soil_lookup_is_cached_per_location(self, get):
        first = get_soil_data(7.3, 125.68)
        second = get_soil_data(7.3, 125.68)

        self.assertEqual(first, second)
        self.assertEqual(first['ph'], 6.4)
        get.assert_called_once()

    @mock.patch('requests.get', return_value=fake_response({'properties': {'layers': []}}))
    def test_a_pixel_without_data_is_not_cached(self, get):
        first = get_soil_data(7.3, 125.68)
        get_soil_data(7.3, 125.68)

        self.assertFalse(first['measured'])
        self.assertEqual(get.call_count, 2)          # asked again: defaults are never kept

    def test_an_outage_is_skipped_for_ten_minutes_and_not_cached(self):
        import requests
        from apps.environmental.services import soilgrids

        def down(url, params=None, timeout=None):
            if url == soilgrids.SOILGRIDS_URL:
                raise requests.ConnectionError('503')
            return mock.Mock(**{'raise_for_status.return_value': None,
                                'text': 'GetFeatureInfo results: Search returned no results.'})

        with mock.patch('requests.get', side_effect=down) as get:
            first = get_soil_data(7.3, 125.68)
            calls = get.call_count
            second = get_soil_data(7.31, 125.69)       # another farm, same outage
        self.assertFalse(first['measured'])
        self.assertEqual(first['ph'], 6.2)
        self.assertFalse(second['measured'])
        self.assertEqual(get.call_count, calls)       # skipped: no wait on SoilGrids
        self.assertTrue(cache.get(soilgrids.OUTAGE_KEY))

        cache.delete(soilgrids.OUTAGE_KEY)            # outage over
        layers = {'properties': {'layers': [{'name': 'phh2o', 'depths': [
            {'label': '0-5cm', 'values': {'Q0.5': 66}}]}]}}
        with mock.patch('requests.get', return_value=fake_response(layers)):
            self.assertEqual(get_soil_data(7.3, 125.68)['ph'], 6.6)   # the default was not cached

    def test_unreachable_cache_falls_back_to_fetching(self):
        with mock.patch.object(cache_service.cache, 'get', side_effect=ConnectionError):
            value, hit = cache_service.cached('k', 60, lambda: 42)

        self.assertEqual((value, hit), (42, False))


@override_settings(CACHES=LOCMEM)
class MonthlyRainfallTests(TestCase):
    URL = '/api/environmental/monthly-rainfall/'

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create_user(username='farmer', password='pass12345'))

    @mock.patch('requests.get')
    def test_months_are_averaged_over_three_years(self, get):
        # 10 mm every January day and 2 mm every July day, for three years
        days = [(f'{y}-01-{d:02d}', 10.0) for y in (2023, 2024, 2025) for d in range(1, 32)]
        days += [(f'{y}-07-{d:02d}', 2.0) for y in (2023, 2024, 2025) for d in range(1, 32)]
        get.return_value = fake_response({'daily': {'time': [t for t, _ in days],
                                                    'precipitation_sum': [mm for _, mm in days]}})
        body = self.client.get(self.URL, {'lat': 7.3, 'lng': 125.68}).json()

        self.assertEqual(len(body['months']), 12)
        self.assertEqual(body['months'][0], 310.0)   # 31 days x 10 mm
        self.assertEqual(body['months'][6], 62.0)
        self.assertEqual(body['months'][3], 0.0)

    @mock.patch('requests.get', side_effect=requests.ConnectionError('down'))
    def test_archive_outage_is_a_503(self, get):
        self.assertEqual(self.client.get(self.URL, {'lat': 7.3, 'lng': 125.68}).status_code, 503)
