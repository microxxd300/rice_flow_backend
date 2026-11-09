from django.urls import path
from .views import (
    GenerateRecommendationView, ReuseRecommendationView, TrainModelsView,
    SetActiveModelView, RecommendationHistoryView, SuitabilityRulesView,
)

urlpatterns = [
    path('generate/<int:scan_id>/',    GenerateRecommendationView.as_view(), name='generate-recommendation'),
    path('reuse/<int:farm_id>/',       ReuseRecommendationView.as_view(),    name='reuse-recommendation'),
    path('history/<int:farm_id>/',     RecommendationHistoryView.as_view(),  name='recommendation-history'),
    path('train/',                     TrainModelsView.as_view(),            name='train-models'),
    path('set-model/<str:model_name>/', SetActiveModelView.as_view(),        name='set-active-model'),
    path('rules/',                     SuitabilityRulesView.as_view(),       name='suitability-rules'),
]
