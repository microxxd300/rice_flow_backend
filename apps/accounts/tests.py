from django.test import TestCase
from rest_framework.test import APIClient


class HealthEndpointTests(TestCase):
    def test_health_is_public_and_reports_database(self):
        r = APIClient().get('/api/health/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['status'], 'ok')
        self.assertEqual(r.json()['database'], 'ok')
        self.assertIn('version', r.json())
