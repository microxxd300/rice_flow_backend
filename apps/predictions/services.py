"""
Yield prediction service — Linear Regression.

Training data, in order of preference:

1. Real harvests: the Davao del Norte Provincial Agriculture harvest reports
   (one row per barangay, season, ecosystem and seed class), read from the CSV at
   settings.YIELD_TRAINING_CSV. The CSV is not in git. In this data the signal is
   in seed type, ecosystem, season and location; soil and climate barely vary
   within a barangay and added nothing in testing, so this model uses
   seed type + ecosystem + season + municipality + barangay. Location names are
   target-encoded (each place's typical yield, fitted without leaking the row's
   own yield). It is tested on the newest season after training on the earlier ones.
2. Real YieldRecord rows from the app once >= 30 exist.
3. A synthetic dataset whose relationships follow documented rice agronomy
   (pH optimum around 6.2, stress above 33 °C, drought below ~1400 mm,
   waterlogging above ~2600 mm), with engineered features for those non-linear
   effects. Validation: 5-fold CV on the training split plus held-out R², MAE, RMSE.
"""
import os
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from django.conf import settings

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import KFold, train_test_split, cross_val_score
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

MODELS_DIR: Path = settings.MODELS_DIR

RAW_FEATURES = [
    'area_ha', 'soil_ph', 'organic_matter', 'avg_temperature',
    'seasonal_rainfall', 'humidity', 'elevation_m',
    'flood_risk_enc',   # low=0, moderate=1, high=2
    'ecosystem_enc',    # lowland=0, upland=1
    'maturity_days', 'variety_avg_yield',
]
ENGINEERED_FEATURES = [
    'ph_stress',      # squared distance from the pH 6.2 optimum
    'heat_stress',    # degrees above 33 °C (0 below)
    'rain_deficit',   # 1000-mm units below 1400 mm (drought)
    'rain_excess',    # 1000-mm units above 2600 mm (waterlogging)
    'flood_x_rain',   # flood-prone farms suffer more from excess rain
    'ph_x_om',        # pH × organic matter interaction (nutrient availability)
]
FEATURE_NAMES = RAW_FEATURES + ENGINEERED_FEATURES

FLOOD_MAP = {'low': 0, 'moderate': 1, 'high': 2}
ECO_MAP   = {'lowland': 0, 'irrigated_lowland': 0, 'rainfed_lowland': 0,
             'upland': 1, 'highland': 1}

PH_OPTIMUM     = 6.2
HEAT_THRESHOLD = 33.0    # °C — spikelet sterility risk above this at flowering
RAIN_LOW       = 1400.0  # mm — below this the crop is water-limited
RAIN_HIGH      = 2600.0  # mm — above this waterlogging/flood losses grow


def encode_features(raw: dict) -> np.ndarray:
    """Map a request payload to the 11 raw feature columns (1 row)."""
    return np.array([[
        float(raw.get('area_ha', 1.0)),
        float(raw.get('soil_ph', 6.0)),
        float(raw.get('organic_matter', 2.0)),
        float(raw.get('avg_temperature', 28.0)),
        float(raw.get('seasonal_rainfall', 2000)),
        float(raw.get('humidity', 75)),
        float(raw.get('elevation_m', 50)),
        FLOOD_MAP.get(str(raw.get('flood_risk', 'low')).lower(), 0),
        ECO_MAP.get(str(raw.get('ecosystem', 'lowland')).lower(), 0),
        float(raw.get('maturity_days', 113)),
        float(raw.get('variety_avg_yield', 5.0)),
    ]])


