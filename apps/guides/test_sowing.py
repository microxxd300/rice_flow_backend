from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.environmental.models import EnvironmentalScan
from apps.farms.models import Farm
from apps.progress.models import FarmCycle, ProgressLog
from apps.recommendations.models import Recommendation

from apps.varieties.models import GrowthStage

from .models import GuideStep, PlantingGuide
from .sowing import NOT_YET_DAYS, season_label
from .tests import make_variety

# The seeded growth stages: (stage_no, name, first paddy day)
STAGES = [(1, 'Germination & Seedling', 0), (2, 'Seedling Stage', 7), (3, 'Tillering', 21),
          (4, 'Stem Elongation', 42), (5, 'Booting', 60), (6, 'Heading / Flowering', 75),
          (7, 'Grain Filling', 85), (8, 'Ripening / Maturity', 100), (9, 'Harvesting', 113),
          (10, 'Post-Harvest', 125)]


class SowingTests(TestCase):
    """The crop cycle follows the guide: the real sowing day moves the whole plan."""

    def setUp(self):
        for no, name, start in STAGES:
            GrowthStage.objects.create(stage_no=no, bbch_min=0, bbch_max=0, name=name, days_min_paddy=start,
                                       days_max_paddy=start + 10, days_min_upland=start, days_max_upland=start + 10,
                                       what_to_do='', water_management='')
        self.user = User.objects.create_user(username='grower', password='pass12345')
        self.farm = Farm.objects.create(user=self.user, name='Farm', barangay='Nanyo', latitude=7.3,
                                        longitude=125.68, area_hectares=1)
        self.rec = Recommendation.objects.create(farm=self.farm, scan=EnvironmentalScan.objects.create(farm=self.farm))
        self.variety = make_variety(maturity_days=113)
        self.rec.results.create(variety=self.variety, rank=1, rsi_score=95, suitability_class='S1')
        # What a scan does: a crop cycle for the top variety
        self.cycle = FarmCycle.objects.create(farm=self.farm, variety=self.variety, season='wet', year=2026,
                                              planting_date=timezone.localdate())
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.guide = self.client.post(reverse('generate-guide', args=[self.rec.id]), {}, format='json').data
        self.today = timezone.localdate()

    def answer(self, **body):
        return self.client.post(reverse('guide-sowing', args=[self.guide['id']]), body, format='json')

    def step(self, key):
        return GuideStep.objects.get(guide_id=self.guide['id'], template_key=key)

    def log(self, key, on):
        return self.client.post('/api/progress/logs/', {'farm_cycle': self.cycle.id, 'log_date': str(on),
                                                        'observation': key, 'guide_step': self.step(key).id},
                                format='json')

    def test_sown_on_a_day_moves_the_plan_and_the_cycle_to_it(self):
        sown = self.today - timedelta(days=3)
        res = self.answer(sown=True, date=str(sown))
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data['start_date'], sown.isoformat())
        self.assertEqual(res.data['season'], season_label(sown))          # renamed with the day
        self.assertEqual(self.step('transplant').scheduled_date, sown + timedelta(days=21))
        for key in ('seeds', 'plow', 'seedbed'):                      # up to sowing counts as done
            self.assertTrue(self.step(key).is_completed, key)
        self.assertFalse(self.step('transplant').is_completed)
        self.assertTrue(ProgressLog.objects.filter(guide_step=self.step('seedbed'), log_date=sown).exists())
        self.cycle.refresh_from_db()
        self.assertEqual(self.cycle.planting_date, sown)
        self.assertEqual(self.cycle.expected_harvest_date, sown + timedelta(days=113))

    def test_sown_with_no_date_means_today(self):
        self.assertEqual(self.answer(sown=True).data['start_date'], self.today.isoformat())

    def test_not_yet_moves_sowing_three_days_later(self):
        planned = PlantingGuide.objects.get(pk=self.guide['id']).start_date
        res = self.answer(sown=False)
        later = max(planned, self.today) + timedelta(days=NOT_YET_DAYS)
        self.assertEqual(res.data['start_date'], later.isoformat())
        self.assertFalse(self.step('seedbed').is_completed)
        self.cycle.refresh_from_db()
        self.assertEqual(self.cycle.planting_date, later)

    def test_bad_answers_are_refused(self):
        self.assertEqual(self.answer(sown=True, date=str(self.today + timedelta(days=1))).status_code, 400)
        self.assertEqual(self.answer(sown=True, date='12/11/2026').status_code, 400)
        self.assertEqual(self.answer(sown='maybe').status_code, 400)
        self.answer(sown=True)
        self.assertEqual(self.answer(sown=False).status_code, 400)       # already sown

    def test_another_farmers_guide_cannot_be_answered(self):
        other = APIClient()
        other.force_authenticate(User.objects.create_user(username='other', password='pass12345'))
        res = other.post(reverse('guide-sowing', args=[self.guide['id']]), {'sown': True}, format='json')
        self.assertEqual(res.status_code, 404)

    def test_logging_the_sowing_step_is_the_answer(self):
        sown = self.today - timedelta(days=2)
        self.assertEqual(self.log('seedbed', sown).status_code, 201)
        self.assertEqual(PlantingGuide.objects.get(pk=self.guide['id']).start_date, sown)
        self.assertTrue(self.step('seeds').is_completed)
        self.assertEqual(ProgressLog.objects.filter(guide_step=self.step('seedbed')).count(), 1)

    def test_a_later_step_logged_before_sowing_gives_an_estimate(self):
        res = self.log('transplant', self.today)
        self.assertEqual(res.data['sowing_estimate'], (self.today - timedelta(days=21)).isoformat())
        self.answer(sown=True)
        self.assertNotIn('sowing_estimate', self.log('replant', self.today).data)   # sown now

    def test_a_step_after_sowing_cannot_be_dated_before_the_sowing_day(self):
        self.answer(sown=True)                                  # sown today
        res = self.log('transplant', self.today - timedelta(days=3))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn('log_date', res.data)
        self.assertFalse(self.step('transplant').is_completed)
        self.assertEqual(self.log('transplant', self.today).status_code, 201)

    def test_a_past_date_is_fine_when_it_is_not_before_sowing(self):
        self.answer(sown=True, date=str(self.today - timedelta(days=10)))
        self.assertEqual(self.log('transplant', self.today - timedelta(days=3)).status_code, 201)

    def test_the_stage_follows_the_logged_steps_or_the_days(self):
        self.answer(sown=True)
        self.log('fertilizer1', self.today)                     # day 0, but tillering work is done
        cycle = self.client.get('/api/progress/cycles/').json()
        cycle = (cycle['results'] if isinstance(cycle, dict) else cycle)[0]
        self.assertEqual(cycle['stage']['name'], 'Tillering')

    def test_the_admin_cycle_list_follows_the_app_too(self):
        sown = self.today - timedelta(days=4)
        self.answer(sown=True, date=str(sown))
        self.log('fertilizer1', self.today)
        admin = APIClient()
        admin.force_authenticate(User.objects.create_user(username='admin', password='pass12345', is_staff=True))
        row = next(c for c in admin.get('/api/progress/admin/cycles/').json() if c['id'] == self.cycle.id)
        self.assertEqual((row['current_stage'], row['stage_no']), ('Tillering', 3))
        self.assertEqual(row['planting_date'], sown.isoformat())
        self.assertEqual(row['expected_harvest_date'], (sown + timedelta(days=113)).isoformat())

    def test_without_logs_the_stage_stays_with_the_guide_and_the_age_is_still_known(self):
        self.answer(sown=True, date=str(self.today - timedelta(days=50)))
        cycle = self.client.get('/api/progress/cycles/').json()
        cycle = (cycle['results'] if isinstance(cycle, dict) else cycle)[0]
        self.assertEqual(cycle['stage']['name'], 'Germination & Seedling')
        self.assertEqual(cycle['age_stage_no'], 4)     # the app still asks about the harvest by age
