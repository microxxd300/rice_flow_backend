from django.contrib import admin
from django.contrib import messages
from .history import save_training
from .models import YieldPrediction, YieldPredictionModel
from .services import train_all_models


@admin.action(description='Train / Retrain all 3 regression models')
def retrain_models(modeladmin, request, queryset):
    try:
        results = train_all_models()
        save_training(results)
        best = max(results, key=lambda x: x['r2_score'])
        messages.success(
            request,
            f"Models trained. Best: {best['model_type']} "
            f"(R²={best['r2_score']:.4f}, MAE={best['mae']:.4f})"
        )
    except Exception as e:
        messages.error(request, f'Training failed: {e}')


@admin.register(YieldPredictionModel)
class YieldPredictionModelAdmin(admin.ModelAdmin):
    list_display  = ('model_type', 'r2_score', 'mae', 'rmse',
                     'training_samples', 'harvests_seen', 'is_active', 'trained_at')
    list_filter   = ('model_type', 'is_active')
    readonly_fields = ('r2_score', 'mae', 'rmse', 'training_samples',
                       'model_file', 'trained_at')
    actions       = [retrain_models]

    def has_add_permission(self, request):
        return False  # models are created only via training


@admin.register(YieldPrediction)
class YieldPredictionAdmin(admin.ModelAdmin):
    list_display  = ('farm_cycle', 'predicted_t_ha', 'model', 'updated_at')
    list_select_related = ('farm_cycle__farm', 'model')
    readonly_fields = ('farm_cycle', 'model', 'predicted_t_ha', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False  # saved by the app's prediction requests and harvest records