def engineer_features(X_raw: np.ndarray) -> np.ndarray:
    """
    Append the engineered agronomic columns to a (n × 11) raw matrix.
    Must stay identical between training and prediction.
    """
    ph        = X_raw[:, 1]
    om        = X_raw[:, 2]
    temp      = X_raw[:, 3]
    rain      = X_raw[:, 4]
    flood_enc = X_raw[:, 7]

    ph_stress    = (ph - PH_OPTIMUM) ** 2
    heat_stress  = np.maximum(0.0, temp - HEAT_THRESHOLD)
    rain_deficit = np.maximum(0.0, RAIN_LOW - rain) / 1000.0
    rain_excess  = np.maximum(0.0, rain - RAIN_HIGH) / 1000.0
    flood_x_rain = flood_enc * rain_excess
    ph_x_om      = ph * om

    return np.column_stack([
        X_raw, ph_stress, heat_stress, rain_deficit, rain_excess,
        flood_x_rain, ph_x_om,
    ])


# ── Real-harvest model (DA harvest reports) ──────────────────────────────────

REAL_CATEGORICAL = ['ecosystem', 'season', 'seed_type']
REAL_LOCATION    = ['municipality', 'barangay']
REAL_COLUMNS     = REAL_CATEGORICAL + REAL_LOCATION
PANABO           = 'city of panabo'   # every RiceFlow farm is inside Panabo City
REAL_ECOSYSTEM   = {
    'irrigated': 'irrigated', 'irrigated_lowland': 'irrigated', 'lowland': 'irrigated',
    'rainfed_lowland': 'rainfed_lowland', 'rainfed': 'rainfed_lowland',
    'upland': 'upland', 'highland': 'upland',
}


def _place(name) -> str:
    """Case- and spacing-insensitive place name, so 'Datu Abdul  Dadia' matches."""
    return ' '.join(str(name or '').lower().split())


def seed_type_for(variety) -> str:
    """'Hybrid' for hybrid varieties (Mestizo line, NSIC codes ending in H), else 'Inbred'."""
    name = f'{getattr(variety, "common_name", "")} {getattr(variety, "nsic_code", "")}'.lower()
    code = str(getattr(variety, 'nsic_code', '')).strip().upper()
    return 'Hybrid' if 'mestizo' in name or 'hybrid' in name or code.endswith('H') else 'Inbred'


def real_features(raw: dict) -> pd.DataFrame:
    """Map a prediction request to the real-harvest model's columns (1 row)."""
    from apps.environmental.services.openmeteo import current_season

    season = str(raw.get('season') or '').strip().lower()
    if season not in ('wet', 'ws', 'dry', 'ds'):
        season = current_season()             # the season being planted now
    return pd.DataFrame([{
        'ecosystem':    REAL_ECOSYSTEM.get(str(raw.get('ecosystem') or '').lower(), 'irrigated'),
        'season':       'WS' if season in ('wet', 'ws') else 'DS',
        'seed_type':    'Hybrid' if str(raw.get('seed_type') or '').lower().startswith('hyb') else 'Inbred',
        'municipality': _place(raw.get('municipality') or PANABO),
        'barangay':     _place(raw.get('barangay')),
    }])


def _load_real_rows(csv_path: str):
    """The harvest-report CSV → (features, yield t/ha, season label, season order)."""
    df = pd.read_csv(csv_path)
    missing = set(REAL_COLUMNS + ['harvest_year', 'yield_t_ha']) - set(df.columns)
    if missing:
        raise ValueError(f'{csv_path} is missing columns: {", ".join(sorted(missing))}')
    df = df.dropna(subset=REAL_COLUMNS + ['harvest_year', 'yield_t_ha'])

    X = pd.DataFrame({
        'ecosystem':    df['ecosystem'].map(lambda e: REAL_ECOSYSTEM.get(str(e).lower(), 'irrigated')),
        'season':       df['season'].str.upper().str.strip(),
        'seed_type':    df['seed_type'].map(lambda s: 'Hybrid' if str(s).lower().startswith('hyb') else 'Inbred'),
        'municipality': df['municipality'].map(_place),
        'barangay':     df['barangay'].map(_place),
    }).reset_index(drop=True)
    y = df['yield_t_ha'].astype(float).to_numpy()
    years = df['harvest_year'].astype(int).to_numpy()
    label = np.array([f'{"Wet" if s == "WS" else "Dry"} {yr}' for s, yr in zip(X['season'], years)])
    # A wet season (May–Oct) ends after the dry season (Nov–Apr) of the same harvest year
    order = years * 2 + (X['season'] == 'WS').to_numpy()
    return X, y, label, order


