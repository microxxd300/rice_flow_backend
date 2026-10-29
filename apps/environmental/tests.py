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


@override_settings(CACHES=LOCMEM)
class LocationCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    @mock.patch('requests.get', return_value=fake_response({'properties': {'layers': []}}))
    def test_soil_lookup_is_cached_per_location(self, get):
        first = get_soil_data(7.3, 125.68)
        second = get_soil_data(7.3, 125.68)

        self.assertEqual(first, second)
        get.assert_called_once()

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
