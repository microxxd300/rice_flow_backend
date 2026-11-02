from django.contrib import admin

from .models import ChangeLog, FarmerNotice


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display  = ['created_at', 'actor_name', 'actor_role', 'summary']
    list_filter   = ['actor_role', 'action']
    search_fields = ['actor_name', 'summary', 'target']

    # A record of what happened: read only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(FarmerNotice)
class FarmerNoticeAdmin(admin.ModelAdmin):
    list_display  = ['created_at', 'user', 'kind', 'title']
    list_filter   = ['kind']
