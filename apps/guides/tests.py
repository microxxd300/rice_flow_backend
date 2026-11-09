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
from apps.varieties.models import RiceVariety

from . import palaycheck
from .models import GuideStep, PlantingGuide
from .views import season_label


def make_variety(maturity_days=110, code='T14', name='Tubigan 14'):
    return RiceVariety.objects.create(variety_id=code, nsic_code=f'NSIC {code}', common_name=name,
                                      ecosystem='rainfed_lowland', season='both', maturity_days=maturity_days,
                                      avg_yield_t_ha=5.0, max_yield_t_ha=8.0)


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

    def test_generate_defaults_to_the_top_ranked_variety(self):
        res = self.client.post(self.generate_url, {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['variety'], self.top.id)

    def test_generate_uses_the_picked_variety(self):
        res = self.client.post(self.generate_url, {'variety': self.second.id}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['variety'], self.second.id)

    def test_generate_without_a_variety_keeps_the_earlier_pick(self):
        self.client.post(self.generate_url, {'variety': self.second.id}, format='json')
        res = self.client.post(self.generate_url, {}, format='json')
        self.assertEqual(res.data['variety'], self.second.id)

    def test_generate_rejects_a_variety_outside_the_recommendation(self):
        res = self.client.post(self.generate_url, {'variety': self.other.id}, format='json')
        self.assertEqual(res.status_code, 400)

    def start_cycle(self):
        # What a scan does (recommendations._auto_start_cycle): the top-ranked variety, today
        return FarmCycle.objects.create(farm=self.rec.farm, variety=self.top, season='wet', year=2026,
                                        planting_date=timezone.now().date())

    def test_the_scans_crop_cycle_follows_the_pick(self):
        cycle = self.start_cycle()
        self.client.post(self.generate_url, {'variety': self.second.id}, format='json')
        cycle.refresh_from_db()
        self.assertEqual(cycle.variety, self.second)
        self.assertEqual(cycle.expected_harvest_date, cycle.planting_date + timedelta(days=110))

    def test_a_cycle_with_field_work_keeps_its_variety(self):
        cycle = self.start_cycle()
        ProgressLog.objects.create(farm_cycle=cycle, log_date=timezone.now().date(), observation='Sown')
        self.client.post(self.generate_url, {'variety': self.second.id}, format='json')
        cycle.refresh_from_db()
        self.assertEqual(cycle.variety, self.top)

    def test_the_scans_crop_cycle_is_sown_on_the_guides_sowing_day(self):
        cycle = self.start_cycle()
        res = self.client.post(self.generate_url, {}, format='json')
        cycle.refresh_from_db()
        sowing = timezone.now().date() + timedelta(days=palaycheck.PREP_DAYS)
        self.assertEqual(res.data['start_date'], sowing.isoformat())
        self.assertEqual(cycle.planting_date, sowing)
        self.assertEqual(cycle.expected_harvest_date, sowing + timedelta(days=110))
        self.assertEqual((cycle.season, cycle.year), ('wet' if 5 <= sowing.month <= 10 else 'dry', sowing.year))

    def test_a_new_guide_for_a_crop_being_worked_uses_its_sowing_day(self):
        cycle = self.start_cycle()
        sown = timezone.now().date() - timedelta(days=20)
        cycle.planting_date = sown
        cycle.save()
        ProgressLog.objects.create(farm_cycle=cycle, log_date=timezone.now().date(), observation='Sown')
        res = self.client.post(self.generate_url, {}, format='json')
        cycle.refresh_from_db()
        self.assertEqual(res.data['start_date'], sown.isoformat())
        self.assertEqual(cycle.planting_date, sown)


class PalayCheckPlanTests(TestCase):
    """The guide is PalayCheck 2022, timed from sowing for the variety's maturity."""

    def test_steps_follow_the_book_timing(self):
        days = {st['key']: st['day'] for st in palaycheck.plan(113)}
        self.assertEqual(days['seedbed'], 0)
        self.assertEqual(days['transplant'], palaycheck.SEEDLING_AGE_DAYS)        # 18-21-day seedlings
        self.assertTrue(days['transplant'] <= days['fertilizer1'] <= days['transplant'] + 14)   # 0-14 DAT
        self.assertEqual(days['fertilizerpi'], 113 - 60 - 6)                      # 5-7 days before PI
        self.assertEqual(days['harvest'], 113)
        self.assertEqual(days['drystore'], 114)
        self.assertEqual(list(days), [st['key'] for st in sorted(palaycheck.plan(113), key=lambda s: s['day'])])

    def test_the_mid_tillering_split_is_only_for_long_varieties(self):
        self.assertIn('fertilizer2', [st['key'] for st in palaycheck.plan(120)])
        self.assertNotIn('fertilizer2', [st['key'] for st in palaycheck.plan(105)])

    def test_every_step_is_worded_in_every_language(self):
        for key, *_ in palaycheck.STEPS:
            for lang in palaycheck.LANGUAGES:
                t = palaycheck.text(key, lang)
                self.assertTrue(t['title'] and t['instruction'] and t['explanation'], (key, lang))


class PalayCheckGuideTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='grower', password='pass12345')
        self.farm = Farm.objects.create(user=self.user, name='Farm', barangay='Nanyo', latitude=7.3,
                                        longitude=125.68, area_hectares=1)
        self.rec = Recommendation.objects.create(farm=self.farm, scan=EnvironmentalScan.objects.create(farm=self.farm))
        self.variety = make_variety(maturity_days=113)
        self.rec.results.create(variety=self.variety, rank=1, rsi_score=95, suitability_class='S1')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse('generate-guide', args=[self.rec.id])

    def generate(self, language='en', **extra):
        return self.client.post(self.url, {'language': language, **extra}, format='json').data

    def test_the_guide_is_palaycheck_with_page_references(self):
        g = self.generate()
        self.assertEqual(g['source'], 'PALAYCHECK')
        first = g['steps'][0]
        self.assertEqual(first['key'], 'seeds')
        self.assertEqual(first['keyCheck'], 1)
        self.assertEqual(first['reference'], 'PalayCheck 2022, pp. 14-15')
        self.assertEqual(first['referenceUrl'], 'https://riceflow.me/booklet.html?b=palaycheck&pages=14-15')
        self.assertTrue(first['explanation'])
        self.assertEqual(self.generate()['source'], 'SAVED')                       # built once

    def test_the_season_is_named_from_the_sowing_day(self):
        from datetime import date
        self.assertEqual(season_label(date(2026, 7, 1)), 'Wet Season 2026')
        self.assertEqual(season_label(date(2026, 11, 14)), 'Dry Season 2026-27')
        self.assertEqual(season_label(date(2027, 2, 1)), 'Dry Season 2026-27')
        sowing = timezone.now().date() + timedelta(days=palaycheck.PREP_DAYS)
        self.assertEqual(self.generate()['season'], season_label(sowing))

    def test_the_next_crop_of_the_variety_gets_a_new_guide(self):
        first = self.generate()
        GuideStep.objects.filter(guide_id=first['id']).update(is_completed=True)   # crop finished
        second = self.generate()
        self.assertNotEqual(second['id'], first['id'])
        self.assertFalse(any(s['is_completed'] for s in second['steps']))
        self.assertEqual(self.generate()['id'], second['id'])                       # then kept

    def test_a_crop_harvested_with_steps_unlogged_does_not_pass_its_guide_on(self):
        first = self.generate()
        guide = PlantingGuide.objects.get(pk=first['id'])
        GuideStep.objects.filter(pk=first['steps'][0]['id']).update(is_completed=True)
        made = timezone.now() - timedelta(days=20)
        PlantingGuide.objects.filter(pk=guide.pk).update(created_at=made)
        FarmCycle.objects.create(farm=guide.farm, variety=guide.variety, season='wet', year=2026,
                                 planting_date=made.date(), status='completed',
                                 actual_harvest_date=timezone.localdate())
        second = self.generate()
        self.assertNotEqual(second['id'], first['id'])
        self.assertFalse(any(s['is_completed'] for s in second['steps']))
        self.assertEqual(self.generate()['id'], second['id'])                       # then kept

    def test_an_old_wet_season_guide_is_kept_and_named_by_its_dates(self):
        guide_id = self.generate()['id']
        PlantingGuide.objects.filter(pk=guide_id).update(season='Wet Season')
        old_app = self.generate(season='Wet Season')            # what older app versions send
        self.assertEqual(old_app['id'], guide_id)
        self.assertNotEqual(old_app['season'], 'Wet Season')
        self.assertEqual(self.generate()['id'], guide_id)
        self.assertEqual(PlantingGuide.objects.filter(farm=self.farm).count(), 1)

    def test_a_new_guide_starts_with_seed_preparation_today(self):
        self.generate()
        first = GuideStep.objects.order_by('days_after_planting').first()
        self.assertEqual(first.scheduled_date, timezone.now().date())

    def test_a_language_switch_rewords_the_same_steps_and_keeps_check_offs(self):
        en = self.generate('en')
        GuideStep.objects.filter(pk=en['steps'][0]['id']).update(is_completed=True)
        fil = self.generate('fil')
        self.assertEqual([s['id'] for s in fil['steps']], [s['id'] for s in en['steps']])
        self.assertTrue(fil['steps'][0]['is_completed'])
        self.assertNotEqual(fil['steps'][0]['title'], en['steps'][0]['title'])
        self.assertEqual(fil['source'], 'SAVED')

    def test_a_guide_from_before_palaycheck_is_rebuilt(self):
        old = PlantingGuide.objects.create(farm=self.farm, variety=self.variety, season='Wet Season',
                                           start_date=timezone.now().date())
        GuideStep.objects.create(guide=old, step_no=1, title='Gemini step', description='...', category='planting')
        g = self.generate()
        self.assertEqual(g['source'], 'PALAYCHECK')
        self.assertFalse(GuideStep.objects.filter(title='Gemini step').exists())

    def test_logging_a_step_marks_it_done(self):
        step_id = self.generate()['steps'][0]['id']
        cycle = FarmCycle.objects.create(farm=self.farm, variety=self.variety, season='wet', year=2026,
                                         planting_date=timezone.now().date())
        r = self.client.post('/api/progress/logs/', {'farm_cycle': cycle.id, 'log_date': str(timezone.now().date()),
                                                     'observation': 'Bought certified seeds', 'guide_step': step_id},
                             format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(GuideStep.objects.get(pk=step_id).is_completed)

    def test_a_step_from_another_farm_cannot_be_logged(self):
        step_id = self.generate()['steps'][0]['id']
        other = Farm.objects.create(user=self.user, name='Other', barangay='Nanyo', latitude=7.3,
                                    longitude=125.68, area_hectares=1)
        cycle = FarmCycle.objects.create(farm=other, season='wet', year=2026, planting_date=timezone.now().date())
        r = self.client.post('/api/progress/logs/', {'farm_cycle': cycle.id, 'log_date': str(timezone.now().date()),
                                                     'observation': 'x', 'guide_step': step_id}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(GuideStep.objects.get(pk=step_id).is_completed)
