from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.farms.models import Farm
from apps.guides.models import GuideStep, PlantingGuide
from apps.guides.tests import make_variety
from apps.progress.models import FarmCycle, ProgressLog, YieldRecord
from apps.varieties.models import GrowthStage

from .season_board import HARVEST_GRACE_DAYS, LATE_DAYS

STAGES = [(1, 'Germination & Seedling', 0), (2, 'Seedling Stage', 7), (3, 'Tillering', 21),
          (4, 'Stem Elongation', 42), (5, 'Booting', 60), (6, 'Heading / Flowering', 75),
          (7, 'Grain Filling', 85), (8, 'Ripening / Maturity', 100), (9, 'Harvesting', 113),
          (10, 'Post-Harvest', 125)]


class SeasonBoardTests(TestCase):
    """The admin's season board: crops per stage, and the farms that need attention."""

    def setUp(self):
        for no, name, start in STAGES:
            GrowthStage.objects.create(stage_no=no, bbch_min=0, bbch_max=0, name=name, days_min_paddy=start,
                                       days_max_paddy=start + 10, days_min_upland=start, days_max_upland=start + 10,
                                       what_to_do='', water_management='')
        self.today = timezone.localdate()
        self.variety = make_variety(maturity_days=113)
        self.grower = User.objects.create_user(username='grower', password='pass12345', first_name='Juan')
        self.staff = User.objects.create_user(username='validator', password='pass12345', is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def crop(self, name, sown_days_ago, **farm):
        f = Farm.objects.create(user=self.grower, name=name, barangay='Nanyo', latitude=7.3, longitude=125.68,
                                area_hectares=1, **farm)
        sown = self.today - timedelta(days=sown_days_ago)
        return FarmCycle.objects.create(farm=f, variety=self.variety, season='wet', year=2026, planting_date=sown,
                                        expected_harvest_date=sown + timedelta(days=113))

    def board(self):
        res = self.client.get(reverse('admin-season'))
        self.assertEqual(res.status_code, 200, res.content)
        return res.data

    def test_counts_crops_at_each_of_the_ten_stages(self):
        self.crop('Young', 2)
        self.crop('Tillering', 25)
        data = self.board()
        self.assertEqual([s['stage_no'] for s in data['stages']], list(range(1, 11)))
        counts = {s['stage_no']: s['count'] for s in data['stages']}
        self.assertEqual(counts[1], 1)
        self.assertEqual(counts[3], 1)
        self.assertEqual(data['active_crops'], 2)

    def test_a_step_late_by_three_days_needs_attention_but_not_on_time(self):
        late = self.crop('Late', 10)
        on_time = self.crop('OnTime', 10)
        for c, days in ((late, LATE_DAYS), (on_time, LATE_DAYS - 1)):
            g = PlantingGuide.objects.create(farm=c.farm, variety=self.variety, season='Wet Season 2026',
                                             start_date=c.planting_date)
            GuideStep.objects.create(guide=g, step_no=1, title='Level the field', description='',
                                     scheduled_date=self.today - timedelta(days=days))
        items = self.board()['attention']['late_steps']['items']
        self.assertEqual([i['farm'] for i in items], ['Late'])
        self.assertEqual(items[0]['days_late'], LATE_DAYS)
        self.assertEqual(items[0]['farmer'], 'Juan')

    def test_problems_this_week_only_worst_first(self):
        c = self.crop('Pests', 30)
        ProgressLog.objects.create(farm_cycle=c, log_date=self.today, observation='a few', issue_type='pest', severity='low')
        ProgressLog.objects.create(farm_cycle=c, log_date=self.today, observation='bad', issue_type='disease', severity='high')
        ProgressLog.objects.create(farm_cycle=c, log_date=self.today - timedelta(days=9), observation='old',
                                   issue_type='pest', severity='high')
        ProgressLog.objects.create(farm_cycle=c, log_date=self.today, observation='just a note')
        problems = self.board()['attention']['problems']
        self.assertEqual(problems['count'], 2)
        self.assertEqual([p['severity'] for p in problems['items']], ['high', 'low'])

    def test_flagged_pins_and_overdue_harvests(self):
        self.crop('OnRoad', 5, location_flag='built_up', location_confirmed=True)
        self.crop('GoodPin', 5, location_flag='ok')
        self.crop('NotChecked', 5, location_flag='unchecked')
        overdue = self.crop('Overdue', 113 + HARVEST_GRACE_DAYS)
        done = self.crop('Harvested', 113 + HARVEST_GRACE_DAYS)
        YieldRecord.objects.create(farm_cycle=done, harvest_date=self.today, area_harvested_ha=1,
                                   gross_yield_kg=5000, net_yield_kg=5000)
        att = self.board()['attention']
        self.assertEqual([(p['farm'], p['kept']) for p in att['flagged_pins']['items']], [('OnRoad', True)])
        self.assertEqual([h['farm'] for h in att['harvest_overdue']['items']], [overdue.farm.name])

    def test_farmers_cannot_see_it(self):
        self.client.force_authenticate(self.grower)
        self.assertEqual(self.client.get(reverse('admin-season')).status_code, 403)
