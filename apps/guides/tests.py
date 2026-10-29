from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.farms.models import Farm
from apps.progress.models import FarmCycle
from apps.varieties.models import RiceVariety

from . import views


def make_variety(maturity_days=110):
    return RiceVariety.objects.create(variety_id='T14', nsic_code='NSIC Rc563', common_name='Tubigan 14',
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