def _real_pipeline() -> Pipeline:
    prep = ColumnTransformer([
        ('cat', OneHotEncoder(handle_unknown='ignore'), REAL_CATEGORICAL),
        # Cross-fitted: each row's place encoding comes from the other folds
        ('loc', TargetEncoder(target_type='continuous', cv=KFold(5, shuffle=True, random_state=42)),
         REAL_LOCATION),
    ])
    return Pipeline([('prep', prep), ('model', LinearRegression())])


def _train_real(csv_path: str) -> dict:
    X, y, label, order = _load_real_rows(csv_path)
    if len(np.unique(order)) < 2:
        raise ValueError('The harvest data needs at least two seasons to test on a new one.')

    # Headline test: train on the earlier seasons, predict the newest one
    newest = order == order.max()
    pipe = _real_pipeline().fit(X[~newest], y[~newest])
    pred = pipe.predict(X[newest])
    r2   = float(r2_score(y[newest], pred))
    mae  = float(mean_absolute_error(y[newest], pred))
    rmse = float(np.sqrt(mean_squared_error(y[newest], pred)))

    # Stability: predict each season from a model trained on all the others
    pooled = np.zeros(len(y))
    for season in np.unique(order):
        held = order == season
        pooled[held] = _real_pipeline().fit(X[~held], y[~held]).predict(X[held])
    loso_r2, loso_mae = float(r2_score(y, pooled)), float(mean_absolute_error(y, pooled))

    # Serve the model fitted on every season
    final = _real_pipeline().fit(X, y)
    path = MODELS_DIR / 'yield_linear.pkl'
    joblib.dump({'kind': 'real', 'pipeline': final}, path)

    return {
        'model_type':       'linear',
        'r2_score':         round(r2, 4),
        'mae':              round(mae, 4),
        'rmse':             round(rmse, 4),
        'training_samples': int((~newest).sum()),
        'model_file':       str(path),
        'is_active':        True,
        'notes':            (
            f'Trained on DA Davao del Norte harvest reports ({len(y)} rows, '
            f'{len(np.unique(order))} seasons, {X["barangay"].nunique()} barangays). '
            f'Inputs: seed type, ecosystem, season, municipality, barangay. '
            f'Test = {label[newest][0]} after training on earlier seasons. '
            f'Leave-one-season-out R2 = {loso_r2:.4f}, MAE = {loso_mae:.4f} t/ha. '
            f'Served model is refitted on all seasons.'
        ),
    }


