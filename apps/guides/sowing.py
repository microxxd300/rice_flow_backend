"""The sowing day: the one date the whole plan hangs on.

The guide plans sowing for a day, but farmers rarely sow exactly then: they wait for
rain, seed or labor. So the app asks "Did you sow already?" on that day:
- sown on a date: the plan moves to that real day (every step not done yet, the crop
  cycle's planting and harvest dates), and the steps up to sowing count as done;
- not yet: the plan moves NOT_YET_DAYS later and the question comes back then.
Logging the sowing step answers it too, and a later step logged without sowing gives
an estimate of the sowing day for the farmer to confirm.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import palaycheck

SOWING_KEY = 'seedbed'
NOT_YET_DAYS = 3
OLDEST_SOWING_DAYS = 150   # a sowing date further back is a typo, not this crop


def sowing_step(guide):
    return guide.steps.filter(template_key=SOWING_KEY).first()


def is_sown(guide) -> bool:
    step = sowing_step(guide)
    return bool(step and step.is_completed)


def active_cycle(guide):
    return guide.farm.farm_cycles.filter(status='active').order_by('-planting_date').first()


def _replan(guide, sowing):
    """Move the plan to a new sowing day: the steps not done yet, and the crop cycle."""
    guide.start_date = sowing
    guide.save(update_fields=['start_date'])
    steps = list(guide.steps.filter(is_completed=False))
    for st in steps:
        st.scheduled_date = sowing + timedelta(days=st.days_after_planting or 0)
    guide.steps.model.objects.bulk_update(steps, ['scheduled_date'])

    cycle = active_cycle(guide)
    if cycle:
        variety = cycle.variety or guide.variety
        cycle.planting_date = sowing
        if variety and variety.maturity_days:
            cycle.expected_harvest_date = sowing + timedelta(days=int(variety.maturity_days))
        cycle.season = 'wet' if 5 <= sowing.month <= 10 else 'dry'
        cycle.year = sowing.year
        cycle.save(update_fields=['planting_date', 'expected_harvest_date', 'season', 'year'])
    return cycle


def check_sowing_date(sown_on):
    """None when the date can be this crop's sowing day, else why not."""
    today = timezone.localdate()
    if sown_on > today:
        return 'The sowing date cannot be in the future.'
    if sown_on < today - timedelta(days=OLDEST_SOWING_DAYS):
        return f'The sowing date is more than {OLDEST_SOWING_DAYS} days ago.'
    return None


@transaction.atomic
def confirm_sowing(guide, sown_on, log=None):
    """The farmer sowed on `sown_on`. `log` is the field log that said so, if any;
    without one, a sowing log is saved so the crop's history shows it."""
    from apps.progress.models import ProgressLog

    cycle = _replan(guide, sown_on)
    step = sowing_step(guide)
    up_to = step.days_after_planting if step else 0
    # Seeds and land preparation come before sowing, so sowing means they are done
    guide.steps.filter(is_completed=False, days_after_planting__lte=up_to) \
        .update(is_completed=True, completed_at=timezone.now())
    if step and log is None and cycle and not step.logs.exists():
        ProgressLog.objects.create(farm_cycle=cycle, log_date=sown_on, guide_step=step,
                                   observation=palaycheck.text(SOWING_KEY, 'en')['title'])


@transaction.atomic
def postpone_sowing(guide, days=NOT_YET_DAYS):
    """Not sown yet: sowing moves `days` later than today (or than the planned day)."""
    _replan(guide, max(guide.start_date, timezone.localdate()) + timedelta(days=days))


def sowing_estimate(step, log_date):
    """The sowing day a later step implies (transplanting 21 days after sowing...), when the
    farmer logs it before saying they sowed; None for steps before sowing."""
    if not step or step.template_key == SOWING_KEY or (step.days_after_planting or 0) <= 0:
        return None
    if is_sown(step.guide):
        return None
    return log_date - timedelta(days=step.days_after_planting)
