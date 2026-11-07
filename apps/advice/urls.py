from django.urls import path

from .views import ExplainView, MatchView, ProblemDetailView, ProblemListView

urlpatterns = [
    path('problems/',            ProblemListView.as_view(),   name='advice-problems'),
    path('problems/<str:key>/',  ProblemDetailView.as_view(), name='advice-problem'),
    path('match/',               MatchView.as_view(),         name='advice-match'),
    path('explain/',             ExplainView.as_view(),       name='advice-explain'),
]
