from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.farms.models import Farm
from apps.progress.models import FarmCycle, ProgressLog, YieldRecord


def make_farm(user):
    return Farm.objects.create(user=user, name=f'{user.username} farm', barangay='Gredu',
                               latitude=7.3, longitude=125.68, area_hectares=1)


def make_cycle(farm):
    return FarmCycle.objects.create(farm=farm, season='wet', year=2026, planting_date='2026-06-01')


class CrossUserWriteTests(TestCase):
    """A farmer must not be able to attach or move records onto another farmer's data."""

    @classmethod
    def setUpTestData(cls):
        cls.me = User.objects.create_user(username='me', password='pass12345')
        cls.other = User.objects.create_user(username='other', password='pass12345')
        cls.my_farm, cls.other_farm = make_farm(cls.me), make_farm(cls.other)
        cls.my_cycle, cls.other_cycle = make_cycle(cls.my_farm), make_cycle(cls.other_farm)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.me)

    def cycle_payload(self, farm):
        return {'farm': farm.id, 'season': 'wet', 'year': 2026, 'planting_date': '2026-06-01'}

    def log_payload(self, cycle):
        return {'farm_cycle': cycle.id, 'log_date': '2026-06-02', 'observation': 'ok'}

    def test_create_cycle_on_own_farm(self):
        # A farm without an active season (my_farm already has one)
        r = self.client.post('/api/progress/cycles/', self.cycle_payload(make_farm(self.me)), format='json')
        self.assertEqual(r.status_code, 201)

    def test_cannot_create_cycle_on_other_users_farm(self):
        r = self.client.post('/api/progress/cycles/', self.cycle_payload(self.other_farm), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('farm', r.json())
        self.assertEqual(FarmCycle.objects.filter(farm=self.other_farm).count(), 1)

    def test_cannot_move_own_cycle_to_other_users_farm(self):
        r = self.client.patch(f'/api/progress/cycles/{self.my_cycle.id}/',
                              {'farm': self.other_farm.id}, format='json')
        self.my_cycle.refresh_from_db()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.my_cycle.farm, self.my_farm)

    def test_create_log_on_own_cycle(self):
        r = self.client.post('/api/progress/logs/', self.log_payload(self.my_cycle), format='json')
        self.assertEqual(r.status_code, 201)

    def test_cannot_create_log_on_other_users_cycle(self):
        r = self.client.post('/api/progress/logs/', self.log_payload(self.other_cycle), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(ProgressLog.objects.filter(farm_cycle=self.other_cycle).exists())

    def test_cannot_move_yield_record_to_other_users_cycle(self):
        record = YieldRecord.objects.create(farm_cycle=self.my_cycle, harvest_date='2026-10-01', area_harvested_ha=1,
                                            gross_yield_kg=1000, net_yield_kg=900)
        r = self.client.patch(f'/api/progress/cycles/{self.my_cycle.id}/yield/',
                              {'farm_cycle': self.other_cycle.id}, format='json')
        record.refresh_from_db()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(record.farm_cycle, self.my_cycle)


class CycleDefaultsTests(TestCase):
    def test_new_cycle_gets_expected_harvest_and_first_stage(self):
        from apps.varieties.models import GrowthStage, RiceVariety
        user = User.objects.create_user(username='planter', password='pass12345')
        farm = make_farm(user)
        variety = RiceVariety.objects.create(variety_id='T1', nsic_code='Rc222', common_name='Tubigan 18',
                                             ecosystem='irrigated_lowland', season='both', maturity_days=113,
                                             avg_yield_t_ha=5.2, max_yield_t_ha=8.0)
        stage = GrowthStage.objects.create(stage_no=1, bbch_min=0, bbch_max=9, name='Land prep', days_min_paddy=0,
                                           days_max_paddy=14, days_min_upland=0, days_max_upland=14,
                                           what_to_do='-', water_management='-')
        client = APIClient()
        client.force_authenticate(user)
        r = client.post('/api/progress/cycles/', {'farm': farm.id, 'variety': variety.id, 'season': 'wet',
                                                  'year': 2026, 'planting_date': '2026-10-01'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['expected_harvest_date'], '2027-01-22')  # 1 Oct + 113 days
        self.assertEqual(r.json()['current_stage'], stage.id)
        self.assertEqual(r.json()['variety_name'], 'Tubigan 18')


class SeasonLifecycleTests(TestCase):
    """A farm has one active season at a time, and recording the harvest ends it."""

    def setUp(self):
        self.user = User.objects.create_user(username='grower', password='pass12345')
        self.farm = make_farm(self.user)
        self.cycle = make_cycle(self.farm)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def new_cycle(self):
        return self.client.post('/api/progress/cycles/', {'farm': self.farm.id, 'season': 'dry', 'year': 2027,
                                                          'planting_date': '2027-01-10'}, format='json')

    def harvest(self):
        return self.client.post(f'/api/progress/cycles/{self.cycle.id}/yield/',
                                {'harvest_date': '2026-10-01', 'area_harvested_ha': 1,
                                 'gross_yield_kg': 4500, 'net_yield_kg': 4200}, format='json')

    def test_second_active_cycle_is_refused(self):
        r = self.new_cycle()
        self.assertEqual(r.status_code, 400)
        self.assertIn('farm', r.json())
        self.assertEqual(FarmCycle.objects.filter(farm=self.farm, status='active').count(), 1)

    def test_harvest_completes_the_cycle(self):
        self.assertEqual(self.harvest().status_code, 201)
        self.cycle.refresh_from_db()
        self.assertEqual(self.cycle.status, 'completed')
        self.assertEqual(str(self.cycle.actual_harvest_date), '2026-10-01')

    def test_new_cycle_allowed_after_harvest(self):
        self.harvest()
        self.assertEqual(self.new_cycle().status_code, 201)

    def test_cannot_reactivate_cycle_while_another_is_active(self):
        self.harvest()
        self.new_cycle()
        r = self.client.patch(f'/api/progress/cycles/{self.cycle.id}/', {'status': 'active'}, format='json')
        self.assertEqual(r.status_code, 400)


class LogSeverityTests(TestCase):
    def test_severity_is_saved(self):
        user = User.objects.create_user(username='logger', password='pass12345')
        cycle = make_cycle(make_farm(user))
        client = APIClient()
        client.force_authenticate(user)
        r = client.post('/api/progress/logs/', {'farm_cycle': cycle.id, 'log_date': '2026-06-02', 'observation': 'Leaf folder',
                                                'issue_type': 'pest', 'severity': 'medium'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(ProgressLog.objects.get(pk=r.json()['id']).severity, 'medium')
