from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from . import palaycheck
from .models import PlantingGuide, GuideStep
from .serializers import PlantingGuideSerializer, GuideStepSerializer
from apps.progress.models import YieldRecord
from apps.recommendations.models import Recommendation

# The planting guide is PalayCheck 2022 (palaycheck.py), not generated text. The farmer works
# through it one step at a time; a step is done when they log it (or tick it in Upcoming Tasks).
VALID_GUIDE_LANGS = set(palaycheck.LANGUAGES)
_PAGES = {key: pages for key, _, _, pages in palaycheck.STEPS}


def _step_dict(st, language):
    """A guide step for the app, worded in the farmer's language. Rows from before PalayCheck
    (Gemini text, no template key) keep their saved text until the guide is rebuilt."""
    if st.template_key in palaycheck.TEXT:
        words = palaycheck.text(st.template_key, language)
        ref = palaycheck.reference(_PAGES[st.template_key])
    else:
        words = {'title': st.title, 'instruction': st.description, 'explanation': ''}
        ref = ''
    return {
        'id':                st.id,
        'stepNumber':        st.step_no,
        'key':               st.template_key,
        'keyCheck':          st.key_check,
        'title':             words['title'],
        'instruction':       words['instruction'],
        'explanation':       words['explanation'],
        'reference':         ref,
        'referenceUrl':      palaycheck.REFERENCE_URL if ref else '',
        'daysAfterPlanting': st.days_after_planting if st.days_after_planting is not None else 0,
        'category':          st.category or 'planting',
        'is_completed':      st.is_completed,
    }


def _guide_response(guide, source, language):
    steps = [_step_dict(st, language) for st in guide.steps.order_by('days_after_planting', 'step_no')]
    return {
        'id':         guide.id,
        'farm':       guide.farm_id,
        'variety':    guide.variety_id,
        'season':     guide.season,
        'language':   language,
        'start_date': guide.start_date.isoformat() if guide.start_date else None,
        'source':     source,
        'reference':  palaycheck.REFERENCE,
        'steps':      steps,
    }


def _is_palaycheck(guide) -> bool:
    keys = list(guide.steps.values_list('template_key', flat=True))
    return bool(keys) and all(keys)


def _build_steps(guide, variety):
    """(Re)write the guide's steps from PalayCheck, timed for the variety's maturity."""
    with transaction.atomic():
        guide.steps.all().delete()
        GuideStep.objects.bulk_create([
            GuideStep(
                guide=guide, step_no=n, template_key=st['key'], key_check=st['key_check'],
                title=palaycheck.text(st['key'], 'en')['title'][:150],
                description=palaycheck.text(st['key'], 'en')['instruction'],
                category=st['category'], days_after_planting=st['day'],
                scheduled_date=(guide.start_date + timedelta(days=st['day'])) if guide.start_date else None,
            )
            for n, st in enumerate(palaycheck.plan(variety.maturity_days), start=1)
        ])


def _chosen_result(rec, variety_pk):
    """The recommendation result the guide is for: the variety the farmer picked
    ("Use this instead"). When none is sent, the variety of the farm's latest guide
    from these results (an earlier pick), else the top-ranked one. None when the
    picked variety is not one of this recommendation's results."""
    results = rec.results.select_related('variety').order_by('rank')
    if variety_pk in (None, ''):
        latest = (PlantingGuide.objects
                  .filter(farm=rec.farm, variety__in=results.values('variety'))
                  .order_by('-created_at').first())
        return (results.filter(variety=latest.variety_id).first() if latest else None) or results.first()
    try:
        return results.filter(variety_id=int(variety_pk)).first()
    except (TypeError, ValueError):
        return None


def _has_field_work(cycle) -> bool:
    return cycle.progress_logs.exists() or YieldRecord.objects.filter(farm_cycle=cycle).exists()


def _sowing_day(farm):
    """The sowing day (start_date) of a new guide. A crop with field work logged keeps its
    own date; otherwise it is far enough ahead that the first step (seed preparation)
    falls on the day the guide is made."""
    cycle = farm.farm_cycles.filter(status='active').first()
    if cycle and _has_field_work(cycle):
        return cycle.planting_date
    return timezone.now().date() + timedelta(days=palaycheck.PREP_DAYS)


