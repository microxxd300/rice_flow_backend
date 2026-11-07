from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .knowledge import LANGS, PROBLEMS


def _lang(value):
    value = (value or 'en').lower()
    return value if value in LANGS else 'en'


class ProblemListView(APIView):
    """GET /api/advice/problems/?language=ceb — the problems a farmer can pick from."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(services.problem_list(_lang(request.query_params.get('language'))))


class ProblemDetailView(APIView):
    """GET /api/advice/problems/<key>/?language=ceb — the booklet card. No AI: it always works."""
    permission_classes = [IsAuthenticated]

    def get(self, request, key):
        if key not in PROBLEMS:
            return Response({'detail': 'Unknown problem.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(services.card(key, _lang(request.query_params.get('language'))))


class MatchView(APIView):
    """POST /api/advice/match/ {text, language} — which problems the farmer's description
    most likely is, from the approved list only. The farmer confirms one."""
    permission_classes = [IsAuthenticated]
    throttle_scope = 'ai_chat'

    def post(self, request):
        text = (request.data.get('text') or '').strip()
        if not text:
            return Response({'error': 'Describe what you see.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(services.match(request.user, text, _lang(request.data.get('language'))))


class ExplainView(APIView):
    """POST /api/advice/explain/ {problem, language, farm?, question?, log?} — the AI explains the
    problem's booklet cards for this farm. Every point lists its sources; with no checked
    answer, points is empty and note says why (the app shows the booklet card alone).
    With `log` (the farmer's own problem log), the farmer's observation is the question and
    a checked answer is saved on the log, so the same problem never asks the AI again."""
    permission_classes = [IsAuthenticated]
    throttle_scope = 'ai_chat'

    def post(self, request):
        key = request.data.get('problem')
        if key not in PROBLEMS:
            return Response({'error': 'Unknown problem.'}, status=status.HTTP_400_BAD_REQUEST)
        from apps.ai.context import farmer_context   # the chat's farm summary: stage, step, weather
        from apps.progress.models import ProgressLog

        lang = _lang(request.data.get('language'))
        log = None
        if str(request.data.get('log') or '').isdigit():
            log = ProgressLog.objects.filter(pk=request.data['log'],
                                             farm_cycle__farm__user=request.user).first()
            saved = (log.advice_tip or {}) if log else {}
            if saved.get('problem') == key and saved.get('language') == lang:
                return Response(saved)
        question = request.data.get('question') or (log.observation if log else '')
        farm = farmer_context(request.user, request.data.get('farm'))
        result = services.explain(request.user, key, lang, farm, question)
        if log and result.get('ai_used'):
            log.advice_tip = {**result, 'language': lang}
            log.save(update_fields=['advice_tip'])
        return Response(result)
