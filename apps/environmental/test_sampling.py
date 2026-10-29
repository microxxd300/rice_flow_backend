from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.environmental.models import EnvironmentalScan
from apps.environmental.services.sampling import (
    M_PER_DEG_LAT, VARIES_MESSAGE, combine_soil, sample_points,
)
from apps.environmental.services.soilgrids import get_soil_data
from apps.farms.models import Farm

PIN = (7.3086, 125.6830)


def soil(ph, clay, sand=30.0):
    return {'ph': ph, 'clay_pct': clay, 'sand_pct': sand, 'silt_pct': 100 - clay - sand,
            'organic_matter': 2.5, 'bulk_density': 1.3, 'nitrogen_ppm': 15.0, 'cec': 20.0,
            'texture': 'ignored', 'drainage': 'ignored'}


class SamplePointsTests(SimpleTestCase):
    def test_no_area_means_pin_only(self):
        self.assertEqual(sample_points(*PIN, None), [PIN])
        self.assertEqual(sample_points(*PIN, 0), [PIN])

    def test_points_start_at_the_pin_and_stay_inside_the_farm(self):
        points = sample_points(*PIN, 40)  # 40 ha: radius ~357 m, samples at ~250 m
        self.assertEqual(points[0], PIN)
        self.assertGreater(len(points), 1)
        for lat, lon in points[1:]:
            north_south_m = abs(lat - PIN[0]) * M_PER_DEG_LAT
            self.assertLess(north_south_m, 357)

    def test_points_in_the_same_soil_pixel_are_queried_once(self):
        # 0.5 ha: samples ~28 m from the pin, mostly inside the pin's 250 m SoilGrids pixel
        self.assertLessEqual(len(sample_points(*PIN, 0.5)), 3)


class CombineSoilTests(SimpleTestCase):
    def test_averages_and_rederives_texture(self):
        combined, sampling = combine_soil([soil(6.0, 38), soil(6.2, 40)])
        self.assertEqual(combined['ph'], 6.1)
        self.assertEqual(combined['clay_pct'], 39.0)
        self.assertEqual(combined['texture'], 'clay loam')        # from the averaged clay/sand
        self.assertEqual(combined['drainage'], 'poorly drained')  # clay > 35
        self.assertEqual(sampling['points'], 2)
        self.assertFalse(sampling['varies'])
        self.assertEqual(sampling['message'], '')

    def test_large_ph_spread_is_flagged(self):
        _, sampling = combine_soil([soil(5.6, 30), soil(6.4, 31)])
        self.assertTrue(sampling['varies'])
        self.assertEqual(sampling['ph_range'], [5.6, 6.4])
        self.assertEqual(sampling['message'], VARIES_MESSAGE)

    def test_large_clay_spread_is_flagged(self):
        _, sampling = combine_soil([soil(6.0, 25), soil(6.0, 40)])
        self.assertTrue(sampling['varies'])

    def test_points_without_soilgrids_data_are_left_out(self):
        default = {**soil(6.2, 35), 'from_soilgrids': False}   # built-up area: defaults only
        real = {**soil(5.2, 37.4), 'from_soilgrids': True}
        combined, sampling = combine_soil([default, real])
        self.assertEqual(combined['ph'], 5.2)
        self.assertEqual(sampling['points'], 1)
        self.assertEqual(sampling['points_without_data'], 1)
        self.assertFalse(sampling['estimated'])

    def test_no_point_with_data_is_marked_estimated(self):
        default = {**soil(6.2, 35), 'from_soilgrids': False}
        combined, sampling = combine_soil([default, default])
        self.assertEqual(combined['ph'], 6.2)  # same values as before sampling existed
        self.assertTrue(sampling['estimated'])


@mock.patch('apps.environmental.views.get_elevation', return_value=20.0)
@mock.patch('apps.environmental.views.get_rainfall_summary',
            return_value={'annual': 2600.0, 'wet_season': 1500.0, 'dry_season': 1100.0})
@mock.patch('apps.environmental.views.get_current_weather', return_value={
    'avg_temperature': 27.0, 'temp_at_flowering': 27.0, 'weekly_rainfall_mm': 100.0,
    'humidity_pct': 80.0, 'solar_radiation': 17.0, 'wind_speed_ms': 2.0, 'sunshine_hours': 6.0})
class ScanSamplingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='farmer', password='pass12345')
        self.farm = Farm.objects.create(user=self.user, name='Big farm', barangay='Gredu',
                                        latitude=PIN[0], longitude=PIN[1], area_hectares=40)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def scan(self):
        return self.client.post(f'/api/environmental/scan/{self.farm.id}/', {}, format='json')

    def test_scan_averages_soil_across_the_farm(self, *_):
        readings = iter([soil(5.6, 30), soil(6.4, 32), soil(6.0, 31), soil(6.0, 31), soil(6.0, 31)])
        with mock.patch('apps.environmental.views.get_soil_data', side_effect=lambda lat, lon: next(readings)) as get:
            r = self.scan()

        self.assertEqual(r.status_code, 201)
        sampling = r.json()['soil_sampling']
        self.assertEqual(sampling['points'], get.call_count)
        self.assertGreater(sampling['points'], 1)
        self.assertTrue(sampling['varies'])
        self.assertEqual(sampling['message'], VARIES_MESSAGE)
        saved = EnvironmentalScan.objects.get(pk=r.json()['id'])
        self.assertEqual(saved.soil_ph, r.json()['soil_ph'])
        self.assertTrue(5.6 < saved.soil_ph < 6.4)

    def test_failed_points_are_skipped(self, *_):
        calls = {'n': 0}

        def flaky(lat, lon):
            calls['n'] += 1
            if calls['n'] == 1:
                raise ConnectionError('SoilGrids timeout')
            return soil(6.2, 33)

        with mock.patch('apps.environmental.views.get_soil_data', side_effect=flaky):
            r = self.scan()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['soil_sampling']['points'], calls['n'] - 1)
        self.assertEqual(r.json()['soil_ph'], 6.2)

    def test_all_points_failing_uses_the_fallback(self, *_):
        with mock.patch('apps.environmental.views.get_soil_data', side_effect=ConnectionError):
            r = self.scan()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['soil_sampling']['points'], 0)
        self.assertEqual(r.json()['soil_ph'], 6.2)  # SOIL_FALLBACK


class OrganicMatterUnitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_soc_in_dg_per_kg_becomes_organic_matter_percent(self):
        layers = [{'name': 'soc', 'depths': [{'label': '0-5cm', 'values': {'Q0.5': 613}}]}]  # 6.13 % SOC
        resp = mock.Mock(**{'json.return_value': {'properties': {'layers': layers}}})
        with mock.patch('requests.get', return_value=resp):
            soil = get_soil_data(7.33, 125.62)
        self.assertEqual(soil['organic_matter'], round(6.13 * 1.724, 2))  # 10.57 %, not 61.3

    def test_root_zone_median_is_weighted_by_layer_thickness(self):
        # Panabo pixel: median SOC 351 / 221 / 136 dg/kg; the mean (1085+) is a long-tail artefact
        depths = [{'label': '0-5cm',   'values': {'Q0.5': 351, 'mean': 1085}},
                  {'label': '5-15cm',  'values': {'Q0.5': 221, 'mean': 1137}},
                  {'label': '15-30cm', 'values': {'Q0.5': 136, 'mean': 1226}}]
        resp = mock.Mock(**{'json.return_value': {'properties': {'layers': [{'name': 'soc', 'depths': depths}]}}})
        with mock.patch('requests.get', return_value=resp) as get:
            soil = get_soil_data(7.35, 125.62)
        # (351*5 + 221*10 + 136*15) / 30 = 200.2 dg/kg = 2.0 % SOC → 3.45 % organic matter
        self.assertEqual(soil['organic_matter'], round(200.1667 / 100 * 1.724, 2))
        self.assertEqual(get.call_args.kwargs['params']['value'], 'Q0.5')

    def test_wms_is_used_when_the_rest_api_is_down(self):
        import requests
        from apps.environmental.services import soilgrids

        def fake_get(url, params=None, timeout=None):
            if url == soilgrids.SOILGRIDS_URL:
                raise requests.ConnectionError('REST API paused')
            value = {'soc': 200, 'phh2o': 52}.get(params['map'].split('/')[-1][:-4], 0)
            return mock.Mock(**{'raise_for_status.return_value': None,
                                'text': f'<b>Value: </b><span id="value">{value}</span><br>'})

        with mock.patch('requests.get', side_effect=fake_get) as get:
            soil = get_soil_data(7.36, 125.62)
        self.assertEqual(soil['organic_matter'], round(2.0 * 1.724, 2))
        self.assertEqual(soil['ph'], 5.2)
        self.assertTrue(soil['from_soilgrids'])
        self.assertEqual(get.call_count, 1 + 8 * 3)     # REST, then 8 properties x 3 depths

    def test_missing_soc_keeps_the_default(self):
        resp = mock.Mock(**{'json.return_value': {'properties': {'layers': []}}})
        with mock.patch('requests.get', return_value=resp):
            self.assertEqual(get_soil_data(7.34, 125.62)['organic_matter'], 2.5)


class SeasonalRainfallTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_rain_is_split_into_wet_and_dry_season_months(self):
        from apps.environmental.services.openmeteo import get_rainfall_summary
        daily = {'time': ['2025-11-15', '2026-03-01', '2026-06-10', '2026-09-30'],
                 'precipitation_sum': [100.0, 50.0, 300.0, None]}
        resp = mock.Mock(**{'json.return_value': {'daily': daily}})
        with mock.patch('requests.get', return_value=resp):
            self.assertEqual(get_rainfall_summary(7.33, 125.62),
                             {'annual': 450.0, 'wet_season': 300.0, 'dry_season': 150.0})

    def test_current_season(self):
        from datetime import date
        from apps.environmental.services.openmeteo import current_season
        self.assertEqual(current_season(date(2026, 10, 28)), 'wet')
        self.assertEqual(current_season(date(2026, 1, 15)), 'dry')
