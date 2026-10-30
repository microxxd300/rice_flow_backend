"""What the chat knows about the farmer's own farm, so answers fit their field.

Only farm facts go to Gemini: no names, email or the farm's name. Text the farmer
typed (log notes) is cut short and the prompt treats all of it as data.
"""
from django.utils import timezone

from apps.environmental.services.openmeteo import get_current_weather
from apps.farms.models import Farm
from apps.guides.models import PlantingGuide
from apps.progress.models import ProgressLog

MAX_NOTE_CHARS = 120


def _short(text) -> str:
    text = ' '.join(str(text or '').split())
    return text if len(text) <= MAX_NOTE_CHARS else text[:MAX_NOTE_CHARS] + '...'


def _selected_farm(user, farm_id):
    """The farm the app has selected, if it is the farmer's; else their newest farm."""
    farms = Farm.objects.filter(user=user, is_active=True)
    farm = None
    if farm_id not in (None, ''):
        try:
            farm = farms.filter(pk=int(farm_id)).first()
        except (TypeError, ValueError):
            farm = None
    return farm or farms.order_by('-created_at').first()


def farmer_context(user, farm_id=None) -> str:
    farm = _selected_farm(user, farm_id)
    today = timezone.localdate()
    if not farm:
        return f'Today is {today:%B %d, %Y}. The farmer has not registered a farm in the app yet.'

    lines = [
        f'Today is {today:%B %d, %Y}.',
        f'Farm: {farm.area_hectares} ha, {farm.get_ecosystem_display().lower()}, barangay {farm.barangay}, Panabo City.',
    ]

    scan = farm.scans.order_by('-scanned_at').first()
    if scan:
        soil = ', '.join(filter(None, [
            scan.soil_texture and f'{scan.soil_texture} soil',
            scan.soil_ph is not None and f'pH {scan.soil_ph:.1f}',
            scan.flood_risk and f'{scan.flood_risk} flood risk',
            scan.annual_rainfall_mm is not None and f'{scan.annual_rainfall_mm:.0f} mm rain a year',
            scan.elevation_m is not None and f'{scan.elevation_m:.0f} m elevation',
        ]))
        if soil:
            lines.append(f'Latest scan ({scan.scanned_at:%B %d}): {soil}.')

    guide = PlantingGuide.objects.filter(farm=farm).select_related('variety').order_by('-created_at').first()
    cycle = farm.farm_cycles.filter(status='active').select_related('variety', 'current_stage') \
        .order_by('-planting_date').first()
    variety = (cycle and cycle.variety) or (guide and guide.variety)
    if variety:
        lines.append(f'Chosen variety: {variety.common_name} ({variety.nsic_code}), matures in '
                     f'{variety.maturity_days} days.')
    if cycle:
        day = (today - cycle.planting_date).days
        if day < 0:
            lines.append(f'Sowing is planned for {cycle.planting_date:%B %d}.')
        else:
            stage = f', stage: {cycle.current_stage.name}' if cycle.current_stage else ''
            # Worked out here, not left to the model's arithmetic
            harvest = (f', expected harvest {cycle.expected_harvest_date:%B %d} '
                       f'(in about {max(0, (cycle.expected_harvest_date - today).days)} days)'
                       if cycle.expected_harvest_date else '')
            lines.append(f'Current crop: sown {cycle.planting_date:%B %d}, day {day} after sowing{stage}{harvest}.')
    else:
        lines.append('No crop is planted yet (no active planting cycle).')

    if guide:
        steps = guide.steps.filter(is_completed=False).order_by('days_after_planting', 'step_no')[:3]
        if steps:
            lines.append('Next planting-guide steps not done yet: ' + '; '.join(
                f'day {s.days_after_planting}: {_short(s.title)}' for s in steps) + '.')

    logs = ProgressLog.objects.filter(farm_cycle__farm=farm).order_by('-log_date', '-id')[:3]
    for log in logs:
        issue = log.get_issue_type_display() if log.issue_type else 'Observation'
        severity = f' ({log.severity})' if log.severity else ''
        action = f'; action taken: {_short(log.action_taken)}' if log.action_taken else ''
        lines.append(f'Field log {log.log_date:%B %d}: {issue}{severity} - {_short(log.observation)}{action}.')

    try:
        weather = get_current_weather(float(farm.latitude), float(farm.longitude))
        lines.append(f"Weather, next 7 days: {weather['weekly_rainfall_mm']} mm rain in total, "
                     f"about {weather['avg_temperature']} C.")
    except Exception:
        pass   # answer without the forecast rather than fail the chat

    return '\n'.join(lines)
