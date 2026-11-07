"""Saved predictions, the kept training history, and the automatic retrain."""
import tempfile
from datetime import date
from pathlib import Path
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activity.models import ChangeLog
from apps.farms.models import Farm
from apps.progress.models import FarmCycle, YieldRecord
from apps.varieties.models import RiceVariety

from . import history, services
from .models import YieldPrediction, YieldPredictionModel
from .tests import write_fixture_csv


class YieldHistoryTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.csv = self.dir / 'harvests.csv'
        write_fixture_csv(self.csv)
        patcher = mock.patch.object(services, 'MODELS_DIR', self.dir)   # never touch the real models
        patcher.start()
        self.addCleanup(patcher.stop)
        settings_patch = override_settings(YIELD_TRAINING_CSV=str(self.csv))
        settings_patch.enable()
        self.addCleanup(settings_patch.disable)

        self.user = User.objects.create_user(username='farmer', password='pass12345')
        self.farm = Farm.objects.create(user=self.user, name='Mine', barangay='Nanyo', latitude=7.3,
                                        longitude=125.68, area_hectares=1, ecosystem='irrigated_lowland')
        self.variety = RiceVariety.objects.create(variety_id='T18', nsic_code='NSIC Rc222', common_name='Tubigan 18',
                                                  ecosystem='irrigated_lowland', season='both', maturity_days=113,
                                                  avg_yield_t_ha=5.2, max_yield_t_ha=8)
        self.cycle = FarmCycle.objects.create(farm=self.farm, variety=self.variety, season='wet', year=2026,
                                              planting_date=date(2026, 6, 1))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def train(self):
        new, _ = history.save_training(services.train_all_models())
        return new

    def add_harvests(self, n):
        """n harvests on other farms, recorded straight in the database."""
        for i in range(n):
            farm = Farm.objects.create(user=self.user, name=f'H{i}', barangay='Gredu', latitude=7.3,
                                       longitude=125.68, area_hectares=1, ecosystem='irrigated_lowland')
            cycle = FarmCycle.objects.create(farm=farm, variety=self.variety, season='wet', year=2026,
                                             planting_date=date(2026, 6, 1), status='completed')
            YieldRecord.objects.create(farm_cycle=cycle, harvest_date=date(2026, 9, 25), area_harvested_ha=1.0,
                                       gross_yield_kg=5500, net_yield_kg=5500)

    def predict(self, **data):
        return self.client.post('/api/predictions/predict/', {'season': 'wet', **data}, format='json')

    # ── Training history ────────────────────────────────────────────────

    def test_retraining_keeps_older_models_each_with_its_own_file(self):
        first, second = self.train(), self.train()
        self.assertEqual(YieldPredictionModel.objects.count(), 2)
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertNotEqual(first.model_file, second.model_file)
        self.assertTrue(Path(first.model_file).exists())

    def test_the_admin_retrain_endpoint_keeps_history(self):
        admin = User.objects.create_superuser(username='admin', password='pass12345')
        self.train()
        self.client.force_authenticate(admin)
        res = self.client.post('/api/predictions/train/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(YieldPredictionModel.objects.count(), 2)
        self.assertEqual(YieldPredictionModel.objects.filter(is_active=True).count(), 1)

    # ── Saved predictions ───────────────────────────────────────────────

    def test_a_prediction_is_saved_for_the_farms_crop_and_its_model(self):
        model = self.train()
        res = self.predict(farm_id=self.farm.id, variety_id=self.variety.id)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('model_id', res.json())                       # same response as before
        saved = YieldPrediction.objects.get()
        self.assertEqual((saved.farm_cycle, saved.model), (self.cycle, model))
        self.assertEqual(saved.predicted_t_ha, res.json()['predicted_yield_t_ha'])

        self.predict(farm_id=self.farm.id, variety_id=self.variety.id)  # asked again: same row
        self.assertEqual(YieldPrediction.objects.count(), 1)

    def test_no_prediction_is_saved_without_a_farm_or_after_the_harvest(self):
        self.train()
        self.predict(variety_id=self.variety.id)
        self.assertFalse(YieldPrediction.objects.exists())

        YieldRecord.objects.create(farm_cycle=self.cycle, harvest_date=date(2026, 9, 25),
                                   area_harvested_ha=1.0, gross_yield_kg=5000, net_yield_kg=5000)
        self.predict(farm_id=self.farm.id, variety_id=self.variety.id)
        self.assertFalse(YieldPrediction.objects.exists())

    def test_recording_a_harvest_keeps_the_prediction_made_just_before(self):
        model = self.train()
        res = self.client.post(f'/api/progress/cycles/{self.cycle.id}/yield/', {
            'harvest_date': '2026-09-25', 'area_harvested_ha': 1.0,
            'gross_yield_kg': 5200, 'net_yield_kg': 5200}, format='json')
        self.assertEqual(res.status_code, 201)
        saved = YieldPrediction.objects.get(farm_cycle=self.cycle)
        self.assertEqual(saved.model, model)
        self.assertTrue(1.0 <= saved.predicted_t_ha <= 12.0)

    # ── Automatic retraining ────────────────────────────────────────────

    def test_retrains_after_five_new_harvests_not_before(self):
        self.train()
        self.add_harvests(history.AUTO_RETRAIN_EVERY - 1)
        self.assertIsNone(history.retrain_if_due())
        self.add_harvests(1)
        new = history.retrain_if_due()
        self.assertIsNotNone(new)
        self.assertEqual(new.harvests_seen, history.AUTO_RETRAIN_EVERY)
        self.assertEqual(history.new_harvests_since_training(), 0)
        entry = ChangeLog.objects.get(action='model.auto_trained')
        self.assertEqual((entry.actor, entry.actor_role), (None, 'system'))

    def test_never_trains_the_first_model_on_its_own(self):
        self.add_harvests(history.AUTO_RETRAIN_EVERY)
        self.assertIsNone(history.retrain_if_due())
        self.assertFalse(YieldPredictionModel.objects.exists())

    def test_a_worse_model_is_kept_but_not_used(self):
        current = self.train()
        YieldPredictionModel.objects.filter(pk=current.pk).update(mae=0.0001)   # hard to beat
        self.add_harvests(history.AUTO_RETRAIN_EVERY)
        new = history.retrain_if_due()
        current.refresh_from_db()
        self.assertTrue(current.is_active)
        self.assertFalse(new.is_active)
        self.assertIn('Not used', new.notes)
        self.assertIn('kept the current model', ChangeLog.objects.get().summary)
        # The rejected training still counts: no retrain again until 5 more harvests
        self.assertIsNone(history.retrain_if_due())

    def test_the_fifth_harvest_from_the_app_starts_the_retrain(self):
        self.train()
        self.add_harvests(history.AUTO_RETRAIN_EVERY - 1)
        with mock.patch.object(history, '_in_background', lambda fn: fn()), \
                self.captureOnCommitCallbacks(execute=True):
            res = self.client.post(f'/api/progress/cycles/{self.cycle.id}/yield/', {
                'harvest_date': '2026-09-25', 'area_harvested_ha': 1.0,
                'gross_yield_kg': 5200, 'net_yield_kg': 5200}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(YieldPredictionModel.objects.count(), 2)

    def test_a_failed_retrain_does_not_break_anything(self):
        self.train()
        self.add_harvests(history.AUTO_RETRAIN_EVERY)
        with mock.patch.object(history, 'train_all_models', side_effect=ValueError('bad data')), \
                self.assertLogs('apps.predictions.history', 'ERROR'):
            self.assertIsNone(history.retrain_if_due())
        self.assertEqual(YieldPredictionModel.objects.count(), 1)
