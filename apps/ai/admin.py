from django.contrib import admin

from .models import KnowledgeSheet


@admin.register(KnowledgeSheet)
class KnowledgeSheetAdmin(admin.ModelAdmin):
    list_display    = ['__str__', 'updated_at', 'updated_by']
    readonly_fields = ['updated_at', 'updated_by']

    # One sheet only: it is created on first use and never deleted
    def has_add_permission(self, request):
        return not KnowledgeSheet.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
