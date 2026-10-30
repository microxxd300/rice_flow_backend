from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User


class TokenLifecycleTests(TestCase):
    def setUp(self):
        cache.clear()  # login is rate limited
        User.objects.create_user(username='farmer', email='f@x.com', password='pass12345')
        self.client = APIClient()
        r = self.client.post('/api/auth/login/', {'email': 'f@x.com', 'password': 'pass12345'}, format='json')
        self.access, self.refresh = r.json()['access_token'], r.json()['refresh_token']

    def refresh_with(self, token):
        return self.client.post('/api/token/refresh/', {'refresh': token}, format='json')

    def test_access_token_lasts_30_minutes(self):
        token = AccessToken(self.access)
        # iat and exp are read from the clock a moment apart, so the whole-second
        # difference can round down to 1799
        self.assertAlmostEqual(token['exp'] - token['iat'], int(timedelta(minutes=30).total_seconds()), delta=1)

    def test_refresh_rotates_and_old_refresh_token_stops_working(self):
        r = self.refresh_with(self.refresh)
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.json())
        self.assertNotEqual(r.json()['refresh'], self.refresh)

        self.assertEqual(self.refresh_with(self.refresh).status_code, 401)
        self.assertEqual(self.refresh_with(r.json()['refresh']).status_code, 200)

    def test_logout_revokes_the_refresh_token(self):
        r = self.client.post('/api/auth/logout/', {'refresh': self.refresh}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.refresh_with(self.refresh).status_code, 401)

    def test_logout_works_with_an_expired_or_missing_access_token(self):
        # The apps call logout with only the refresh token, no Authorization header
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not-a-valid-token')
        r = self.client.post('/api/auth/logout/', {'refresh': self.refresh}, format='json')
        self.assertEqual(r.status_code, 200)
