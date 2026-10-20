---
name: riceflow-ml-predictions
description: Use when changing RiceFlow yield prediction (Linear Regression), variety clustering (K-Means), RSI suitability scoring, fit explanations, model training, or the farm land-data checks.
---

# RiceFlow ML predictions

## When to use

Use this skill for the machine-learning and scoring code behind recommendations and yield forecasts: `apps/predictions/services.py`, `apps/recommendations/clustering.py`, `apps/recommendations/scoring.py`, `apps/recommendations/fit_explanation.py`, and the Panabo land-data checks in `apps/farms/location_check.py`. The project uses only K-Means and Linear Regression.

## Workflow

1. Identify the entry point: the `train/`, `predict/`, `models/`, `generate/<scan_id>/`, or `set-model/<name>/` views, or the `train_yield_models` and `load_land_data` management commands.
2. Yield prediction: keep `RAW_FEATURES`, `ENGINEERED_FEATURES`, `encode_features`, and `engineer_features` identical between training and prediction. If the feature set changes, retrain; `predict_yield` falls back to the heuristic when a saved model has a different feature count.
3. Training data: `train_all_models` uses real `YieldRecord` rows once at least 30 exist, and the seeded synthetic agronomy dataset until then. Report which source a result came from.
4. Clustering: K-Means searches k = 2 to 8, keeps the best silhouette score, and uses `random_state=42` with `n_init=50`. The cluster label is supplementary metadata; the recommendation ranking comes from RSI in `scoring.py`.
5. Track the active model through `is_active`. `predict_yield` loads the newest active `YieldPredictionModel` (ordered by `-trained_at`), and `ClusterModel.save()` deactivates every other cluster model. Keep that behavior when changing how models are saved or switched.
6. Report metrics the way the code does: 5-fold cross-validation plus held-out R², MAE, and RMSE for regression; silhouette and Davies-Bouldin for clustering. `notebooks/model_training.ipynb` holds the training walkthrough and charts.
7. Test with fixed seeds and small inputs. Follow the existing `SimpleTestCase` tests in `apps/farms/tests.py`, and see [Python testing patterns](../python-testing-patterns/SKILL.md) for fixtures and mocking.

## Boundaries

- Trained models in `models/trained/`, `*.pkl`, `*.npz`, and `notebooks/artifacts/` are regenerable and gitignored. Rebuild them with the commands above; never commit them.
- Training endpoints are admin-only (`IsAdminUser`). Do not expose training to regular users.
- Keep agronomic constants (pH optimum 6.2, heat threshold 33 °C, rainfall 1400 to 2600 mm) in one place and document any change.
- API routes, serializers, and permissions belong to [RiceFlow API endpoints](../riceflow-api-endpoints/SKILL.md).

## Useful result

A useful change states which model or scorer changed, whether features stayed compatible with saved models, the metrics before and after when retraining, the data source (real or synthetic), and the tests run.
