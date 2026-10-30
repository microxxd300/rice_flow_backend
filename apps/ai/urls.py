from django.urls import path
from .views import AIChatView, KnowledgeSheetView

urlpatterns = [
    path('chat/',      AIChatView.as_view(),         name='ai-chat'),
    path('knowledge/', KnowledgeSheetView.as_view(), name='ai-knowledge'),
]
