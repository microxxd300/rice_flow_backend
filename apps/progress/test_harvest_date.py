from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.farms.models import Farm
from apps.farms.serializers import FarmSerializer
from apps.progress.models import FarmCycle, YieldRecord


class HarvestDateTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='me', password='pass12345')
        farm = Farm.objects.create(user=user, name='Farm', barangay='Gredu', latitude=7.3, longitude=125.68,
                                   area_hectares=1)
        self.cycle = FarmCycle.objects.create(farm=farm, season='dry', year=2026, planting_date='2026-11-19')
        self.client = APIClient()
        self.client.force_authenticate(user)
        self.url = f'/api/progress/cycles/{self.cycle.id}/yield/'

    def post(self, day):
        return self.client.post(self.url, {'harvest_date': day, 'area_harvested_ha': 1, 'gross_yield_kg': 100,
                                           'net_yield_kg': 90}, format='json')

    def test_harvest_before_sowing_is_refused(self):
        r = self.post('2026-11-09')
        self.assertEqual(r.status_code, 400)
        self.assertIn('harvest_date', r.json())
        self.assertFalse(YieldRecord.objects.exists())

    def test_harvest_on_the_sowing_day_is_refused(self):
        self.assertEqual(self.post('2026-11-19').status_code, 400)

    def test_harvest_after_sowing_is_saved(self):
        self.assertEqual(self.post('2027-03-05').status_code, 201)

    def test_edit_cannot_move_a_harvest_before_sowing(self):
        self.post('2027-03-05')
        r = self.client.patch(self.url, {'harvest_date': '2026-11-01'}, format='json')
        self.assertEqual(r.status_code, 400)


class ImpossibleYieldTests(TestCase):
    def test_impossible_yield_is_refused_but_a_high_one_is_kept(self):
        user = User.objects.create_user(username='me', password='pass12345')
        farm = Farm.objects.create(user=user, name='Farm', barangay='Gredu', latitude=7.3, longitude=125.68,
                                   area_hectares=1)
        cycle = FarmCycle.objects.create(farm=farm, season='wet', year=2026, planting_date='2026-06-01')
        client = APIClient()
        client.force_authenticate(user)
        url = f'/api/progress/cycles/{cycle.id}/yield/'
        body = {'harvest_date': '2026-10-01', 'area_harvested_ha': 1.5, 'gross_yield_kg': 101000}
        r = client.post(url, {**body, 'net_yield_kg': 101000}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('net_yield_kg', r.json())
        self.assertEqual(client.post(url, {**body, 'net_yield_kg': 22500}, format='json').status_code, 201)   # 15 t/ha


class FarmSizeTests(TestCase):
    def errors(self, size):
        serializer = FarmSerializer(data={'area_hectares': size})
        serializer.is_valid()
        return serializer.errors.get('area_hectares')

    def test_zero_and_negative_sizes_are_refused(self):
        self.assertEqual(self.errors('0'), ['Farm size must be more than 0.'])
        self.assertEqual(self.errors('-2'), ['Farm size must be more than 0.'])

    def test_a_real_size_is_accepted(self):
        self.assertIsNone(self.errors('1.5'))
