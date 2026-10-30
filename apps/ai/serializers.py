from rest_framework import serializers

from .models import KnowledgeSheet


class KnowledgeSheetSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.email', read_only=True)

    class Meta:
        model  = KnowledgeSheet
        fields = ['content', 'updated_at', 'updated_by_name']
        read_only_fields = ['updated_at', 'updated_by_name']
