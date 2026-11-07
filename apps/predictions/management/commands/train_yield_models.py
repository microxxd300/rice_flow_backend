"""
python manage.py train_yield_models [--csv PATH]

Trains the Linear Regression yield model. Data, in order of preference: the DA
harvest-report CSV (--csv, else the YIELD_TRAINING_CSV setting), real
YieldRecords when >= 30 exist, otherwise the agronomy-calibrated synthetic
dataset. Reports test R2/MAE/RMSE, with validation details in notes. Safe to
re-run anytime: the new model is used from then on, and older ones are kept.
"""
from django.core.management.base import BaseCommand, CommandError
from apps.predictions.history import save_training
from apps.predictions.services import train_all_models


class Command(BaseCommand):
    help = 'Train the Linear Regression yield prediction model'

    def add_arguments(self, parser):
        parser.add_argument('--csv', help='Harvest-report training CSV (overrides YIELD_TRAINING_CSV)')

    def handle(self, *args, **options):
        self.stdout.write('Training yield prediction models...')

        try:
            results = train_all_models(options.get('csv'))
        except (FileNotFoundError, ValueError) as e:
            raise CommandError(f'Could not train: {e}')
        save_training(results)

        for r in results:
            active_label = ' << BEST' if r['is_active'] else ''
            self.stdout.write(
                f"  {r['model_type']:8s}  "
                f"R²={r['r2_score']:.4f}  "
                f"MAE={r['mae']:.4f}  "
                f"RMSE={r['rmse']:.4f}"
                f"{active_label}"
            )
            self.stdout.write(f"  {r['notes']}")

        best = max(results, key=lambda x: x['r2_score'])
        self.stdout.write(self.style.SUCCESS(
            f'\nBest model: {best["model_type"]} '
            f'(R²={best["r2_score"]:.4f})'
        ))
