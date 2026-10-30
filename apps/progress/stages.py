"""The growth stage a crop is in today.

FarmCycle.current_stage is set once, when the cycle starts, and nothing moves it on,
so a crop sown in June still read "Germination & Seedling" in October. The stage is
worked out from the crop's age instead: day 0 = sowing (planting_date), the same
timeline the planting guide uses, against each GrowthStage's day range.
"""
from django.utils import timezone

from apps.varieties.models import GrowthStage


def growth_stages() -> list:
    """All stages in order; load once and pass to stage_today() for many cycles."""
    return list(GrowthStage.objects.order_by('stage_no'))


def stage_today(cycle, stages=None, today=None):
    """The cycle's stage for its age. Only an active cycle moves on; a completed or
    abandoned one keeps the stage it was saved with."""
    if cycle.status != 'active' or not cycle.planting_date:
        return cycle.current_stage
    stages = growth_stages() if stages is None else stages
    day = max(0, ((today or timezone.localdate()) - cycle.planting_date).days)
    start = 'days_min_upland' if cycle.farm.ecosystem == 'upland' else 'days_min_paddy'
    # The last stage that has started by this day (stage start days only go up)
    current = None
    for stage in stages:
        if getattr(stage, start) <= day:
            current = stage
    return current or cycle.current_stage
