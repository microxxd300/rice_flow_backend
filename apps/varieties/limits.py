"""
What a rice variety's numbers can be. These feed the RSI score, the yield model and the
farmers' harvest dates, so a slip (a blank saved as 0, average above maximum) must not get in.
Both the admin form and the CSV import use this.
"""
from django.utils import timezone

MAX_YIELD_T_HA = 20
MIN_MATURITY_DAYS, MAX_MATURITY_DAYS = 60, 200
OLDEST_RELEASE_YEAR = 1960


def variety_problems(values):
    """{field: message} for the values given; a field left out or empty is not checked."""
    found = {}

    def given(field):
        return values.get(field) not in (None, '')

    if given('maturity_days') and not MIN_MATURITY_DAYS <= values['maturity_days'] <= MAX_MATURITY_DAYS:
        found['maturity_days'] = f'Maturity must be {MIN_MATURITY_DAYS} to {MAX_MATURITY_DAYS} days.'
    for field, name in (('avg_yield_t_ha', 'Average yield'), ('max_yield_t_ha', 'Maximum yield')):
        if given(field) and not 0 < values[field] <= MAX_YIELD_T_HA:
            found[field] = f'{name} must be above 0 and at most {MAX_YIELD_T_HA} t/ha.'
    if given('avg_yield_t_ha') and given('max_yield_t_ha') and not found \
            and values['max_yield_t_ha'] < values['avg_yield_t_ha']:
        found['max_yield_t_ha'] = 'Maximum yield cannot be below the average yield.'
    if given('optimal_temp_min') and given('optimal_temp_max') \
            and values['optimal_temp_min'] >= values['optimal_temp_max']:
        found['optimal_temp_max'] = 'Optimal temperature max must be above the min.'
    if given('optimal_rainfall_min') and values['optimal_rainfall_min'] < 0:
        found['optimal_rainfall_min'] = 'Rainfall cannot be negative.'
    if given('plant_height_cm') and values['plant_height_cm'] <= 0:
        found['plant_height_cm'] = 'Plant height must be above 0 cm.'
    if given('amylose_pct') and not 0 <= values['amylose_pct'] <= 100:
        found['amylose_pct'] = 'Amylose must be 0 to 100%.'
    if given('year_released') and not OLDEST_RELEASE_YEAR <= values['year_released'] <= timezone.localdate().year:
        found['year_released'] = f'Year released must be {OLDEST_RELEASE_YEAR} to this year.'
    return found
