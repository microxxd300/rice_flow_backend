from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.environmental.models import EnvironmentalScan
from apps.farms.models import Farm
from apps.progress.models import FarmCycle
from apps.varieties.models import RiceVariety

from .models import Recommendation

TODAY = date(2026, 11, 20)   # dry season


def utc(*parts):
    return datetime(*parts, tzinfo=dt_timezone.utc)


@patch('apps.recommendations.views.timezone.localdate', lambda *a: TODAY if not a else a[0].date())
class ReuseRecommendationTests(TestCase):
    """The next crop starts from the saved top 3 unless the season has changed."""

    def setUp(self):
        self.user = User.objects.create_user(username='grower', password='pass12345')
        self.farm = Farm.objects.create(user=self.user, name='Farm', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                        area_hectares=1)
        self.scan = EnvironmentalScan.objects.create(farm=self.farm)
        self.rec = Recommendation.objects.create(farm=self.farm, scan=self.scan)
        variety = RiceVariety.objects.create(variety_id='T14', nsic_code='NSIC T14', common_name='Tubigan 14',
                                             ecosystem='rainfed_lowland', season='both', maturity_days=110,
                                             avg_yield_t_ha=5.0, max_yield_t_ha=8.0)
        self.rec.results.create(variety=variety, rank=1, rsi_score=90, suitability_class='S1')
        self.set_scan_date(utc(2026, 11, 9))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse('reuse-recommendation', args=[self.farm.id])

    def set_scan_date(self, when):
        EnvironmentalScan.objects.filter(pk=self.scan.pk).update(scanned_at=when)
        Farm.objects.filter(pk=self.farm.pk).update(updated_at=utc(2026, 1, 1))

    def test_same_season_reuses_the_top_3_and_starts_the_crop(self):
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['recommendation']['id'], self.rec.id)
        self.assertEqual(res.data['scan']['id'], self.scan.id)
        self.assertEqual(Recommendation.objects.count(), 1)
        self.assertEqual(FarmCycle.objects.filter(farm=self.farm, status='active').count(), 1)

    def test_a_second_request_does_not_start_a_second_crop(self):
        self.client.post(self.url)
        self.client.post(self.url)
        self.assertEqual(FarmCycle.objects.filter(farm=self.farm).count(), 1)

    def test_a_changed_season_needs_a_new_scan(self):
        self.set_scan_date(utc(2026, 10, 20))   # wet season
        self.assertEqual(self.client.post(self.url).status_code, 409)
        self.assertFalse(FarmCycle.objects.filter(farm=self.farm).exists())

    def test_the_same_season_last_year_needs_a_new_scan(self):
        self.set_scan_date(utc(2025, 11, 20))
        self.assertEqual(self.client.post(self.url).status_code, 409)

    def test_a_farm_changed_after_the_scan_needs_a_new_scan(self):
        Farm.objects.filter(pk=self.farm.pk).update(updated_at=utc(2026, 11, 15))
        self.assertEqual(self.client.post(self.url).status_code, 409)

    def test_a_farm_with_no_recommendation_needs_a_scan(self):
        self.rec.delete()
        self.assertEqual(self.client.post(self.url).status_code, 409)

    def test_another_farmers_farm_is_not_found(self):
        other = User.objects.create_user(username='other', password='pass12345')
        client = APIClient()
        client.force_authenticate(other)
        self.assertEqual(client.post(self.url).status_code, 404)
