"""
python manage.py generate_variety_descriptions [--force]

Generate a short farmer-friendly description for each rice variety, grounded
strictly in that variety's real dataset fields (never invented). Stored on
RiceVariety.ai_description so the mobile variety page reads it instantly with
no per-view AI call.

Idempotent: skips varieties that already have a description unless --force.
"""
import os
import requests
from django.core.management.base import BaseCommand
from apps.varieties.models import RiceVariety

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_URL = (
    'https://generativelanguage.googleapis.com/v1beta/models/'
    'gemini-2.5-flash-lite:generateContent'
)


def _facts(v):
    def tol(x):
        return x or 'unknown'

    return (
        f"NSIC code: {v.nsic_code}\n"
        f"Common name: {v.common_name}\n"
        f"Ecosystem: {v.get_ecosystem_display()}\n"
        f"Maturity: {v.maturity_days} days\n"
        f"Average yield: {v.avg_yield_t_ha} t/ha (max {v.max_yield_t_ha} t/ha)\n"
        f"Submergence/flood tolerance: {tol(v.submergence_tolerance)}\n"
        f"Drought tolerance: {tol(v.drought_tolerance)}\n"
        f"Salinity tolerance: {tol(v.salinity_tolerance)}\n"
        f"Grain type: {v.grain_type or 'unknown'}\n"
        f"Optimal temperature: {v.optimal_temp_min}-{v.optimal_temp_max} C\n"
    )


def _generate(v):
    """Ask Gemini for a 2-3 sentence description grounded in the variety facts."""
    if not GEMINI_API_KEY:
        return None
    prompt = (
        "You are a Philippine rice agronomist writing a short, friendly "
        "description of a rice variety for a smallholder farmer.\n\n"
        "Use ONLY these facts — do not invent numbers, traits, or claims:\n\n"
        f"{_facts(v)}\n"
        "Write 2-3 plain-English sentences describing what this variety is, "
        "what conditions it suits, and its key strength (yield, maturity, or a "
        "tolerance). No markdown, no bullet points, no heading — just the "
        "sentences."
    )
    payload = {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.4, 'maxOutputTokens': 220,
            'thinkingConfig': {'thinkingBudget': 0},
        },
    }
    try:
        resp = requests.post(GEMINI_URL, headers={'x-goog-api-key': GEMINI_API_KEY}, json=payload, timeout=30)
        if resp.status_code != 200:
            return None
        body = resp.json()
        text = (body.get('candidates') or [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return text.strip() or None
    except Exception:
        return None


class Command(BaseCommand):
    help = 'Generate farmer-friendly descriptions for rice varieties (grounded in real data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Regenerate even for varieties that already have a description',
        )

    def handle(self, *args, **opts):
        if not GEMINI_API_KEY:
            self.stderr.write(self.style.ERROR('GEMINI_API_KEY not set — cannot generate.'))
            return

        qs = RiceVariety.objects.filter(is_active=True)
        if not opts['force']:
            qs = qs.filter(ai_description='')

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nothing to do — all varieties already have descriptions.'))
            return

        self.stdout.write(f'Generating descriptions for {total} varieties...')
        ok, failed = 0, 0
        for v in qs:
            desc = _generate(v)
            if desc:
                v.ai_description = desc
                v.save(update_fields=['ai_description'])
                ok += 1
                self.stdout.write(f'  ✓ {v.nsic_code} {v.common_name}')
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(f'  ✗ {v.nsic_code} — generation failed'))

        self.stdout.write(self.style.SUCCESS(f'\nDone: {ok} generated, {failed} failed.'))
