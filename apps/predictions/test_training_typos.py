from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.predictions.services import _get_real_training_data


def harvest(net_kg):
    variety = SimpleNamespace(maturity_days=110, avg_yield_t_ha=5.0)
    farm = SimpleNamespace(area_hectares=1.0, ecosystem='irrigated_lowland')
    cycle = SimpleNamespace(farm=farm, variety=variety)
    return SimpleNamespace(farm_cycle=cycle, area_harvested_ha=1.0, net_yield_kg=net_kg, gross_yield_kg=net_kg,
                           moisture_pct=14)


class TrainingSkipsTyposTests(SimpleTestCase):
    def test_impossible_harvests_never_reach_the_model(self):
        rows = [harvest(5000) for _ in range(30)] + [harvest(90000)]
        scan = SimpleNamespace(soil_ph=6.2, organic_matter=2.0, avg_temperature=27.0, seasonal_rainfall_mm=1800.0,
                               humidity_pct=80.0, elevation_m=20.0, flood_risk='low')
        with patch('apps.progress.models.YieldRecord.objects') as records, \
                patch('apps.environmental.models.EnvironmentalScan.objects') as scans:
            records.select_related.return_value.filter.return_value = rows
            scans.filter.return_value.order_by.return_value.first.return_value = scan
            X, y = _get_real_training_data()
        self.assertEqual(len(y), 30)
        self.assertLessEqual(max(y), 15)
