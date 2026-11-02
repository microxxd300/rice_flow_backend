from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.permissions import IsSuperUser
from .models import ChangeLog, FarmerNotice

NOTICE_DAYS = 30   # older notices are not sent to the app


class ChangeLogView(APIView):
    """
    GET /api/activity/changes/?role=validator&limit=50
    The admin website's change log, newest first. Admin only: it is how the admin
    sees what the validator (and other admins) changed.
    """
    permission_classes = [IsSuperUser]

    def get(self, request):
        rows = ChangeLog.objects.all()
        role = request.query_params.get('role')
        if role in ('admin', 'validator'):
            rows = rows.filter(actor_role=role)
        try:
            limit = max(1, min(int(request.query_params.get('limit', 100)), 500))
        except ValueError:
            limit = 100
        return Response([{
            'id':         r.id,
            'actor_name': r.actor_name,
            'actor_role': r.actor_role,
            'action':     r.action,
            'target':     r.target,
            'summary':    r.summary,
            'changes':    r.changes,
            'created_at': r.created_at.isoformat(),
        } for r in rows[:limit]])


class FarmerNoticeListView(APIView):
    """
    GET /api/activity/notices/?after=<id>
    The signed-in farmer's notices from the last 30 days, newest first (at most 20).
    The app sends the newest id it already has as `after` and adds the rest to the bell.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = FarmerNotice.objects.filter(user=request.user,
                                           created_at__gte=timezone.now() - timedelta(days=NOTICE_DAYS))
        after = request.query_params.get('after')
        if after and after.isdigit():
            rows = rows.filter(id__gt=int(after))
        return Response([{
            'id':         n.id,
            'kind':       n.kind,
            'params':     n.params,
            'title':      n.title,
            'body':       n.body,
            'created_at': n.created_at.isoformat(),
        } for n in rows[:20]])
