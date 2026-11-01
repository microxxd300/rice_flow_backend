from django.test import TestCase
from rest_framework.test import APIClient


class HealthEndpointTests(TestCase):
    def test_health_is_public_and_reports_database(self):
        r = APIClient().get('/api/health/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'ok')
        self.assertEqual(r.json()['database'], 'ok')
        self.assertIn('version', r.json())


class ProfileRoleTests(TestCase):
    def setUp(self):
        from apps.accounts.models import User
        self.user = User.objects.create_user(username='farmer', email='f@x.com', password='pass12345')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_user_cannot_grant_themselves_admin(self):
        r = self.client.patch('/api/auth/profile/', {'is_staff': True, 'is_superuser': True}, format='json')
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_user_can_still_edit_their_profile(self):
        r = self.client.patch('/api/auth/profile/', {'first_name': 'Juan'}, format='json')
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.user.first_name, 'Juan')

    def test_login_email_and_username_cannot_be_changed_here(self):
        r = self.client.patch('/api/auth/profile/', {'email': 'other@x.com', 'username': 'boss',
                                                     'barangay': 'Nanyo'}, format='json')
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 200)
        self.assertEqual((self.user.email, self.user.username), ('f@x.com', 'farmer'))
        self.assertEqual(self.user.barangay, 'Nanyo')


class AdminDeactivationTests(TestCase):
    """A farmer the admin website deactivates is locked out of the app at once."""

    def setUp(self):
        from apps.accounts.models import User
        self.admin = User.objects.create_user(username='agri', email='agri@georice.app', password='pass12345',
                                              is_staff=True, is_superuser=True)
        self.farmer = User.objects.create_user(username='juan', email='juan@georice.app', password='Palay-2026!')
        self.app = APIClient()
        r = self.app.post('/api/auth/login/', {'email': 'juan@georice.app', 'password': 'Palay-2026!'}, format='json')
        self.app.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access_token']}")

    def test_deactivated_farmer_loses_the_open_session_and_cannot_log_in(self):
        self.assertEqual(self.app.get('/api/farms/').status_code, 200)

        admin = APIClient()
        admin.force_authenticate(self.admin)
        r = admin.patch('/api/auth/users/', {'id': self.farmer.id, 'is_active': False}, format='json')
        self.assertEqual(r.status_code, 200)

        self.assertEqual(self.app.get('/api/farms/').status_code, 401)   # the token in the app stops working
        r = APIClient().post('/api/auth/login/', {'email': 'juan@georice.app', 'password': 'Palay-2026!'},
                             format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('account is disabled', r.json()['non_field_errors'][0])   # shown as-is by the app

    def test_a_wrong_password_on_a_disabled_account_says_nothing_about_it(self):
        self.farmer.is_active = False
        self.farmer.save()
        r = APIClient().post('/api/auth/login/', {'email': 'juan@georice.app', 'password': 'wrong-pass'}, format='json')
        self.assertEqual(r.json()['non_field_errors'], ['Invalid credentials.'])


class ValidatorRoleTests(TestCase):
    """The validator (is_staff) reads the admin data and corrects varieties; everything
    that changes accounts, deletes records or changes the RSI model is admin (superuser) only."""

    @classmethod
    def setUpTestData(cls):
        from apps.accounts.models import User
        from apps.farms.models import Farm
        from apps.progress.models import FarmCycle
        from apps.varieties.models import RiceVariety
        cls.admin = User.objects.create_user(username='dev', email='dev@georice.app', password='pass12345',
                                             is_staff=True, is_superuser=True)
        cls.validator = User.objects.create_user(username='engr', email='engr@georice.app', password='pass12345',
                                                 is_staff=True)
        cls.farmer = User.objects.create_user(username='juan', email='juan@georice.app', password='pass12345')
        cls.farm = Farm.objects.create(user=cls.farmer, name='Juan farm', barangay='Gredu',
                                       latitude=7.3, longitude=125.68, area_hectares=1)
        cls.cycle = FarmCycle.objects.create(farm=cls.farm, season='wet', year=2026, planting_date='2026-06-01')
        cls.variety = RiceVariety.objects.create(variety_id='T1', nsic_code='Rc222', common_name='Tubigan 18',
                                                 ecosystem='irrigated_lowland', season='both', maturity_days=113,
                                                 avg_yield_t_ha=5.2, max_yield_t_ha=8.0)

    def as_user(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_validator_reads_the_admin_pages(self):
        v = self.as_user(self.validator)
        for url in ('/api/auth/admin-stats/', '/api/farms/all/', '/api/progress/admin/cycles/',
                    '/api/varieties/', '/api/recommendations/rules/', '/api/predictions/models/'):
            self.assertEqual(v.get(url).status_code, 200, url)

    def test_validator_cannot_do_admin_only_actions(self):
        v = self.as_user(self.validator)
        denied = [
            ('get',    '/api/auth/users/'),
            ('patch',  '/api/auth/users/'),
            ('delete', f'/api/auth/users/{self.farmer.id}/'),
            ('delete', f'/api/farms/admin/{self.farm.id}/'),
            ('post',   '/api/farms/cleanup/'),
            ('delete', f'/api/progress/admin/cycles/{self.cycle.id}/'),
            ('post',   '/api/varieties/'),
            ('delete', f'/api/varieties/{self.variety.id}/'),
            ('post',   '/api/varieties/import-csv/'),
            ('put',    '/api/recommendations/rules/'),
            ('post',   '/api/recommendations/train/'),
            ('post',   '/api/predictions/train/'),
            ('get',    '/api/ai/knowledge/'),
        ]
        for method, url in denied:
            self.assertEqual(getattr(v, method)(url, {}, format='json').status_code, 403, f'{method} {url}')
        self.assertTrue(self.farm.__class__.objects.filter(pk=self.farm.pk).exists())
        self.variety.refresh_from_db()
        self.assertTrue(self.variety.is_active)

    def test_validator_can_correct_a_variety_but_not_deactivate_it(self):
        r = self.as_user(self.validator).patch(f'/api/varieties/{self.variety.id}/',
                                               {'avg_yield_t_ha': 5.4, 'is_active': False}, format='json')
        self.assertEqual(r.status_code, 200)
        self.variety.refresh_from_db()
        self.assertEqual(self.variety.avg_yield_t_ha, 5.4)
        self.assertTrue(self.variety.is_active)

    def test_farmer_emails_are_hidden_from_the_validator(self):
        v, a = self.as_user(self.validator), self.as_user(self.admin)
        self.assertIsNone(v.get('/api/farms/all/').json()[0]['owner_email'])
        self.assertIsNone(v.get('/api/progress/admin/cycles/').json()[0]['owner_email'])
        self.assertEqual(a.get('/api/farms/all/').json()[0]['owner_email'], 'juan@georice.app')
        self.assertEqual(a.get('/api/progress/admin/cycles/').json()[0]['owner_email'], 'juan@georice.app')

    def test_admin_keeps_full_access(self):
        a = self.as_user(self.admin)
        self.assertEqual(a.get('/api/auth/users/').status_code, 200)
        self.assertEqual(a.delete(f'/api/progress/admin/cycles/{self.cycle.id}/').status_code, 200)
        self.assertEqual(a.delete(f'/api/farms/admin/{self.farm.id}/').status_code, 204)
