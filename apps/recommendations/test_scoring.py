from datetime import datetime
from types import SimpleNamespace

from django.test import SimpleTestCase

from .scoring import S1, S2, S3, N, _score_stress_tolerance, calculate_rsi, planting_season


def variety(name, ecosystem='irrigated_lowland', season='Dry/Wet', sub='low', dro='low'):
    return SimpleNamespace(common_name=name, ecosystem=ecosystem, season=season,
                           submergence_tolerance=sub, drought_tolerance=dro, salinity_tolerance='low')


# Profiles from the variety dataset
TUBIGAN_18 = variety('Tubigan 18', sub='moderate')
TUBIGAN_7  = variety('Tubigan 7')
SAHOD_11   = variety('Sahod Ulan 11', 'rainfed_lowland', 'Wet', sub='high', dro='high')
SAHOD_1    = variety('Sahod Ulan 1',  'rainfed_lowland', 'Wet', sub='high', dro='moderate')
SAHOD_3    = variety('Sahod Ulan 3',  'rainfed_lowland', 'Wet', sub='moderate')
APO        = variety('Apo', 'upland', 'Dry', dro='high')

WET = datetime(2026, 7, 1)
DRY = datetime(2026, 2, 1)


def scan(when, flood='Low'):
    return SimpleNamespace(scanned_at=when, flood_risk=flood, soil_ph=6.2, soil_texture='clay loam',
                           organic_matter=2.5, drainage='poorly drained', avg_temperature=27,
                           seasonal_rainfall_mm=1200, humidity_pct=82, solar_radiation=17,
                           temp_at_flowering=27, elevation_m=45, slope_pct=1)


def fit(v, ecosystem, when, flood='Low'):
    return _score_stress_tolerance(v, scan(when, flood), ecosystem=ecosystem)


class SeasonFitTests(SimpleTestCase):
    """The variety factor: farm type, season, and the flood or drought that season brings."""

    def test_the_planting_season_follows_the_scan_date(self):
        self.assertEqual(planting_season(scan(WET)), 'wet')
        self.assertEqual(planting_season(scan(DRY)), 'dry')

    def test_wet_season_favours_submergence_tolerant_varieties(self):
        self.assertEqual(fit(TUBIGAN_18, 'irrigated_lowland', WET), S1)
        self.assertEqual(fit(TUBIGAN_7, 'irrigated_lowland', WET), S2)
        self.assertEqual(fit(SAHOD_1, 'rainfed_lowland', WET), S1)

    def test_dry_season_favours_drought_tolerant_varieties_on_rainfed_farms(self):
        self.assertGreater(fit(SAHOD_11, 'rainfed_lowland', DRY), fit(SAHOD_3, 'rainfed_lowland', DRY))
        self.assertEqual(fit(SAHOD_3, 'rainfed_lowland', DRY), S3)       # drought-prone, low tolerance

    def test_an_irrigated_farm_is_not_drought_prone_in_the_dry_season(self):
        self.assertEqual(fit(TUBIGAN_7, 'irrigated_lowland', DRY), S1)

    def test_a_variety_for_another_farm_type_ranks_below(self):
        self.assertEqual(fit(SAHOD_11, 'irrigated_lowland', WET), S3)
        self.assertEqual(fit(APO, 'irrigated_lowland', DRY), S3)
        self.assertLess(fit(SAHOD_11, 'irrigated_lowland', WET), fit(TUBIGAN_7, 'irrigated_lowland', WET))

    def test_a_variety_for_the_other_season_is_at_most_s2(self):
        self.assertEqual(fit(APO, 'upland', WET), S2)
        self.assertEqual(fit(APO, 'upland', DRY), S1)

    def test_a_high_flood_risk_rules_out_varieties_that_cannot_stand_it(self):
        self.assertEqual(fit(TUBIGAN_7, 'irrigated_lowland', DRY, flood='High'), N)

    def test_the_rsi_ranks_the_tolerant_variety_first(self):
        wet = scan(WET)
        ranked = sorted([TUBIGAN_7, SAHOD_11, TUBIGAN_18],
                        key=lambda v: calculate_rsi(v, wet, 'irrigated_lowland')['rsi_score'], reverse=True)
        self.assertEqual([v.common_name for v in ranked], ['Tubigan 18', 'Tubigan 7', 'Sahod Ulan 11'])
