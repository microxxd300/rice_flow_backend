from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.environmental.models import EnvironmentalScan
from apps.farms.models import Farm
from apps.progress.stages import STEP_STAGE
from apps.recommendations.models import Recommendation
from apps.varieties.models import RiceVariety

from . import direct_seeded, palaycheck, sowing
from .models import PlantingGuide

UPLAND, RAINFED, IRRIGATED = 'upland', 'rainfed_lowland', 'irrigated_lowland'


class PlanTests(SimpleTestCase):
    def test_every_step_has_text_in_all_languages_and_a_source(self):
        for ecosystem in (UPLAND, RAINFED):
            for step in palaycheck.plan(115, ecosystem):
                for language in palaycheck.LANGUAGES:
                    self.assertTrue(palaycheck.text(step['key'], language)['instruction'], step['key'])
                self.assertTrue(palaycheck.reference_for(step['key']))
                self.assertTrue(palaycheck.reference_url_for(step['key']).startswith('https://'))

    def test_sources_open_our_viewer_at_the_cited_page(self):
        self.assertEqual(palaycheck.reference_url_for('up_pests'), 'https://riceflow.me/booklet.html?b=upland&pages=10-14')
        self.assertEqual(palaycheck.reference_url_for('rf_sow'), 'https://riceflow.me/booklet.html?b=mddst&pages=4,7')
        # Two booklets cited: the link opens the first
        self.assertEqual(palaycheck.reference_url_for('rf_seeds'), 'https://riceflow.me/booklet.html?b=mddst&pages=6')
        self.assertEqual(palaycheck.reference_url_for('rf_drain'), 'https://riceflow.me/booklet.html?b=mdds&pages=35')

    def test_direct_seeded_farms_sow_on_day_zero_without_transplanting(self):
        for ecosystem, sow in ((UPLAND, 'up_sow'), (RAINFED, 'rf_sow')):
            days = {s['key']: s['day'] for s in palaycheck.plan(115, ecosystem)}
            self.assertEqual(days[sow], 0)
            self.assertNotIn('transplant', days)
            self.assertNotIn('seedbed', days)

    def test_steps_are_in_day_order_and_end_with_harvest_and_storage(self):
        for ecosystem in (UPLAND, RAINFED):
            steps = palaycheck.plan(100, ecosystem)
            days = [s['day'] for s in steps]
            self.assertEqual(days, sorted(days))
            self.assertIn(steps[-2]['key'], direct_seeded.HARVEST_KEYS)
            self.assertEqual(steps[-2]['day'], 100)

    def test_irrigated_and_unknown_farm_types_keep_palaycheck(self):
        for ecosystem in (IRRIGATED, None, 'other'):
            keys = [s['key'] for s in palaycheck.plan(115, ecosystem)]
            self.assertIn('transplant', keys)

    def test_steps_after_sowing_have_a_growth_stage(self):
        for ecosystem in (UPLAND, RAINFED):
            for step in palaycheck.plan(115, ecosystem):
                if step['day'] >= 0:
                    self.assertIn(step['key'], STEP_STAGE)

    def test_no_herbicide_product_or_rate_reaches_the_farmer(self):
        for words in direct_seeded.TEXT.values():
            for parts in words.values():
                joined = ' '.join(parts).lower()
                for product in ('oxadiazon', 'ronstar', 'pendimethalin', 'herbadox', '2,4-d', 'glyphosate', 'butachlor'):
                    self.assertNotIn(product, joined)


class GuideForFarmTypeTests(TestCase):
    def make_guide(self, ecosystem):
        user = get_user_model().objects.create_user(username=f'grower-{ecosystem}', password='pass12345')
        farm = Farm.objects.create(user=user, name='Farm', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                   area_hectares=1, ecosystem=ecosystem)
        rec = Recommendation.objects.create(farm=farm, scan=EnvironmentalScan.objects.create(farm=farm))
        variety = RiceVariety.objects.create(variety_id=f'V{ecosystem[:2]}', nsic_code=f'NSIC {ecosystem[:2]}',
                                             common_name='Apo', ecosystem=ecosystem, season='both', maturity_days=119,
                                             avg_yield_t_ha=3.0, max_yield_t_ha=5.0)
        rec.results.create(variety=variety, rank=1, rsi_score=90, suitability_class='S1')
        client = APIClient()
        client.force_authenticate(user)
        return client.post(reverse('generate-guide', args=[rec.id]), {'language': 'en'}, format='json').data

    def test_an_upland_farm_gets_the_upland_booklet(self):
        guide = self.make_guide(UPLAND)
        keys = [s['key'] for s in guide['steps']]
        self.assertIn('up_sow', keys)
        self.assertNotIn('transplant', keys)
        self.assertIn('Upland', guide['reference'])
        self.assertIn('PalayCheck Upland', guide['steps'][0]['reference'])

    def test_a_rainfed_farm_gets_the_rainfed_booklets_without_keychecks(self):
        guide = self.make_guide(RAINFED)
        sow = next(s for s in guide['steps'] if s['key'] == 'rf_sow')
        self.assertIsNone(sow['keyCheck'])
        self.assertIn('MDDST', sow['reference'])

    def test_an_irrigated_farm_is_unchanged(self):
        guide = self.make_guide(IRRIGATED)
        self.assertIn('transplant', [s['key'] for s in guide['steps']])
        self.assertIn('PalayCheck System 2022', guide['reference'])

    def test_confirming_sowing_moves_a_direct_seeded_plan(self):
        data = self.make_guide(UPLAND)
        guide = PlantingGuide.objects.get(pk=data['id'])
        self.assertEqual(sowing.sowing_step(guide).template_key, 'up_sow')
        sown_on = timezone.localdate() - timedelta(days=2)
        sowing.confirm_sowing(guide, sown_on)
        guide.refresh_from_db()
        self.assertEqual(guide.start_date, sown_on)
        self.assertTrue(sowing.is_sown(guide))
