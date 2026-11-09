from django.test import SimpleTestCase

from apps.environmental.views import weather_outlook


class OutlookHeatTests(SimpleTestCase):
    def test_hottest_hour_of_the_next_day(self):
        hourly = {'temperature_2m': [20] + [30] * 23 + [36] + [50] * 5}
        self.assertEqual(weather_outlook(hourly, 1)['temp_c_max_24h'], 36)

    def test_no_data_is_zero(self):
        self.assertEqual(weather_outlook({}, 0)['temp_c_max_24h'], 0)