def _generate_training_data(n_samples: int = 5000) -> tuple:
    """
    Synthetic dataset following documented rice-agronomy relationships.
    Used until enough real YieldRecords accumulate. Ranges are wide enough
    (drought through waterlogging, mild through hot) that the model learns
    the stress responses, not just the comfortable middle.
    """
    rng = np.random.default_rng(42)

    area_ha        = rng.uniform(0.5, 5.0,   n_samples)
    soil_ph        = rng.uniform(4.5, 8.0,   n_samples)
    organic_matter = rng.uniform(0.5, 4.0,   n_samples)
    avg_temp       = rng.uniform(24, 36,     n_samples)
    rainfall       = rng.uniform(800, 3500,  n_samples)
    humidity       = rng.uniform(60, 90,     n_samples)
    elevation_m    = rng.uniform(0, 600,     n_samples)
    flood_risk_enc = rng.integers(0, 3,      n_samples).astype(float)
    ecosystem_enc  = rng.integers(0, 2,      n_samples).astype(float)
    maturity_days  = rng.uniform(100, 130,   n_samples)
    variety_avg_y  = rng.uniform(4.0, 7.5,   n_samples)

    ph_stress    = (soil_ph - PH_OPTIMUM) ** 2
    heat_stress  = np.maximum(0.0, avg_temp - HEAT_THRESHOLD)
    rain_deficit = np.maximum(0.0, RAIN_LOW - rainfall) / 1000.0
    rain_excess  = np.maximum(0.0, rainfall - RAIN_HIGH) / 1000.0

    yield_t_ha = (
        variety_avg_y * 0.55                          # varietal potential
        + 1.2 * np.exp(-ph_stress / 0.9)              # pH sweet spot peaks at 6.2
        + 0.22 * organic_matter                       # fertility
        - 1.5 * rain_deficit                          # drought loss
        - 0.5 * rain_excess                           # waterlogging loss
        - 0.35 * flood_risk_enc * rain_excess         # worse on flood-prone land
        - 0.10 * heat_stress ** 1.5                   # non-linear heat sterility
        + 0.20 * (1 - ecosystem_enc)                  # lowland advantage
        - 0.15 * flood_risk_enc                       # baseline flood exposure
        - elevation_m / 2500.0                        # cooler/steeper marginal loss
        + rng.normal(0, 0.35, n_samples)              # field noise
    )
    yield_t_ha = np.clip(yield_t_ha, 1.5, 9.5)

    X = np.column_stack([
        area_ha, soil_ph, organic_matter, avg_temp,
        rainfall, humidity, elevation_m,
        flood_risk_enc, ecosystem_enc,
        maturity_days, variety_avg_y,
    ])
    return X, yield_t_ha


def _get_real_training_data():
    """Pull actual YieldRecord rows if there are enough of them."""
    from apps.progress.models import YieldRecord
    from apps.environmental.models import EnvironmentalScan

    rows = (YieldRecord.objects
            .select_related('farm_cycle__farm', 'farm_cycle__variety')
            .filter(net_yield_kg__gt=0))

    X_rows, y_rows = [], []
    for yr in rows:
        cycle = yr.farm_cycle
        farm  = cycle.farm
        scan  = EnvironmentalScan.objects.filter(farm=farm).order_by('-id').first()
        if not scan:
            continue
        area = float(farm.area_ha or 1.0) if hasattr(farm, 'area_ha') else float(getattr(farm, 'area_hectares', 1.0) or 1.0)
        y_t_ha = (yr.net_yield_kg / 1000) / max(area, 0.1)
        X_rows.append([
            area,
            float(scan.soil_ph),
            float(scan.organic_matter),
            float(scan.avg_temperature),
            float(getattr(scan, 'seasonal_rainfall_mm', None) or getattr(scan, 'seasonal_rainfall', 0) or 0),
            float(getattr(scan, 'humidity_pct', None) or getattr(scan, 'humidity', 0) or 0),
            float(scan.elevation_m),
            FLOOD_MAP.get(str(scan.flood_risk or 'low').lower(), 0),
            ECO_MAP.get(str(farm.ecosystem or 'lowland').lower(), 0),
            float(cycle.variety.maturity_days),
            float(cycle.variety.avg_yield_t_ha),
        ])
        y_rows.append(y_t_ha)

    if len(X_rows) < 30:
        return None, None
    return np.array(X_rows), np.array(y_rows)


