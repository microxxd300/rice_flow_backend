"""The growth stage a crop is in today.

FarmCycle.current_stage is set once, when the cycle starts, and nothing moves it on,
so a crop sown in June still read "Germination & Seedling" in October. The stage is
worked out from the crop's age instead: day 0 = sowing (planting_date), the same
timeline the planting guide uses, against each GrowthStage's day range. The PalayCheck
steps the farmer has logged move it on too: whichever is further along counts, so a
farmer who logs sees the real stage at once and one who forgets still sees time pass.
"""
from datetime import timedelta

from django.utils import timezone

from apps.guides.direct_seeded import STEP_STAGE as DIRECT_SEEDED_STAGE
from apps.guides.models import PlantingGuide
from apps.varieties.models import GrowthStage

# The GrowthStage (stage_no) a PalayCheck step belongs to; prep steps before sowing have none
STEP_STAGE = {
    'seedbed': 1,                                    # Germination & Seedling
    'leveling': 2, 'transplant': 2, 'replant': 2,    # Seedling Stage
    'fertilizer1': 3, 'lcc': 3, 'water': 3, 'weeds': 3, 'pests': 3, 'fertilizer2': 3,   # Tillering
    'fertilizerpi': 4,                               # Stem Elongation (before panicle initiation)
    'flowering': 6,                                  # Heading / Flowering
    'drain': 8,                                      # Ripening / Maturity
    'harvest': 9,                                    # Harvesting
    'drystore': 10,                                  # Post-Harvest
    **DIRECT_SEEDED_STAGE,                           # upland and rainfed guides
}


def guide_stage_no(cycle) -> int:
    """The furthest stage the farmer's logged guide steps reach (0 for none). Only a guide
    for this crop counts (sown within a month of it), never the last crop's finished one."""
    window = (cycle.planting_date - timedelta(days=30), cycle.planting_date + timedelta(days=30))
    guides = PlantingGuide.objects.filter(farm_id=cycle.farm_id, start_date__range=window) \
        .order_by('-created_at')
    guide = (cycle.variety_id and guides.filter(variety_id=cycle.variety_id).first()) or guides.first()
    if not guide:
        return 0
    keys = guide.steps.filter(is_completed=True).values_list('template_key', flat=True)
    return max((STEP_STAGE.get(k, 0) for k in keys), default=0)


def growth_stages() -> list:
    """All stages in order; load once and pass to stage_today() for many cycles."""
    return list(GrowthStage.objects.order_by('stage_no'))


def stage_today(cycle, stages=None, today=None):
    """The cycle's stage: by its age, or by the guide steps logged if those are further
    along. Only an active cycle moves on; a completed or abandoned one keeps the stage
    it was saved with."""
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
    logged = guide_stage_no(cycle)
    if logged and (not current or logged > current.stage_no):
        current = next((s for s in stages if s.stage_no == logged), current)
    return current or cycle.current_stage
