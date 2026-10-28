"""Train K-Means on the active rice varieties and record the result in ClusterModel."""
from apps.varieties.models import RiceVariety

from .clustering import train_all_models
from .models import ClusterModel

MIN_VARIETIES = 4


def train_and_record():
    """Fit K-Means (saves scaler.pkl / kmeans.pkl) and update the ClusterModel rows.

    Returns the saved ClusterModel objects. Raises ValueError with too few varieties.
    """
    varieties = list(RiceVariety.objects.filter(is_active=True))
    if len(varieties) < MIN_VARIETIES:
        raise ValueError(f'Need at least {MIN_VARIETIES} varieties to cluster.')

    results, _ = train_all_models(varieties)

    # Drop rows for algorithms we no longer train (e.g. legacy agglomerative/dbscan entries)
    ClusterModel.objects.exclude(name__in=list(results.keys())).delete()

    saved = []
    for name, res in results.items():
        cm, _ = ClusterModel.objects.update_or_create(
            name=name,
            defaults={
                'training_time_ms': res['training_time_ms'],
                'silhouette_score': res['silhouette'],
                'davies_bouldin':   res['davies_bouldin'],
                'n_clusters':       res['n_clusters'],
                # K-Means is the only model, so it is active immediately
                'is_active':        True,
            },
        )
        saved.append(cm)
    return saved
