from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User

PASSWORD = 'Palay-Tanim-2026'


class GmailOnlySignupTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache

    def register(self, email):
        return APIClient().post('/api/auth/register/', {
            'email': email, 'password': PASSWORD, 'password2': PASSWORD,
            'first_name': 'Ana', 'last_name': 'Cruz'}, format='json')

    def test_gmail_can_sign_up(self):
        for email in ('ana@gmail.com', 'ana2@GMAIL.com', 'ana3@googlemail.com'):
            self.assertEqual(self.register(email).status_code, 201, email)

    def test_other_addresses_are_refused(self):
        for email in ('ana@georice.app', 'ana@yahoo.com', 'ana@gmail.com.ph', 'ana@notgmail.com'):
            r = self.register(email)
            self.assertEqual(r.status_code, 400, email)
            self.assertIn('Gmail', r.json()['email'][0])
        self.assertFalse(User.objects.exists())

    def test_existing_non_gmail_account_can_still_log_in(self):
        User.objects.create_user(username='old', email='old@georice.app', password=PASSWORD)
        r = APIClient().post('/api/auth/login/', {'email': 'old@georice.app', 'password': PASSWORD}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_admin_can_still_create_a_non_gmail_farmer(self):
        admin = User.objects.create_superuser(username='boss', email='boss@georice.app', password=PASSWORD)
        client = APIClient()
        client.force_authenticate(admin)
        r = client.post('/api/auth/users/', {'username': 'noemail', 'email': 'noemail@georice.app',
                                             'password': PASSWORD}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