def _cycle_follows_guide(rec, guide, picked=None):
    """A scan starts the crop cycle (top-ranked variety, sown the day of the scan) before
    there is a guide. Until field work is logged, that cycle follows the guide: the variety
    the farmer picked and the guide's sowing day, so Progress, the guide and the logs count
    the same days. Only the cycle this recommendation started, so a real crop is never changed."""
    cycle = rec.farm.farm_cycles.filter(status='active', created_at__gte=rec.created_at) \
        .select_related('variety').first()
    if not cycle or _has_field_work(cycle):
        return
    variety = picked or cycle.variety
    harvest = (guide.start_date + timedelta(days=int(variety.maturity_days))
               if variety and variety.maturity_days else cycle.expected_harvest_date)
    if (cycle.variety_id, cycle.planting_date, cycle.expected_harvest_date) == \
            (variety and variety.id, guide.start_date, harvest):
        return
    cycle.variety = variety
    cycle.planting_date = guide.start_date
    cycle.expected_harvest_date = harvest
    cycle.save(update_fields=['variety', 'planting_date', 'expected_harvest_date'])


# ── The view ───────────────────────────────────────────────────────────────────
class GeneratePlantingGuideView(APIView):
    """The farm's PalayCheck planting guide for the chosen variety.

    POST body: {"variety": 12, "season": "Wet Season", "language": "en" | "fil" | "ceb",
                "force_regenerate": false}
    The steps are saved once per farm + variety + season, so check-offs survive reinstalls;
    the language only changes the wording, never the steps.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, recommendation_id):
        try:
            rec = Recommendation.objects.select_related('farm').get(
                pk=recommendation_id, farm__user=request.user
            )
        except Recommendation.DoesNotExist:
            return Response({'detail': 'Recommendation not found.'}, status=404)

        if not rec.results.exists():
            return Response({'detail': 'No recommendation results found.'}, status=400)
        chosen = _chosen_result(rec, request.data.get('variety'))
        if not chosen:
            return Response({'detail': "variety must be one of this recommendation's varieties."}, status=400)

        variety = chosen.variety
        language = (request.data.get('language') or 'en').lower()
        if language not in VALID_GUIDE_LANGS:
            language = 'en'

        # start_date is the sowing day (day 0 of the guide)
        guide, _ = PlantingGuide.objects.get_or_create(
            farm=rec.farm, variety=variety, season=request.data.get('season', 'Wet Season'),
            defaults={'start_date': _sowing_day(rec.farm), 'language': language},
        )
        _cycle_follows_guide(rec, guide, variety if request.data.get('variety') not in (None, '') else None)
        # A guide from before PalayCheck (Gemini steps), or a new plan, gets the PalayCheck steps
        if request.data.get('force_regenerate') or not _is_palaycheck(guide):
            _build_steps(guide, variety)
            source = 'PALAYCHECK'
        else:
            source = 'SAVED'
        if guide.language != language:
            guide.language = language
            guide.save(update_fields=['language'])
        return Response(_guide_response(guide, source, language))


class PlantingGuideListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlantingGuideSerializer

    def get_queryset(self):
        # prefetch steps + each step's growth_stage — the serializer nests both,
        # which is N+M queries without prefetch.
        return (PlantingGuide.objects
                .filter(farm__user=self.request.user)
                .prefetch_related('steps__growth_stage'))


class PlantingGuideDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PlantingGuideSerializer

    def get_queryset(self):
        return (PlantingGuide.objects
                .filter(farm__user=self.request.user)
                .prefetch_related('steps__growth_stage'))


class MarkStepCompleteView(APIView):
    """Set a guide step's completion. Steps are persisted GuideStep rows, so this
    is the durable source of truth — reinstalling the app or logging in on
    another device restores check-offs from here.

    PATCH body: { "is_completed": true | false }   (defaults to true)
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, step_id):
        try:
            step = GuideStep.objects.select_related('guide__farm').get(
                pk=step_id, guide__farm__user=request.user
            )
        except GuideStep.DoesNotExist:
            return Response({'detail': 'Step not found.'}, status=404)

        done = bool(request.data.get('is_completed', True))
        step.is_completed = done
        step.completed_at = timezone.now() if done else None
        step.save(update_fields=['is_completed', 'completed_at'])
        return Response(GuideStepSerializer(step).data)
