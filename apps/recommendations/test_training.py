import io
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.recommendations.models import ClusterModel
from apps.varieties.models import RiceVariety


class TrainClusterModelsTests(TestCase):
    def test_command_trains_kmeans_and_records_it(self):
        for i, (eco, days, yld) in enumerate([('irrigated_lowland', 110, 5.0), ('irrigated_lowland', 120, 6.5),
                                               ('rainfed_lowland', 105, 4.2), ('rainfed_lowland', 125, 4.8),
                                               ('upland', 100, 3.5), ('upland', 115, 3.9)]):
            RiceVariety.objects.create(variety_id=f'V{i}', nsic_code=f'Rc{i}', common_name=f'Variety {i}', ecosystem=eco,
                                       season='both', maturity_days=days, avg_yield_t_ha=yld, max_yield_t_ha=yld + 2,
                                       optimal_temp_min=22, optimal_temp_max=32, optimal_rainfall_min=1000)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch('apps.recommendations.clustering.MODELS_DIR', Path(tmp)):
            call_command('train_cluster_models', stdout=io.StringIO())
            self.assertTrue((Path(tmp) / 'kmeans.pkl').exists())
        cm = ClusterModel.objects.get(name='kmeans')
        self.assertTrue(cm.is_active)
        self.assertGreaterEqual(cm.n_clusters, 2)
