from django.db import models


class YieldPredictionModel(models.Model):
    """One training run of the yield model. Old runs are kept (not deleted) so every saved
    prediction still points to the model that made it; only one run is active at a time."""
    MODEL_CHOICES = [
        ('linear', 'Linear Regression'),
    ]

    model_type       = models.CharField(max_length=20, choices=MODEL_CHOICES)
    r2_score         = models.FloatField(default=0)
    mae              = models.FloatField(default=0, verbose_name='MAE (t/ha)')
    rmse             = models.FloatField(default=0, verbose_name='RMSE (t/ha)')
    training_samples = models.IntegerField(default=0)
    # How many harvests recorded in RiceFlow the model had learned from: the automatic
    # retrain counts new harvests from here
    harvests_seen    = models.IntegerField(default=0)
    model_file       = models.CharField(max_length=200)
    is_active        = models.BooleanField(default=False)
    trained_at       = models.DateTimeField(auto_now_add=True)
    notes            = models.TextField(blank=True)

    class Meta:
        ordering = ['-trained_at', '-id']
        verbose_name = 'Yield Prediction Model'

    def __str__(self):
        return f'{self.get_model_type_display()} — R²={self.r2_score:.3f} ({self.trained_at:%Y-%m-%d})'


class YieldPrediction(models.Model):
    """The yield the model predicted for a crop before its harvest was recorded, kept so
    each harvest can be compared with what was predicted. One row per crop per model."""
    farm_cycle     = models.ForeignKey('progress.FarmCycle', on_delete=models.CASCADE,
                                       related_name='yield_predictions')
    # Empty when no trained model was available and a simple estimate was used
    model          = models.ForeignKey(YieldPredictionModel, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='predictions')
    predicted_t_ha = models.FloatField()
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return f'{self.predicted_t_ha} t/ha for {self.farm_cycle}'
