"""
The admin's season board: how many crops are at each growth stage, and the farms that
need the agriculturist's attention now.

- late_steps:      the crop's current PalayCheck step is LATE_DAYS or more past its date
- problems:        logs that report a problem (pest, disease, weather, ...) in the last week
- flagged_pins:    farms pinned on a road, a building, water or mangrove (location check)
- harvest_overdue: an active crop HARVEST_GRACE_DAYS past its expected harvest with no yield

Beside the stage counts: crops planned but not sown yet, and crops harvested this season.

Each list is capped at LIST_LIMIT rows (worst first) with its full count beside it.
"""
from collections import Counter
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.farms.models import Farm
from apps.guides.models import PlantingGuide
from apps.progress.models import FarmCycle, ProgressLog
from apps.progress.stages import growth_stages, stage_today

LATE_DAYS = 3
PROBLEM_WINDOW_DAYS = 7
HARVEST_GRACE_DAYS = 7
LIST_LIMIT = 8
# The location check's problems (farms/location_check.py), as stored on Farm.location_flag
PIN_PROBLEMS = ('on_building', 'built_up', 'water', 'mangrove')


def _farmer(farm):
    u = farm.user
    return (f'{u.first_name} {u.last_name}'.strip() or u.username) if u else ''


def _row(farm, **extra):
    return {'farm_id': farm.id, 'farm': farm.name, 'farmer': _farmer(farm),
            'barangay': farm.barangay or '', **extra}


def _capped(rows, key):
    rows = sorted(rows, key=key)
    return {'count': len(rows), 'items': rows[:LIST_LIMIT]}


def season_start(today):
    """First day of the cropping season `today` is in: wet May-October, dry November-April."""
    if 5 <= today.month <= 10:
        return date(today.year, 5, 1)
    return date(today.year if today.month >= 11 else today.year - 1, 11, 1)


def season_board(today=None):
    today = today or timezone.localdate()
    cycles = list(FarmCycle.objects.filter(status='active', farm__is_active=True)
                  .select_related('farm', 'farm__user', 'variety'))

    # Crops at each of the 10 stages, by the crop's age or its logged steps (stage_today)
    stages = growth_stages()
    by_no = Counter()
    not_sown = 0
    for c in cycles:
        st = stage_today(c, stages)
        if st:
            by_no[st.stage_no] += 1
        else:
            not_sown += 1

    # Crops already harvested since this season began (no longer in the field, so not above)
    start = season_start(today)
    harvested = FarmCycle.objects.filter(status='completed', farm__is_active=True).filter(
        Q(actual_harvest_date__range=(start, today))
        | Q(actual_harvest_date__isnull=True, yield_record__harvest_date__range=(start, today))
    ).count()
    stage_rows = [{'stage_no': s.stage_no, 'name': s.name, 'count': by_no.get(s.stage_no, 0)}
                  for s in sorted(stages, key=lambda s: s.stage_no)]

    # Late PalayCheck steps: each crop's newest guide, its first step not done
    late = []
    farm_ids = {c.farm_id for c in cycles}
    latest_guide = {}
    for g in PlantingGuide.objects.filter(farm_id__in=farm_ids).order_by('farm_id', '-created_at'):
        latest_guide.setdefault(g.farm_id, g)
    for c in cycles:
        g = latest_guide.get(c.farm_id)
        if not g:
            continue
        step = g.steps.filter(is_completed=False).order_by('step_no').first()
        if step and step.scheduled_date and (today - step.scheduled_date).days >= LATE_DAYS:
            late.append(_row(c.farm, step=step.title, due=step.scheduled_date.isoformat(),
                             days_late=(today - step.scheduled_date).days))

    # Problems farmers logged this week and have not marked fixed
    since = today - timedelta(days=PROBLEM_WINDOW_DAYS)
    sev_rank = {'high': 0, 'medium': 1, 'low': 2, '': 3}
    problems = [
        _row(log.farm_cycle.farm, issue=log.issue_type, issue_label=log.get_issue_type_display(),
             severity=log.severity, date=log.log_date.isoformat(), note=(log.observation or '')[:140])
        for log in ProgressLog.objects.filter(log_date__gte=since, farm_cycle__farm__is_active=True,
                                              resolved_at__isnull=True)
        .exclude(issue_type='').select_related('farm_cycle__farm', 'farm_cycle__farm__user')
    ]

    # Pins the location check flagged (the farmer may have kept them anyway)
    # (location_flag is the problem found, or 'ok' / 'unchecked' / 'warning' when there is none)
    pins = [_row(f, flag=f.location_flag, kept=f.location_confirmed)
            for f in Farm.objects.filter(is_active=True, location_flag__in=PIN_PROBLEMS).select_related('user')]

    # Crops past their harvest date with no harvest recorded
    overdue = []
    for c in cycles:
        if c.expected_harvest_date and (today - c.expected_harvest_date).days >= HARVEST_GRACE_DAYS \
                and not hasattr(c, 'yield_record'):
            overdue.append(_row(c.farm, variety=c.variety.common_name if c.variety else '',
                                expected=c.expected_harvest_date.isoformat(),
                                days_over=(today - c.expected_harvest_date).days))

    return {
        # Only sown crops: the ones the stage counts above add up to
        'active_crops': sum(by_no.values()),
        'stages': stage_rows,
        # Crops outside the stage counts: planned but not sown, and harvested this season
        'not_sown': not_sown,
        'harvested_this_season': harvested,
        'season': 'wet' if start.month == 5 else 'dry',
        'season_start': start.isoformat(),
        'attention': {
            'late_steps':      _capped(late, key=lambda r: -r['days_late']),
            # worst first, then newest
            'problems':        _capped(problems, key=lambda r: (sev_rank.get(r['severity'], 3),
                                                            -date.fromisoformat(r['date']).toordinal())),
            'flagged_pins':    _capped(pins, key=lambda r: (r['kept'], r['farm'])),
            'harvest_overdue': _capped(overdue, key=lambda r: -r['days_over']),
        },
    }
