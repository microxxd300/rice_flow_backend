"""
python manage.py train_cluster_models

Trains K-Means on the active rice varieties (same as the admin "train" endpoint) and
records silhouette / Davies-Bouldin in ClusterModel. Safe to re-run anytime.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.recommendations.training import train_and_record


class Command(BaseCommand):
    help = 'Train the K-Means variety clustering model'

    def handle(self, *args, **options):
        try:
            saved = train_and_record()
        except ValueError as e:
            raise CommandError(str(e))
        for cm in saved:
            self.stdout.write(self.style.SUCCESS(
                f'{cm.name}: k={cm.n_clusters}  silhouette={cm.silhouette_score:.4f}  '
                f'Davies-Bouldin={cm.davies_bouldin:.4f}'
            ))
