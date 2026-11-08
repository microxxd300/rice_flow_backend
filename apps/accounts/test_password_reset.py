import re
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import PasswordResetCode, User

REQUEST = '/api/auth/password-reset/request/'
CONFIRM = '/api/auth/password-reset/confirm/'
OLD = 'Palay-2026!'
NEW = 'Bagong-Palay-77'


class RunNow:
    """Stands in for Thread so the email exists when the test looks for it."""

    def __init__(self, target, args, daemon):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


@patch('apps.accounts.password_reset.Thread', RunNow)
class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in the cache
        self.client = APIClient()
        self.user = User.objects.create_user(username='juan', email='juan@x.com', password=OLD)

    def ask(self, email='juan@x.com'):
        return self.client.post(REQUEST, {'email': email}, format='json')

    def code_from_email(self):
        return re.search(r'\b(\d{6})\b', mail.outbox[-1].body).group(1)

    def confirm(self, code, password=NEW, email='juan@x.com'):
        return self.client.post(CONFIRM, {'email': email, 'code': code, 'new_password': password,
                                          'new_password2': password}, format='json')

    def wrong(self, code):
        return '000000' if code != '000000' else '111111'

    def age_codes(self, **delta):
        PasswordResetCode.objects.update(created_at=timezone.now() - timedelta(**delta))

    def login(self, password):
        return self.client.post('/api/auth/login/', {'email': 'juan@x.com', 'password': password}, format='json')

    def test_code_is_emailed_and_only_stored_hashed(self):
        r = self.ask()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(mail.outbox[-1].to, ['juan@x.com'])
        self.assertNotEqual(PasswordResetCode.objects.get().code_hash, self.code_from_email())

    def test_email_has_a_designed_version_with_the_same_code(self):
        self.ask()
        html, mimetype = mail.outbox[-1].alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn(self.code_from_email(), html)
        self.assertIn('10 minutes', html)

    def test_reply_never_reveals_whether_the_email_is_registered(self):
        known, unknown = self.ask(), self.ask('nobody@x.com')
        self.assertEqual((known.status_code, known.json()), (unknown.status_code, unknown.json()))
        self.assertEqual(len(mail.outbox), 1)

    def test_disabled_account_gets_no_code(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(mail.outbox, [])

    def test_capitals_in_the_email_are_forgiven_but_the_saved_address_gets_the_mail(self):
        self.ask('JUAN@X.com')
        self.assertEqual(mail.outbox[-1].to, ['juan@x.com'])

    def test_right_code_sets_the_new_password_once(self):
        self.ask()
        code = self.code_from_email()
        self.assertEqual(self.confirm(code).status_code, 200)
        self.assertEqual(self.login(NEW).status_code, 200)
        self.assertEqual(self.login(OLD).status_code, 400)
        self.assertEqual(self.confirm(code, 'Pangatlo-Palay-88').status_code, 400)

    def test_reset_logs_out_existing_sessions(self):
        refresh = self.login(OLD).json()['refresh_token']
        self.ask()
        self.confirm(self.code_from_email())
        self.assertEqual(self.client.post('/api/token/refresh/', {'refresh': refresh}, format='json').status_code, 401)

    def test_code_dies_after_5_wrong_tries(self):
        self.ask()
        code = self.code_from_email()
        for _ in range(5):
            self.assertIn('code', self.confirm(self.wrong(code)).json())
        self.assertEqual(self.confirm(code).status_code, 400)
        self.assertEqual(self.login(OLD).status_code, 200)

    def test_expired_code_is_refused(self):
        self.ask()
        PasswordResetCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.confirm(self.code_from_email()).status_code, 400)

    def test_new_code_replaces_the_old_one(self):
        self.ask()
        first = self.code_from_email()
        self.age_codes(minutes=2)
        self.ask()
        second = self.code_from_email()
        if first != second:
            self.assertEqual(self.confirm(first).status_code, 400)
        self.assertEqual(self.confirm(second).status_code, 200)

    def test_weak_password_is_refused_and_keeps_the_code_usable(self):
        self.ask()
        code = self.code_from_email()
        r = self.confirm(code, '12345678')
        self.assertEqual(r.status_code, 400)
        self.assertIn('new_password', r.json())
        self.assertEqual(self.confirm(code).status_code, 200)

    def test_passwords_must_match(self):
        self.ask()
        r = self.client.post(CONFIRM, {'email': 'juan@x.com', 'code': self.code_from_email(),
                                       'new_password': NEW, 'new_password2': 'Iba-Palay-99'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('new_password', r.json())

    def test_unknown_email_gets_the_same_error_as_a_wrong_code(self):
        self.ask()
        wrong_code = self.confirm(self.wrong(self.code_from_email()))
        unknown = self.confirm('123456', email='nobody@x.com')
        self.assertEqual((wrong_code.status_code, wrong_code.json()), (unknown.status_code, unknown.json()))

    def test_must_wait_before_a_second_email(self):
        self.ask()
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_no_more_than_5_codes_a_day(self):
        for _ in range(7):
            self.ask()
            self.age_codes(minutes=2)
        self.assertEqual(len(mail.outbox), 5)

    def test_mail_failure_still_answers_normally(self):
        with patch('apps.accounts.password_reset.send_mail', side_effect=OSError('smtp down')):
            self.assertEqual(self.ask().status_code, 200)

    def test_requests_are_rate_limited_per_ip(self):
        for _ in range(10):
            self.ask('nobody@x.com')
        self.assertEqual(self.ask('nobody@x.com').status_code, 429)
