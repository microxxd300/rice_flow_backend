from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.environmental.models import EnvironmentalScan
from apps.farms.models import Farm
from apps.varieties.models import RiceVariety

from .clustering import preselect_varieties
from .models import ClusterModel, Recommendation

IRRIGATED, RAINFED, UPLAND = 'irrigated_lowland', 'rainfed_lowland', 'upland'


def variety(pk, ecosystem):
    return SimpleNamespace(id=pk, ecosystem=ecosystem)


def picked(varieties, clusters, ecosystem):
    return [v.id for v in preselect_varieties(varieties, clusters, ecosystem)]


class PreselectVarietiesTests(SimpleTestCase):
    def test_keeps_only_the_clusters_for_the_farm_type(self):
        varieties = [variety(1, IRRIGATED), variety(2, IRRIGATED), variety(3, IRRIGATED),
                     variety(4, RAINFED), variety(5, UPLAND)]
        clusters = {1: 0, 2: 0, 3: 0, 4: 1, 5: 2}
        self.assertEqual(picked(varieties, clusters, IRRIGATED), [1, 2, 3])

    def test_a_farm_type_split_over_two_clusters_keeps_both(self):
        varieties = [variety(1, IRRIGATED), variety(2, IRRIGATED), variety(3, IRRIGATED), variety(4, RAINFED)]
        clusters = {1: 0, 2: 0, 3: 3, 4: 1}
        self.assertEqual(picked(varieties, clusters, IRRIGATED), [1, 2, 3])

    def test_keeps_everything_when_too_few_would_remain(self):
        varieties = [variety(1, UPLAND), variety(2, UPLAND), variety(3, RAINFED), variety(4, IRRIGATED)]
        clusters = {1: 2, 2: 2, 3: 1, 4: 0}
        self.assertEqual(picked(varieties, clusters, UPLAND), [1, 2, 3, 4])

    def test_keeps_everything_when_no_variety_fits_the_farm_type(self):
        varieties = [variety(1, RAINFED), variety(2, RAINFED), variety(3, RAINFED)]
        clusters = {1: 0, 2: 0, 3: 0}
        self.assertEqual(picked(varieties, clusters, UPLAND), [1, 2, 3])


class GenerateRecommendationPreselectionTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username='grower', password='pass12345')
        farm = Farm.objects.create(user=user, name='Farm', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                   area_hectares=1, ecosystem=IRRIGATED)
        self.scan = EnvironmentalScan.objects.create(farm=farm)
        self.client = APIClient()
        self.client.force_authenticate(user)
        ClusterModel.objects.create(name='kmeans', training_time_ms=1, silhouette_score=0.6, davies_bouldin=0.5,
                                    n_clusters=2, is_active=True)

    def make(self, code, ecosystem):
        return RiceVariety.objects.create(variety_id=code, nsic_code=f'NSIC {code}', common_name=code,
                                          ecosystem=ecosystem, season='both', maturity_days=110,
                                          avg_yield_t_ha=5.0, max_yield_t_ha=8.0)

    def generate(self, clusters):
        with mock.patch('apps.recommendations.views.predict_cluster',
                        side_effect=lambda v, _name: clusters[v.variety_id]):
            res = self.client.post(reverse('generate-recommendation', args=[self.scan.id]))
        self.assertEqual(res.status_code, 201)
        return list(Recommendation.objects.latest('id').results.order_by('rank'))

    def test_only_the_farm_types_cluster_is_ranked(self):
        for code in ('I1', 'I2', 'I3'):
            self.make(code, IRRIGATED)
        self.make('R1', RAINFED)
        results = self.generate({'I1': 1, 'I2': 1, 'I3': 1, 'R1': 0})
        self.assertEqual(sorted(r.variety.variety_id for r in results), ['I1', 'I2', 'I3'])
        self.assertEqual({r.variety_cluster for r in results}, {1})

    def test_the_farmer_still_gets_three_when_the_cluster_is_small(self):
        self.make('I1', IRRIGATED)
        for code in ('R1', 'R2'):
            self.make(code, RAINFED)
        self.assertEqual(len(self.generate({'I1': 1, 'R1': 0, 'R2': 0})), 3)
