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
