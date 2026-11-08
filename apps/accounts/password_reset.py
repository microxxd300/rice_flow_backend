"""Forgot password: a 6-digit code goes to the account's email, then the code sets a new password."""
import logging
import secrets
from datetime import timedelta
from threading import Thread

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import PasswordResetCode

User = get_user_model()
logger = logging.getLogger('riceflow.email')

CODE_LIFETIME = timedelta(minutes=10)
RESEND_WAIT = timedelta(seconds=60)
MAX_WRONG_TRIES = 5   # per code
MAX_CODES_PER_DAY = 5  # per account: limits guessing, inbox flooding and the Gmail quota

BAD_CODE = 'That code is wrong or has expired. Please request a new one.'


def _find_user(email):
    """The one active account for this email. Exact spelling wins, as in login; capitals are
    forgiven only if that leaves a single account. Emails aren't unique in the database."""
    users = list(User.objects.filter(email__iexact=email, is_active=True))
    matches = [u for u in users if u.email == email] or users
    return matches[0] if len(matches) == 1 else None


def _hash(user, code):
    return salted_hmac('riceflow.password_reset', f'{user.pk}:{code}', algorithm='sha256').hexdigest()


def _deliver(to, code):
    minutes = CODE_LIFETIME.seconds // 60
    try:
        send_mail(
            'Your RiceFlow password reset code',
            f'Your RiceFlow code is {code}\n\n'
            f'Enter it in the app to set a new password. It works for {minutes} minutes.\n\n'
            'Never share this code with anyone. If you did not ask for it, you can ignore this email. '
            'Your password has not changed.',
            settings.DEFAULT_FROM_EMAIL,
            [to],
            html_message=render_to_string('accounts/password_reset_email.html', {'code': code, 'minutes': minutes}),
        )
    except Exception:  # noqa: BLE001 - a mail failure must never reach the farmer as a crash
        logger.exception('password reset email could not be sent')


def send_code(email):
    """Email a new code if the account exists. Says nothing either way, and mails in the
    background so the response time doesn't reveal which emails are registered."""
    user = _find_user(email)
    if user is None:
        return
    now = timezone.now()
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)  # one request at a time per account
        today = user.password_reset_codes.filter(created_at__gte=now - timedelta(days=1))
        if today.filter(created_at__gte=now - RESEND_WAIT).exists() or today.count() >= MAX_CODES_PER_DAY:
            return
        today.filter(used_at__isnull=True).update(used_at=now)  # only the newest code works
        code = f'{secrets.randbelow(1_000_000):06d}'
        user.password_reset_codes.create(code_hash=_hash(user, code), expires_at=now + CODE_LIFETIME)
    Thread(target=_deliver, args=(user.email, code), daemon=True).start()


def reset_password(email, code, new_password):
    """Set the new password if the code is right. Returns field errors, or None when done."""
    with transaction.atomic():
        now = timezone.now()
        user = _find_user(email)
        entry = user and PasswordResetCode.objects.select_for_update().filter(
            user=user, used_at__isnull=True, expires_at__gt=now, attempts__lt=MAX_WRONG_TRIES,
        ).order_by('-created_at').first()
        if not entry:
            return {'code': [BAD_CODE]}
        if not constant_time_compare(entry.code_hash, _hash(user, code)):
            entry.attempts += 1
            entry.save(update_fields=['attempts'])
            return {'code': [BAD_CODE]}
        # Checked after the code so a weak password doesn't use the code up
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return {'new_password': list(e.messages)}
        user.set_password(new_password)
        user.save(update_fields=['password'])
        entry.used_at = now
        entry.save(update_fields=['used_at'])
        # Log out every phone: whoever had the old password shouldn't stay signed in
        BlacklistedToken.objects.bulk_create(
            [BlacklistedToken(token=t) for t in OutstandingToken.objects.filter(user=user, expires_at__gt=now)],
            ignore_conflicts=True,
        )
    return None
