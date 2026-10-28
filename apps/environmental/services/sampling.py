"""Soil sampling across a farm's area instead of at the single pin.

A farm stores one pin and its size (area_hectares), not its shape. To cover more than
the pinned spot, soil is read at the pin plus four points north, east, south and west
of it, inside a circle with the farm's area. The readings are averaged and their
spread is reported, so a farm whose soil differs a lot gets a warning to register its
different parts as separate farms.

Weather is not sampled this way: Open-Meteo's grid cells are larger than any farm, so
every point would return the same values.
"""
import math

from .soilgrids import _classify_texture

M_PER_DEG_LAT = 111_320
# SoilGrids has one value per 250 m pixel. Points closer than that usually fall in the
# same pixel and return the same data, so only one point per ~250 m cell is queried.
SOILGRIDS_CELL_DEG = 250 / M_PER_DEG_LAT
OFFSET_FRACTION = 0.7  # sample at 70% of the radius so points stay inside the farm

# Spread above which the farm's soil counts as varied
PH_SPREAD_LIMIT = 0.5
CLAY_SPREAD_LIMIT = 10.0  # percentage points

VARIES_MESSAGE = (
    'Soil differs across this farm. If parts of the land are different, register them '
    'as separate farms so each part gets its own recommendation.'
)

AVERAGED_FIELDS = {  # field -> decimals, matching get_soil_data()
    'ph': 1, 'clay_pct': 1, 'sand_pct': 1, 'silt_pct': 1,
    'organic_matter': 2, 'bulk_density': 2, 'nitrogen_ppm': 1, 'cec': 1,
}


def sample_points(lat: float, lon: float, area_hectares) -> list[tuple[float, float]]:
    """The pin plus up to 4 points around it, one per ~250 m SoilGrids cell."""
    points = [(lat, lon)]
    area_m2 = float(area_hectares or 0) * 10_000
    if area_m2 > 0:
        offset_m = OFFSET_FRACTION * math.sqrt(area_m2 / math.pi)
        dlat = offset_m / M_PER_DEG_LAT
        dlon = offset_m / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
        points += [(lat + dlat, lon), (lat, lon + dlon), (lat - dlat, lon), (lat, lon - dlon)]

    seen, unique = set(), []
    for p_lat, p_lon in points:
        cell = (round(p_lat / SOILGRIDS_CELL_DEG), round(p_lon / SOILGRIDS_CELL_DEG))
        if cell not in seen:
            seen.add(cell)
            unique.append((p_lat, p_lon))
    return unique


def combine_soil(samples: list[dict]) -> tuple[dict, dict]:
    """Average soil readings and describe how much they differ.

    Points where SoilGrids had no data (built-up areas, water) only carry default values,
    so they are left out of the average when at least one point has real data.

    Returns (soil, sampling): `soil` has the same keys as get_soil_data(); `sampling`
    says how many points were used, the pH and clay ranges, whether the soil varies, and
    whether the values are estimates because no point had SoilGrids data.
    """
    measured = [s for s in samples if s.get('from_soilgrids', True)]
    no_data = len(samples) - len(measured)
    samples = measured or samples
    soil = {
        field: round(sum(s[field] for s in samples) / len(samples), decimals)
        for field, decimals in AVERAGED_FIELDS.items()
    }
    # Texture and drainage follow from the averaged numbers, so they always agree with them
    soil['texture'] = _classify_texture(soil['clay_pct'], soil['sand_pct'])
    soil['drainage'] = 'poorly drained' if soil['clay_pct'] > 35 else 'moderately drained'

    ph = [s['ph'] for s in samples]
    clay = [s['clay_pct'] for s in samples]
    varies = (max(ph) - min(ph) > PH_SPREAD_LIMIT) or (max(clay) - min(clay) > CLAY_SPREAD_LIMIT)
    sampling = {
        'points': len(samples),
        'points_without_data': no_data,
        'estimated': not measured,
        'ph_range': [min(ph), max(ph)],
        'clay_pct_range': [min(clay), max(clay)],
        'varies': varies,
        'message': VARIES_MESSAGE if varies else '',
    }
    return soil, sampling
