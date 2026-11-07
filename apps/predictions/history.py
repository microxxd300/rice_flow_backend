"""
The yield model's training history and its automatic retraining.

Every training is kept as its own YieldPredictionModel row and model file, so saved
predictions keep pointing to the model that made them. One row is active at a time.

Automatic retraining: after AUTO_RETRAIN_EVERY new harvests are recorded in RiceFlow
(counted from the last training), the model retrains in the background on all the data.
The new model only becomes active if its error on the DA test season is not worse than
the active model's (within NOT_WORSE_TOLERANCE); otherwise it is kept, inactive, with a
note saying why, and the old model stays in use. Both outcomes go to the change log.
"""
import logging
import threading

from django.db import close_old_connections, transaction

from apps.activity.models import ChangeLog

from .models import YieldPredictionModel
from .services import app_harvest_rows, train_all_models

log = logging.getLogger(__name__)

AUTO_RETRAIN_EVERY  = 5      # new harvests recorded in RiceFlow before a retrain
NOT_WORSE_TOLERANCE = 0.02   # the new model's MAE may be at most 2% above the active one's

_training = threading.Lock()  # one training at a time


def save_training(results, *, auto=False):
    """Keep a training's results as new model rows (old ones are never deleted).

    A training someone asked for (admin button, command) becomes the active model.
    An automatic one becomes active only if it is not worse than the active model.
    Returns (the new model, whether it is now active)."""
    harvests = len(app_harvest_rows())
    current = YieldPredictionModel.objects.filter(is_active=True).first()
    new = None
    for r in results:
        new = YieldPredictionModel.objects.create(**{**r, 'is_active': False, 'harvests_seen': harvests})

    use_it = not auto or current is None or new.mae <= current.mae * (1 + NOT_WORSE_TOLERANCE)
    if use_it:
        YieldPredictionModel.objects.filter(is_active=True).update(is_active=False)
        new.is_active = True
        new.save(update_fields=['is_active'])
    else:
        new.notes = (f'Not used: its test error (MAE {new.mae:.4f} t/ha) is higher than the '
                     f'model in use (MAE {current.mae:.4f} t/ha). ' + new.notes)
        new.save(update_fields=['notes'])
    return new, use_it


def new_harvests_since_training() -> int:
    """Harvests recorded in RiceFlow since the last training (used or not), counted the
    way training counts them (typos and harvests without an area are left out)."""
    last = YieldPredictionModel.objects.order_by('-trained_at', '-id').first()
    return len(app_harvest_rows()) - (last.harvests_seen if last else 0)


def retrain_if_due():
    """Retrain when enough new harvests have come in. Only once a model has been
    trained the first time (by the admin), and never two trainings at once."""
    if not YieldPredictionModel.objects.exists():
        return None
    if not _training.acquire(blocking=False):
        return None
    try:
        new_count = new_harvests_since_training()
        if new_count < AUTO_RETRAIN_EVERY:
            return None
        new, used = save_training(train_all_models(), auto=True)
        summary = (f'retrained the yield model automatically after {new_count} new harvests '
                   + ('and started using it' if used else 'but kept the current model, which is more accurate'))
        ChangeLog.objects.create(
            actor=None, actor_name='RiceFlow', actor_role='system', action='model.auto_trained',
            target='Yield prediction model', summary=summary[:300],
            changes={'mae': [None, new.mae], 'r2_score': [None, new.r2_score], 'used': [None, used]},
        )
        return new
    except Exception:                       # a failed retrain must never affect the farmer
        log.exception('Automatic yield model retrain failed')
        return None
    finally:
        _training.release()


def _in_background(fn):
    def run():
        try:
            fn()
        finally:
            close_old_connections()
    threading.Thread(target=run, daemon=True).start()


def after_harvest_recorded():
    """Called when a harvest is saved: check for a retrain once the save has committed,
    in the background, so the farmer never waits for training."""
    transaction.on_commit(lambda: _in_background(retrain_if_due))
