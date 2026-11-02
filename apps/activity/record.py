"""
Helpers the admin views call after a change succeeds: log_change() writes the
change log, notify_*() leave a notice for the farmers it affects.
"""
from .models import ChangeLog, FarmerNotice


def role_of(user):
    if user.is_superuser:
        return 'admin'
    return 'validator' if user.is_staff else 'farmer'


def display_name(user):
    first = (user.first_name or '').strip()
    last  = (user.last_name or '').strip()
    if first and last and first.casefold() == last.casefold():
        last = ''
    return f'{first} {last}'.strip() or user.username or user.email


def diff(before, after):
    """{field: [old, new]} for every key whose value changed."""
    return {k: [before.get(k), after.get(k)] for k in after if before.get(k) != after.get(k)}


def field_list(changes):
    """"maturity days, avg yield t ha" from {"maturity_days": ..., "avg_yield_t_ha": ...}."""
    return ', '.join(k.replace('_', ' ') for k in changes)


def log_change(user, action, summary, target='', changes=None):
    return ChangeLog.objects.create(
        actor=user, actor_name=display_name(user), actor_role=role_of(user),
        action=action, target=target[:200], summary=summary[:300], changes=changes or {},
    )


def _notify(user, kind, params, title, body):
    FarmerNotice.objects.create(user=user, kind=kind, params=params, title=title, body=body)


def notify_farm_removed(farm):
    _notify(farm.user, 'farm_removed', {'farm': farm.name},
            'Farm removed',
            f'Your farm "{farm.name}" was removed by the RiceFlow admin.')


def notify_cycle_removed(cycle):
    farm = cycle.farm
    season = cycle.get_season_display()
    _notify(farm.user, 'cycle_removed', {'farm': farm.name, 'season': cycle.season, 'year': cycle.year},
            'Crop cycle removed',
            f'Your {season} {cycle.year} crop cycle on "{farm.name}" was removed by the RiceFlow admin.')


def notify_variety_planters(variety, kind):
    """Tell every farmer with an active cycle of this variety that it was updated or retired."""
    from apps.progress.models import FarmCycle
    users = {c.farm.user for c in FarmCycle.objects.filter(variety=variety, status='active')
                                                   .select_related('farm__user')}
    name = variety.common_name
    if kind == 'variety_updated':
        title, body = 'Variety details updated', (
            f'The details of {name}, the variety you planted, were updated. Open the guide to see them.')
    else:
        title, body = 'Variety no longer recommended', (
            f'{name}, the variety you planted, is no longer recommended for new seasons. '
            'Your current crop is not affected.')
    for user in users:
        _notify(user, kind, {'variety': name}, title, body)
