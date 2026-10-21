import logging

from django.conf import settings
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import exception_handler as drf_exception_handler, set_rollback

security_log = logging.getLogger('riceflow.security')
error_log = logging.getLogger('riceflow.errors')


def client_ip(request) -> str:
    """Client IP behind nginx/Render/ngrok, the same way the rate limiter sees it (NUM_PROXIES)."""
    return BaseThrottle().get_ident(request)


def _who(request) -> str:
    user = getattr(request, 'user', None)
    return f'user={user.pk}' if user is not None and user.is_authenticated else 'anonymous'


def exception_handler(exc, context):
    """DRF's handler, plus: log 403s and 429s, and answer unexpected errors with a plain JSON 500.

    Clients never get a stack trace. Locally (DEBUG=True) Django's debug page still shows.
    """
    request = context['request']
    response = drf_exception_handler(exc, context)

    if response is None:
        if settings.DEBUG:
            return None
        error_log.exception('unhandled error on %s %s', request.method, request.path)
        set_rollback()
        return Response({'detail': 'Server error.'}, status=500)

    if isinstance(exc, exceptions.Throttled):
        security_log.warning('rate limited %s %s %s ip=%s retry_after=%ss',
                             request.method, request.path, _who(request), client_ip(request), exc.wait)
    elif isinstance(exc, exceptions.PermissionDenied):
        security_log.warning('permission denied %s %s %s ip=%s',
                             request.method, request.path, _who(request), client_ip(request))
    return response
