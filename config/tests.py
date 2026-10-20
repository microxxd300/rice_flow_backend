from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.farms.models import Farm


class PaginationTests(TestCase):
    URL = '/api/farms/'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='farmer', password='pass12345')
        Farm.objects.bulk_create([
            Farm(user=cls.user, name=f'Farm {i}', barangay='Gredu',
                 latitude=7.3, longitude=125.68, area_hectares=1)
            for i in range(105)
        ])

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_default_page_keeps_existing_keys_and_adds_total_pages(self):
        body = self.client.get(self.URL).json()
        self.assertEqual(set(body), {'count', 'total_pages', 'next', 'previous', 'results'})
        self.assertEqual(body['count'], 105)
        self.assertEqual(body['total_pages'], 6)
        self.assertEqual(len(body['results']), 20)
        self.assertIsNone(body['previous'])

    def test_page_size_query_param(self):
        body = self.client.get(self.URL, {'page_size': 5, 'page': 2}).json()
        self.assertEqual(len(body['results']), 5)
        self.assertEqual(body['total_pages'], 21)
        self.assertIn('page_size=5', body['next'])

    def test_page_size_is_capped(self):
        body = self.client.get(self.URL, {'page_size': 999999}).json()
        self.assertEqual(len(body['results']), 100)
        self.assertEqual(body['total_pages'], 2)
