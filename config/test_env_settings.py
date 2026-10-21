import importlib

from django.test import TestCase, override_settings
from django.urls import clear_url_caches
from rest_framework.test import APIClient

import config.urls


class AdminUrlTests(TestCase):
    def reload_urls(self):
        clear_url_caches()
        importlib.reload(config.urls)

    def tearDown(self):
        self.reload_urls()  # back to the real ADMIN_URL for other tests

    def test_default_admin_url(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)  # redirects to the admin login

    @override_settings(ADMIN_URL='admin/x7k2q9/')
    def test_custom_admin_url_hides_the_default_path(self):
        self.reload_urls()
        self.assertEqual(self.client.get('/admin/x7k2q9/').status_code, 302)
        self.assertEqual(self.client.get('/admin/').status_code, 404)


@override_settings(CORS_ALLOW_ALL_ORIGINS=False, CORS_ALLOWED_ORIGINS=['https://admin.example.com'])
class CorsTests(TestCase):
    def preflight(self, origin):
        return APIClient().options('/api/health/', HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET')

    def test_allowed_origin_gets_cors_headers(self):
        r = self.preflight('https://admin.example.com')
        self.assertEqual(r.get('Access-Control-Allow-Origin'), 'https://admin.example.com')

    def test_other_origins_do_not(self):
        self.assertNotIn('Access-Control-Allow-Origin', self.preflight('https://evil.example.com'))
