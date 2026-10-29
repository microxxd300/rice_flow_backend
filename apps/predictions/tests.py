import csv
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.farms.models import Farm
from apps.varieties.models import RiceVariety

from . import services
from .models import YieldPredictionModel

# A made-up harvest table with known effects (not the DA data): hybrid +0.6 t/ha,
# rainfed -0.5, upland -0.9, wet season +0.2, and Nanyo +0.8 above other barangays.
COLUMNS = ['municipality', 'barangay', 'season', 'harvest_year', 'ecosystem', 'seed_type', 'yield_t_ha']


def write_fixture_csv(path: Path):
    effects = {'irrigated': 0.0, 'rainfed_lowland': -0.5, 'upland': -0.9}
    places = [('CITY OF PANABO', 'Nanyo', 0.8), ('CITY OF PANABO', 'Gredu', 0.0), ('CARMEN', 'Ising', -0.3)]
    rows = []
    for year in (2022, 2023, 2024, 2025):
        for season, s_eff in (('DS', 0.0), ('WS', 0.2)):
            for eco, e_eff in effects.items():
                for seed, h_eff in (('Hybrid', 0.6), ('Inbred', 0.0)):
                    for muni, brgy, p_eff in places:
                        noise = ((year * 7 + len(brgy) * 3 + len(eco)) % 5 - 2) * 0.02
                        rows.append([muni, brgy, season, year, eco, seed, 4.0 + s_eff + e_eff + h_eff + p_eff + noise])
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)


class RealHarvestModelTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.csv = self.dir / 'harvests.csv'
        write_fixture_csv(self.csv)
        # Never overwrite the real trained models
        patcher = mock.patch.object(services, 'MODELS_DIR', self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def train(self, **kwargs):
        [result] = services.train_all_models(**kwargs)
        YieldPredictionModel.objects.create(**result)
        return result

    def predict(self, **features):
        return services.predict_yield({'season': 'wet', 'municipality': 'CITY OF PANABO',
                                       'barangay': 'Nanyo', 'ecosystem': 'irrigated_lowland', **features})

    def test_trains_on_the_harvest_csv_and_tests_on_the_newest_season(self):
        result = self.train(csv_path=str(self.csv))
        self.assertIn('Test = Wet 2025', result['notes'])
        self.assertGreater(result['r2_score'], 0.9)
        self.assertEqual(self.predict()['model_used'], 'Linear Regression')

    def test_learns_seed_ecosystem_and_location_effects(self):
        self.train(csv_path=str(self.csv))
        hybrid = self.predict(seed_type='Hybrid')['predicted_yield_t_ha']
        inbred = self.predict(seed_type='Inbred')['predicted_yield_t_ha']
        upland = self.predict(seed_type='Inbred', ecosystem='upland')['predicted_yield_t_ha']
        gredu  = self.predict(seed_type='Inbred', barangay='Gredu')['predicted_yield_t_ha']
        self.assertAlmostEqual(hybrid - inbred, 0.6, delta=0.15)
        self.assertLess(upland, inbred)
        self.assertLess(gredu, inbred)

    def test_unknown_barangay_falls_back_to_the_municipality(self):
        self.train(csv_path=str(self.csv))
        result = self.predict(barangay='New Malitbog')
        self.assertEqual(result['model_used'], 'Linear Regression')
        self.assertTrue(3.0 < result['predicted_yield_t_ha'] < 6.5)

    @override_settings(YIELD_TRAINING_CSV='')
    def test_without_the_csv_it_trains_the_synthetic_model(self):
        result = self.train()
        self.assertIn('synthetic', result['notes'])
        self.assertNotEqual(services.predict_yield({'variety_avg_yield': 5})['model_used'], 'heuristic')

    def test_missing_csv_path_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            services.train_all_models(csv_path=str(self.dir / 'nope.csv'))

    def test_predict_endpoint_fills_location_and_seed_from_ids(self):
        self.train(csv_path=str(self.csv))
        user = User.objects.create_user(username='farmer', password='pass12345')
        other = User.objects.create_user(username='other', password='pass12345')
        mine = Farm.objects.create(user=user, name='Mine', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                   area_hectares=1, ecosystem='irrigated_lowland')
        theirs = Farm.objects.create(user=other, name='Theirs', barangay='Gredu', latitude=7.3, longitude=125.68,
                                     area_hectares=1, ecosystem='upland')
        hybrid = RiceVariety.objects.create(variety_id='M1', nsic_code='PSB Rc72H', common_name='Mestizo 1',
                                            ecosystem='irrigated_lowland', season='both', maturity_days=123,
                                            avg_yield_t_ha=6.0, max_yield_t_ha=9.0)
        client = APIClient()
        client.force_authenticate(user)

        def post(**data):
            return client.post('/api/predictions/predict/', {'season': 'wet', **data}, format='json').json()

        with_ids = post(farm_id=mine.id, variety_id=hybrid.id)['predicted_yield_t_ha']
        explicit = self.predict(seed_type='Hybrid')['predicted_yield_t_ha']
        self.assertAlmostEqual(with_ids, explicit, places=2)
        # Another farmer's farm is ignored, not read
        self.assertEqual(post(farm_id=theirs.id, variety_id=hybrid.id)['predicted_yield_t_ha'],
                         self.predict(barangay='', seed_type='Hybrid')['predicted_yield_t_ha'])

    def test_seed_type_for_varieties(self):
        self.assertEqual(services.seed_type_for(RiceVariety(common_name='Mestizo 1', nsic_code='PSB Rc72H')), 'Hybrid')
        self.assertEqual(services.seed_type_for(RiceVariety(common_name='Tubigan 14', nsic_code='NSIC Rc563')), 'Inbred')