def train_all_models(csv_path: str | None = None):
    """
    Train the Linear Regression yield model.

    Uses the harvest-report CSV (csv_path, else settings.YIELD_TRAINING_CSV) when
    it exists; an explicit csv_path that doesn't exist raises FileNotFoundError.
    Returns a single-item list (kept as a list so callers that iterate results
    keep working) with the test metrics; validation details go into notes.
    """
    if csv_path and not os.path.exists(csv_path):
        raise FileNotFoundError(csv_path)
    csv_path = csv_path or getattr(settings, 'YIELD_TRAINING_CSV', '')
    if csv_path and os.path.exists(csv_path):
        return [_train_real(csv_path)]

    X_real, y_real = _get_real_training_data()
    if X_real is not None:
        X_raw, y = X_real, y_real
        source = 'real'
    else:
        X_raw, y = _generate_training_data()
        source = 'synthetic'

    X = engineer_features(X_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    pipe = Pipeline([('scaler', StandardScaler()), ('model', LinearRegression())])

    # 5-fold CV on the training split → a stability estimate, not one lucky split
    cv_scores = cross_val_score(pipe, X_train, y_train, cv=5, scoring='r2')
    cv_mean, cv_std = float(cv_scores.mean()), float(cv_scores.std())

    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    r2   = float(r2_score(y_test, y_pred))
    mae  = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    path = MODELS_DIR / 'yield_linear.pkl'
    joblib.dump(pipe, path)

    return [{
        'model_type':       'linear',
        'r2_score':         round(r2,   4),
        'mae':              round(mae,  4),
        'rmse':             round(rmse, 4),
        'training_samples': len(X_train),
        'model_file':       str(path),
        'is_active':        True,
        'notes':            (
            f'Trained on {source} data ({len(X)} samples, '
            f'{len(FEATURE_NAMES)} features incl. engineered agronomy). '
            f'5-fold CV R2 = {cv_mean:.4f} ± {cv_std:.4f}.'
        ),
    }]


def predict_yield(features: dict) -> dict:
    """
    Run prediction using the active model. Returns predicted yield + which
    model produced it. Falls back to a simple heuristic if nothing is trained.
    """
    from apps.predictions.models import YieldPredictionModel

    def _heuristic(reason: str) -> dict:
        base = float(features.get('variety_avg_yield', 5.0))
        return {'predicted_yield_t_ha': round(base * 0.85, 2),
                'model_used': 'heuristic', 'r2_score': None, 'note': reason}

    active = YieldPredictionModel.objects.filter(is_active=True).first()
    if not active or not os.path.exists(active.model_file):
        return _heuristic('no trained model available')

    try:
        pipe = joblib.load(active.model_file)
    except Exception as exc:                       # pickle from another sklearn build
        print(f'[PREDICT] could not load {active.model_file}: {exc}', flush=True)
        return _heuristic('saved model could not be loaded')

    # Real-harvest model: its own inputs (seed type, ecosystem, season, location)
    if isinstance(pipe, dict) and pipe.get('kind') == 'real':
        try:
            pred = float(pipe['pipeline'].predict(real_features(features))[0])
        except Exception as exc:
            print(f'[PREDICT] prediction failed: {exc}', flush=True)
            return _heuristic('prediction failed')
        return {
            'predicted_yield_t_ha': round(max(1.0, min(pred, 12.0)), 2),
            'model_used':           active.get_model_type_display(),
            'r2_score':             active.r2_score,
        }

    X = engineer_features(encode_features(features))

    # A model saved before the current feature set was introduced expects a
    # different input width. Serving a heuristic is honest; silently reshaping
    # would invent a number, and retraining is a deliberate action — not
    # something a prediction request should trigger on its own.
    expected = getattr(pipe, 'n_features_in_', None)
    if expected is not None and int(expected) != X.shape[1]:
        print(
            f'[PREDICT] stale model artifact: expects {expected} features, '
            f'current feature set has {X.shape[1]} — retrain to use it.',
            flush=True,
        )
        return _heuristic(f'saved model is out of date ({expected} vs {X.shape[1]} features)')

    try:
        pred = float(pipe.predict(X)[0])
    except Exception as exc:
        print(f'[PREDICT] prediction failed: {exc}', flush=True)
        return _heuristic('prediction failed')

    pred = max(1.0, min(pred, 12.0))

    return {
        'predicted_yield_t_ha': round(pred, 2),
        'model_used':           active.get_model_type_display(),
        'r2_score':             active.r2_score,
    }
