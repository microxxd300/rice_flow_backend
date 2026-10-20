from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User

BAD_LOGIN = {'email': 'nobody@x.com', 'password': 'wrong-password'}


class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.client = APIClient()

    def login(self, ip='10.0.0.1'):
        return self.client.post('/api/auth/login/', BAD_LOGIN, format='json', HTTP_X_FORWARDED_FOR=ip)

    def test_login_is_blocked_after_10_attempts_per_minute(self):
        for _ in range(10):
            self.assertEqual(self.login().status_code, 400)
        blocked = self.login()
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('Retry-After', blocked)

    def test_limits_are_per_client_ip(self):
        for _ in range(11):
            self.login(ip='10.0.0.1')
        self.assertEqual(self.login(ip='10.0.0.2').status_code, 400)

    def test_client_cannot_fake_its_ip(self):
        # nginx appends the real client IP; with NUM_PROXIES=1 the last entry is used
        for i in range(11):
            r = self.login(ip=f'1.2.3.{i}, 10.0.0.1')
        self.assertEqual(r.status_code, 429)

    def test_register_is_blocked_after_10_attempts_per_hour(self):
        for _ in range(10):
            self.client.post('/api/auth/register/', {}, format='json')
        self.assertEqual(self.client.post('/api/auth/register/', {}, format='json').status_code, 429)

    def test_ai_chat_is_blocked_after_60_messages_per_hour(self):
        self.client.force_authenticate(User.objects.create_user(username='farmer', password='pass12345'))
        for _ in range(60):
            self.client.post('/api/ai/chat/', {'message': ''}, format='json')  # 400, no Gemini call
        self.assertEqual(self.client.post('/api/ai/chat/', {'message': ''}, format='json').status_code, 429)

    def test_health_check_is_never_throttled(self):
        for _ in range(301):  # one more than the anonymous hourly limit
            r = self.client.get('/api/health/')
        self.assertEqual(r.status_code, 200)
