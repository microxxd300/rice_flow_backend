"""
Per-farm "why this variety fits your farm" text.

Built directly from the RSI factor_scores the engine already computes, so it is
truthful (it IS the real breakdown), instant, free, and different per user
because it reflects that farm's conditions. Generated once when the
recommendation is created and stored on RecommendationResult.fit_explanation.

Scores follow the RSI scale: 100=S1 (excellent), 75=S2 (good), 50=S3
(marginal), 25=N (poor).
"""

# Factor key -> farmer-friendly label
FRIENDLY = {
    'soil_ph':           'soil pH',
    'soil_texture':      'soil texture',
    'organic_matter':    'soil fertility',
    'drainage':          'drainage',
    'avg_temperature':   'temperature',
    'seasonal_rainfall': 'rainfall',
    'humidity':          'humidity',
    'solar_radiation':   'sunlight',
    'temp_at_flowering': 'flowering-time temperature',
    'elevation':         'elevation',
    'slope':             'land slope',
    'stress_tolerance':  'flood/drought tolerance',
}


def _join(items):
    """Human-friendly list join: a, b and c."""
    items = list(items)
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"


def build_fit_explanation(variety_name, rsi_score, suitability_class, factor_scores):
    """Return a short, truthful sentence describing how the variety fits THIS farm."""
    fs = factor_scores or {}
    strong = [FRIENDLY.get(k, k) for k, s in fs.items() if isinstance(s, (int, float)) and s >= 100]
    weak   = [FRIENDLY.get(k, k) for k, s in fs.items() if isinstance(s, (int, float)) and s <= 50]

    verdict = (suitability_class.split(' - ')[-1] if ' - ' in (suitability_class or '')
               else suitability_class or 'suitable')

    parts = [f"{variety_name} scores {round(rsi_score)}/100 for your farm — {verdict.lower()}."]
    if strong:
        parts.append(f"Strong match on {_join(strong[:3])}.")
    if weak:
        parts.append(f"Weaker on {_join(weak[:2])}, so watch those closely.")
    return ' '.join(parts)
