from unittest import mock

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User

REGISTER = {'email': 'juan@x.com', 'first_name': 'Juan', 'last_name': 'Cruz',
            'barangay': 'Gredu', 'municipality': 'Panabo City', 'province': 'Davao del Norte'}


class PasswordTests(TestCase):
    def setUp(self):
        cache.clear()  # login and register are rate limited
        self.client = APIClient()

    def register(self, password):
        return self.client.post('/api/auth/register/', {**REGISTER, 'password': password, 'password2': password},
                                format='json')

    def test_new_passwords_are_hashed_with_argon2(self):
        self.assertEqual(self.register('tanim-palay-2026').status_code, 201)
        self.assertTrue(User.objects.get(email='juan@x.com').password.startswith('argon2$'))

    def test_register_rejects_common_and_numeric_passwords(self):
        for weak in ('password123', '12345678901'):
            r = self.register(weak)
            self.assertEqual(r.status_code, 400, weak)
            self.assertIn('password', r.json())

    def test_old_pbkdf2_hash_still_works_and_is_upgraded_on_login(self):
        user = User.objects.create(username='old', email='old@x.com',
                                   password=make_password('tanim-palay-2026', hasher='pbkdf2_sha256'))
        r = self.client.post('/api/auth/login/', {'email': 'old@x.com', 'password': 'tanim-palay-2026'}, format='json')
        user.refresh_from_db()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(user.password.startswith('argon2$'))


class SecurityLogTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_failed_login_is_logged(self):
        with self.assertLogs('riceflow.security', 'WARNING') as logs:
            self.client.post('/api/auth/login/', {'email': 'x@x.com', 'password': 'wrong'}, format='json')
        self.assertIn('login failed email=x@x.com', logs.output[0])

    def test_permission_denied_is_logged(self):
        farmer = User.objects.create_user(username='farmer', password='pass12345')
        self.client.force_authenticate(farmer)
        with self.assertLogs('riceflow.security', 'WARNING') as logs:
            r = self.client.get('/api/auth/users/')  # admin only
        self.assertEqual(r.status_code, 403)
        self.assertIn(f'permission denied GET /api/auth/users/ user={farmer.pk}', logs.output[0])

    def test_rate_limit_is_logged(self):
        with self.assertLogs('riceflow.security', 'WARNING') as logs:
            for _ in range(11):
                self.client.post('/api/auth/register/', {}, format='json')
        self.assertTrue(any('rate limited POST /api/auth/register/' in line for line in logs.output))


class ErrorResponseTests(TestCase):
    def test_unexpected_error_returns_json_500_without_details(self):
        client = APIClient()
        client.force_authenticate(User.objects.create_user(username='farmer', password='pass12345'))
        with mock.patch('apps.accounts.views.UserSerializer', side_effect=RuntimeError('db password=secret')), \
                self.assertLogs('riceflow.errors', 'ERROR'):
            r = client.get('/api/auth/profile/')
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json(), {'detail': 'Server error.'})
        self.assertNotIn('secret', r.content.decode())
