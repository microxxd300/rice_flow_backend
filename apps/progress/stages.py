"""The growth stage a crop is in today: one rule for the app, the admin and the AI.

The planting guide decides. The stage is the furthest step the farmer has logged, and the
crop's age only moves it through stages that have no guide step (Booting, Grain Filling),
never past the next step still to log. A crop not sown yet has no stage, and a harvested
crop is at the last one. With no guide, the stage comes from the age alone.
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


def _crop_guide(cycle):
    """The guide for this crop (sown within a month of it), never the last crop's finished one."""
    window = (cycle.planting_date - timedelta(days=30), cycle.planting_date + timedelta(days=30))
    guides = PlantingGuide.objects.filter(farm_id=cycle.farm_id, start_date__range=window) \
        .order_by('-created_at')
    return (cycle.variety_id and guides.filter(variety_id=cycle.variety_id).first()) or guides.first()


# The admin's five Farm Cycles groups, decided here so every screen counts a crop the same way
STAGE_GROUPS = (
    ('land_prep',    'Land Prep'),      # not sown yet: the field is being prepared
    ('planting',     'Planting'),       # germination, seedling, transplanting
    ('vegetative',   'Vegetative'),     # tillering, stem elongation
    ('reproductive', 'Reproductive'),   # booting, heading and flowering, grain filling
    ('harvesting',   'Harvesting'),     # ripening, harvest, after harvest
)
GROUP_LABEL = dict(STAGE_GROUPS)
_GROUP_BY_STAGE_NO = {1: 'planting', 2: 'planting', 3: 'vegetative', 4: 'vegetative',
                      5: 'reproductive', 6: 'reproductive', 7: 'reproductive',
                      8: 'harvesting', 9: 'harvesting', 10: 'harvesting'}


def stage_group(cycle, stage) -> str | None:
    """The crop's group from its stage today (stage_today): an active crop not sown yet is in
    Land Prep. None for a crop that is neither growing nor planned."""
    if stage is None:
        return 'land_prep' if cycle.status == 'active' else None
    return _GROUP_BY_STAGE_NO.get(stage.stage_no)


def growth_stages() -> list:
    """All stages in order; load once and pass to stage_today() for many cycles."""
    return list(GrowthStage.objects.order_by('stage_no'))


def _stage_at(stages, stage_no):
    """The stage with this number, or the nearest one before it."""
    reached = [s for s in stages if s.stage_no <= stage_no]
    return reached[-1] if reached else None


def age_stage(cycle, stages=None, today=None):
    """The stage by days since sowing alone: None before the sowing day. The app uses it to
    ask about the harvest even when the farmer stopped logging."""
    if not cycle.planting_date:
        return None
    day = ((today or timezone.localdate()) - cycle.planting_date).days
    if day < 0:
        return None
    stages = growth_stages() if stages is None else stages
    start = 'days_min_upland' if cycle.farm.ecosystem == 'upland' else 'days_min_paddy'
    current = None
    for stage in stages:     # the last stage that has started by this day (start days only go up)
        if getattr(stage, start) <= day:
            current = stage
    return current


def stage_today(cycle, stages=None, today=None):
    """The cycle's stage today (see the top of this file). None for a crop not sown yet."""
    stages = growth_stages() if stages is None else stages
    if cycle.status == 'completed':
        return stages[-1] if stages else cycle.current_stage
    if cycle.status != 'active' or not cycle.planting_date:
        return cycle.current_stage
    by_age = age_stage(cycle, stages, today)
    if by_age is None:
        return None
    guide = _crop_guide(cycle)
    rows = [(STEP_STAGE.get(key, 0), done) for key, done in
            guide.steps.values_list('template_key', 'is_completed')] if guide else []
    if not any(no for no, _ in rows):          # no guide, or one from before the PalayCheck steps
        return by_age
    logged = max((no for no, done in rows if done), default=0)
    if logged == 0 and any(no == 1 for no, _ in rows):   # the sowing step is still open
        return None
    reached = max(1, logged)
    ahead = [no for no, done in rows if not done and no > reached]
    limit = min(ahead) - 1 if ahead else by_age.stage_no
    return _stage_at(stages, max(reached, min(by_age.stage_no, limit)))
