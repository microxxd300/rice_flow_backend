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
