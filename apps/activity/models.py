from django.conf import settings
from django.db import models


class ChangeLog(models.Model):
    """One change made from the admin website: who made it, what changed, and when."""
    actor      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='+')
    # Kept as text so the entry still reads correctly if the account changes later
    actor_name = models.CharField(max_length=150)
    actor_role = models.CharField(max_length=20)     # 'admin' or 'validator'
    action     = models.CharField(max_length=40)     # e.g. 'variety.updated'
    target     = models.CharField(max_length=200, blank=True)
    summary    = models.CharField(max_length=300)
    changes    = models.JSONField(default=dict, blank=True)   # {"field": [old, new]}
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.actor_name}: {self.summary}'


class FarmerNotice(models.Model):
    """A message for one farmer about something the admin changed. The app pulls
    these when it opens and shows them in the bell; `kind` and `params` let it
    word the message in the farmer's language."""
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='notices')
    kind       = models.CharField(max_length=30)     # farm_removed, cycle_removed, variety_updated, variety_retired
    params     = models.JSONField(default=dict, blank=True)
    title      = models.CharField(max_length=120)    # English fallback
    body       = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.user}: {self.title}'
