import io

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.varieties.models import RiceVariety


def variety(**over):
    return {'variety_id': 'V900', 'nsic_code': 'NSIC Rc900', 'common_name': 'Test Rice', 'ecosystem': 'upland',
            'season': 'Wet/Dry', 'maturity_days': 110, 'avg_yield_t_ha': 5.0, 'max_yield_t_ha': 7.0, 'grain_type': 'Long',
            'optimal_temp_min': 22, 'optimal_temp_max': 35, 'optimal_rainfall_min': 1200,
            'pagasa_climate_types': 'IV', **over}


class VarietyLimitTests(TestCase):
    def setUp(self):
        self.admin = APIClient()
        self.admin.force_authenticate(User.objects.create_superuser('boss', 'boss@example.com', 'pass12345'))

    def post(self, **over):
        return self.admin.post('/api/varieties/', variety(**over), format='json')

    def test_a_good_variety_is_saved(self):
        res = self.post(year_released=None, plant_height_cm=None, amylose_pct=None)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertIsNone(res.data['year_released'])

    def test_impossible_numbers_are_refused(self):
        for field, bad in (('maturity_days', 0), ('avg_yield_t_ha', 0), ('max_yield_t_ha', 30), ('max_yield_t_ha', 4),
                           ('optimal_temp_min', 40), ('optimal_rainfall_min', -1), ('plant_height_cm', 0),
                           ('amylose_pct', 120), ('year_released', 0)):
            res = self.post(**{field: bad})
            self.assertEqual(res.status_code, 400, (field, bad))
        self.assertFalse(RiceVariety.objects.exists())

    def test_an_edit_is_checked_against_the_saved_values(self):
        pk = self.post().data['id']
        url = f'/api/varieties/{pk}/'
        self.assertEqual(self.admin.patch(url, {'avg_yield_t_ha': 6.5}, format='json').status_code, 200)
        self.assertEqual(self.admin.patch(url, {'avg_yield_t_ha': 7.5}, format='json').status_code, 400)  # above the max

    def test_an_old_bad_value_does_not_block_another_edit(self):
        pk = self.post().data['id']
        RiceVariety.objects.filter(pk=pk).update(year_released=0)
        url = f'/api/varieties/{pk}/'
        self.assertEqual(self.admin.patch(url, {'avg_yield_t_ha': 5.5, 'year_released': 0}, format='json').status_code, 200)
        self.assertEqual(self.admin.patch(url, {'year_released': 5}, format='json').status_code, 400)

    def test_a_second_variety_cannot_take_an_nsic_code(self):
        self.post()
        res = self.post(variety_id='V901', nsic_code='nsic rc900')
        self.assertEqual(res.status_code, 400)
        self.assertIn('nsic_code', res.data)

    def test_keeping_its_own_nsic_code_is_fine(self):
        created = self.post().data
        res = self.admin.patch(f"/api/varieties/{created['id']}/", {'nsic_code': created['nsic_code']}, format='json')
        self.assertEqual(res.status_code, 200, res.content)

    def csv(self, text):
        f = io.BytesIO(text.encode())
        f.name = 'v.csv'
        return self.admin.post('/api/varieties/import-csv/', {'file': f}, format='multipart')

    def test_csv_without_a_maximum_yield_uses_the_average(self):
        head = 'nsic_code,common_name,ecosystem,maturity_days,avg_yield_t_ha,max_yield_t_ha\n'
        res = self.csv(head + 'NSIC Rc901,New,upland,110,5.0,\n')
        self.assertEqual((res.data['created'], res.data['skipped']), (1, 0), res.data)
        self.assertEqual(RiceVariety.objects.get(nsic_code='NSIC Rc901').max_yield_t_ha, 5.0)

    def test_csv_refuses_impossible_numbers_with_the_line(self):
        res = self.csv('nsic_code,common_name,ecosystem,maturity_days,avg_yield_t_ha\nNSIC Rc902,New,upland,0,5.0\n')
        self.assertEqual(res.data['skipped'], 1)
        self.assertEqual(res.data['errors'][0]['line'], 2)
