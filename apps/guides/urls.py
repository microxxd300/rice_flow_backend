from django.urls import path
from .views import (
    GeneratePlantingGuideView, PlantingGuideListView,
    PlantingGuideDetailView, MarkStepCompleteView, SowingView,
)

urlpatterns = [
    path('',                              PlantingGuideListView.as_view(),       name='guide-list'),
    path('<int:pk>/',                     PlantingGuideDetailView.as_view(),     name='guide-detail'),
    path('<int:guide_id>/sowing/',        SowingView.as_view(),                  name='guide-sowing'),
    path('generate/<int:recommendation_id>/', GeneratePlantingGuideView.as_view(), name='generate-guide'),
    path('steps/<int:step_id>/complete/', MarkStepCompleteView.as_view(),       name='step-complete'),
]
