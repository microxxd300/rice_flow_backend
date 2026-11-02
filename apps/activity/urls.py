from django.urls import path
from .views import ChangeLogView, FarmerNoticeListView

urlpatterns = [
    path('changes/', ChangeLogView.as_view(),        name='activity-changes'),
    path('notices/', FarmerNoticeListView.as_view(), name='activity-notices'),
]
