from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.environmental.models import EnvironmentalScan
from apps.farms.models import Farm
from apps.progress.models import FarmCycle
from apps.recommendations.models import Recommendation
from apps.varieties.models import RiceVariety

from . import views


def make_variety(maturity_days=110, code='T14', name='Tubigan 14'):
    return RiceVariety.objects.create(variety_id=code, nsic_code=f'NSIC {code}', common_name=name,
                                      ecosystem='rainfed_lowland', season='both', maturity_days=maturity_days,
                                      avg_yield_t_ha=5.0, max_yield_t_ha=8.0)


class SeasonTimelineTests(TestCase):
    """Guide steps follow one timeline: day 0 = sowing, harvest = the variety's maturity day."""

    def test_rules_give_harvest_drain_and_forecast_window(self):
        rules = views._season_rules(make_variety(110), current_day=4)
        self.assertIn('counts from SOWING', rules)
        self.assertIn('harvest is day 110', rules)
        self.assertIn('Never drain before or during heading', rules)
        self.assertIn('day 96 to 100', rules)          # drain 10-14 days before harvest
        self.assertIn('between day 4 and day 11', rules)

    def test_steps_after_harvest_are_pulled_back_to_harvest_day(self):
        steps = [{'daysAfterPlanting': 30}, {'daysAfterPlanting': 140}]
        fitted = views._fit_to_season(steps, make_variety(110))
        self.assertEqual([s['daysAfterPlanting'] for s in fitted], [30, 110])

    def test_fallback_template_uses_the_same_timeline(self):
        steps = {s['title']: s['daysAfterPlanting'] for s in views._fallback_steps('en', 110)}
        self.assertEqual(steps['Sowing'], 0)
        self.assertEqual(steps['Transplanting'], views.SEEDLING_AGE_DAYS)
        self.assertEqual(steps['Drain Before Harvest'], 98)
        self.assertEqual(steps['Harvesting'], 110)

    def test_current_day_comes_from_the_active_cycle(self):
        user = User.objects.create_user(username='grower', password='pass12345')
        farm = Farm.objects.create(user=user, name='Farm', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                   area_hectares=1)
        self.assertEqual(views._current_day(farm), 0)
        FarmCycle.objects.create(farm=farm, season='wet', year=2026,
                                 planting_date=timezone.now().date() - timedelta(days=12))
        self.assertEqual(views._current_day(farm), 12)


AI_STEP = {'title': 'Sowing', 'instruction': 'Sow the seeds.', 'category': 'planting', 'daysAfterPlanting': 0}


@patch.object(views, '_get_forecast', return_value=[])
class ChosenVarietyTests(TestCase):
    """The guide is built for the variety the farmer picked, not always the top-ranked one."""

    def setUp(self):
        user = User.objects.create_user(username='grower', password='pass12345')
        farm = Farm.objects.create(user=user, name='Farm', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                   area_hectares=1)
        self.rec = Recommendation.objects.create(farm=farm, scan=EnvironmentalScan.objects.create(farm=farm))
        self.top = make_variety(code='T14', name='Tubigan 14')
        self.second = make_variety(code='T18', name='Tubigan 18')
        for rank, variety in enumerate([self.top, self.second], start=1):
            self.rec.results.create(variety=variety, rank=rank, rsi_score=95, suitability_class='S1')
        self.other = make_variety(code='T7', name='Tubigan 7')
        self.client = APIClient()
        self.client.force_authenticate(user)
        self.generate_url = reverse('generate-guide', args=[self.rec.id])
        self.append_url = reverse('append-guide-step', args=[self.rec.id])

    @patch.object(views, '_generate_ai_steps', return_value=[AI_STEP])
    def test_generate_defaults_to_the_top_ranked_variety(self, _ai, _forecast):
        res = self.client.post(self.generate_url, {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['variety'], self.top.id)

    @patch.object(views, '_generate_ai_steps', return_value=[AI_STEP])
    def test_generate_uses_the_picked_variety(self, ai, _forecast):
        res = self.client.post(self.generate_url, {'variety': self.second.id}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['variety'], self.second.id)
        self.assertEqual(ai.call_args.args[0], self.second)

    @patch.object(views, '_generate_ai_steps', return_value=[AI_STEP])
    def test_generate_without_a_variety_keeps_the_earlier_pick(self, _ai, _forecast):
        self.client.post(self.generate_url, {'variety': self.second.id}, format='json')
        res = self.client.post(self.generate_url, {}, format='json')
        self.assertEqual(res.data['variety'], self.second.id)

    @patch.object(views, '_generate_ai_steps', return_value=[AI_STEP])
    def test_generate_rejects_a_variety_outside_the_recommendation(self, _ai, _forecast):
        res = self.client.post(self.generate_url, {'variety': self.other.id}, format='json')
        self.assertEqual(res.status_code, 400)

    @patch.object(views, '_generate_one_step', return_value=AI_STEP)
    def test_append_adds_the_step_to_the_picked_variety_guide(self, one_step, _forecast):
        res = self.client.post(self.append_url, {'category': 'planting', 'last_day': 0, 'variety': self.second.id},
                               format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(one_step.call_args.args[0], self.second)
        self.assertTrue(self.rec.farm.planting_guides.filter(variety=self.second).exists())
