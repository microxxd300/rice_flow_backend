from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.farms.models import Farm
from apps.progress.models import FarmCycle
from apps.varieties.models import RiceVariety
from .models import ChangeLog, FarmerNotice


class ChangeLogTests(TestCase):
    """Every change made from the admin website lands in the change log with who made it."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='dev', email='dev@georice.app', password='pass12345',
                                             first_name='Kurt', is_staff=True, is_superuser=True)
        cls.validator = User.objects.create_user(username='engr', email='engr@georice.app', password='pass12345',
                                                 first_name='Engr', last_name='Cruz', is_staff=True)
        cls.farmer = User.objects.create_user(username='juan', email='juan@georice.app', password='pass12345',
                                              first_name='Juan')
        cls.variety = RiceVariety.objects.create(variety_id='T1', nsic_code='Rc222', common_name='Tubigan 18',
                                                 ecosystem='irrigated_lowland', season='both', maturity_days=113,
                                                 avg_yield_t_ha=5.2, max_yield_t_ha=8.0)

    def as_user(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_a_validator_variety_edit_records_who_and_the_old_and_new_values(self):
        self.as_user(self.validator).patch(f'/api/varieties/{self.variety.id}/', {'avg_yield_t_ha': 5.4},
                                           format='json')
        entry = ChangeLog.objects.get()
        self.assertEqual((entry.actor_name, entry.actor_role, entry.action),
                         ('Engr Cruz', 'validator', 'variety.updated'))
        self.assertEqual(entry.changes, {'avg_yield_t_ha': [5.2, 5.4]})
        self.assertEqual(entry.summary, 'edited the variety Tubigan 18 (Rc222) (avg yield t ha)')

    def test_an_edit_that_changes_nothing_is_not_logged(self):
        self.as_user(self.validator).patch(f'/api/varieties/{self.variety.id}/', {'avg_yield_t_ha': 5.2},
                                           format='json')
        self.assertFalse(ChangeLog.objects.exists())

    def test_admin_account_edits_are_logged_without_the_password(self):
        a = self.as_user(self.admin)
        a.patch(f'/api/auth/users/{self.farmer.id}/', {'barangay': 'Gredu', 'password': 'New-pass-2026'},
                format='json')
        entry = ChangeLog.objects.get()
        self.assertEqual(entry.action, 'user.updated')
        self.assertEqual(entry.changes['barangay'], ['', 'Gredu'])
        self.assertEqual(entry.changes['password'], ['', 'changed'])
        self.assertNotIn('New-pass-2026', str(entry.changes) + entry.summary)

    def test_rules_save_lists_the_changed_values(self):
        from apps.recommendations.models import SuitabilityRuleSet
        bands = {'s1': {'min': 5.5, 'max': 6.5}, 's2': {'min': 5.0, 'max': 7.0}, 's3': {'min': 4.5, 'max': 8.0}}
        ph   = {'key': 'soil_ph', 'label': 'Soil pH', 'type': 'range', 'weight': 0.4, **bands}
        temp = {'key': 'temp', 'label': 'Temperature', 'type': 'range', 'weight': 0.6, **bands}
        SuitabilityRuleSet.objects.update_or_create(pk=1, defaults={'payload': {'rules': [ph, temp]}})
        r = self.as_user(self.admin).put('/api/recommendations/rules/',
                                         {'payload': {'rules': [{**ph, 'weight': 0.5}, {**temp, 'weight': 0.5}]}},
                                         format='json')
        self.assertEqual(r.status_code, 200, r.content)
        entry = ChangeLog.objects.get()
        self.assertEqual(entry.action, 'rules.updated')
        self.assertEqual(entry.changes, {'Soil pH weight': [0.4, 0.5], 'Temperature weight': [0.6, 0.5]})

    def test_only_the_admin_reads_the_change_log(self):
        self.as_user(self.validator).patch(f'/api/varieties/{self.variety.id}/', {'avg_yield_t_ha': 5.4},
                                           format='json')
        self.assertEqual(self.as_user(self.validator).get('/api/activity/changes/').status_code, 403)
        rows = self.as_user(self.admin).get('/api/activity/changes/?role=validator').json()
        self.assertEqual([r['actor_role'] for r in rows], ['validator'])
        self.assertEqual(self.as_user(self.admin).get('/api/activity/changes/?role=admin').json(), [])


class FarmerNoticeTests(TestCase):
    """A farmer hears about admin changes to their own farm, cycle or planted variety."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='dev', password='pass12345', is_staff=True, is_superuser=True)
        cls.farmer = User.objects.create_user(username='juan', password='pass12345')
        cls.other = User.objects.create_user(username='pedro', password='pass12345')
        cls.variety = RiceVariety.objects.create(variety_id='T1', nsic_code='Rc222', common_name='Tubigan 18',
                                                 ecosystem='irrigated_lowland', season='both', maturity_days=113,
                                                 avg_yield_t_ha=5.2, max_yield_t_ha=8.0)

    def setUp(self):
        self.farm = Farm.objects.create(user=self.farmer, name='Juan farm', barangay='Gredu',
                                        latitude=7.3, longitude=125.68, area_hectares=1)
        self.cycle = FarmCycle.objects.create(farm=self.farm, season='wet', year=2026, planting_date='2026-06-01',
                                              variety=self.variety)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)

    def notices_for(self, user, query=''):
        client = APIClient()
        client.force_authenticate(user)
        return client.get(f'/api/activity/notices/{query}').json()

    def test_deleting_a_farm_tells_its_owner_only(self):
        self.admin_client.delete(f'/api/farms/admin/{self.farm.id}/')
        [notice] = self.notices_for(self.farmer)
        self.assertEqual(notice['kind'], 'farm_removed')
        self.assertEqual(notice['params'], {'farm': 'Juan farm'})
        self.assertEqual(self.notices_for(self.other), [])
        self.assertEqual(ChangeLog.objects.get().action, 'farm.deleted')

    def test_deleting_a_cycle_tells_its_owner(self):
        self.admin_client.delete(f'/api/progress/admin/cycles/{self.cycle.id}/')
        [notice] = self.notices_for(self.farmer)
        self.assertEqual(notice['kind'], 'cycle_removed')
        self.assertEqual(notice['params'], {'farm': 'Juan farm', 'season': 'wet', 'year': 2026})

    def test_variety_changes_reach_farmers_who_are_growing_it(self):
        self.admin_client.patch(f'/api/varieties/{self.variety.id}/', {'maturity_days': 115}, format='json')
        self.admin_client.delete(f'/api/varieties/{self.variety.id}/')
        kinds = [n['kind'] for n in self.notices_for(self.farmer)]
        self.assertEqual(kinds, ['variety_retired', 'variety_updated'])   # newest first
        self.assertEqual(self.notices_for(self.other), [])

    def test_a_finished_cycle_gets_no_variety_notice(self):
        self.cycle.status = 'completed'
        self.cycle.save()
        self.admin_client.patch(f'/api/varieties/{self.variety.id}/', {'maturity_days': 115}, format='json')
        self.assertEqual(self.notices_for(self.farmer), [])

    def test_after_returns_only_newer_notices_and_old_ones_expire(self):
        first = FarmerNotice.objects.create(user=self.farmer, kind='farm_removed', title='a', body='a')
        second = FarmerNotice.objects.create(user=self.farmer, kind='farm_removed', title='b', body='b')
        self.assertEqual([n['id'] for n in self.notices_for(self.farmer, f'?after={first.id}')], [second.id])
        FarmerNotice.objects.filter(pk=second.pk).update(created_at=timezone.now() - timedelta(days=31))
        self.assertEqual([n['id'] for n in self.notices_for(self.farmer)], [first.id])
