"""
Set every farm's barangay from its pin (barangays.py), and fill in a farmer's empty
barangay from their first farm. Shows the changes only; pass --apply to save them.

  python manage.py fix_farm_barangays            # report
  python manage.py fix_farm_barangays --apply    # save
"""
from django.core.management.base import BaseCommand

from apps.farms.barangays import barangay_at
from apps.farms.models import Farm


class Command(BaseCommand):
    help = "Set farm barangays from their pins (report only unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='save the changes')

    def handle(self, *args, **opts):
        farm_changes, users = [], {}
        for farm in Farm.objects.select_related('user').order_by('created_at'):
            found = barangay_at(float(farm.latitude), float(farm.longitude))
            if found and found != farm.barangay:
                farm_changes.append((farm, found))
            users.setdefault(farm.user_id, (farm.user, found or farm.barangay))   # first farm wins
        user_changes = [(u, b) for u, b in users.values() if not u.barangay and b]

        for farm, found in farm_changes:
            self.stdout.write(f'farm #{farm.id} "{farm.name}" ({farm.user.email}): '
                              f'{farm.barangay or "(empty)"} -> {found}')
        for user, b in user_changes:
            self.stdout.write(f'farmer {user.email}: (empty) -> {b}')

        if not opts['apply']:
            self.stdout.write(self.style.WARNING(
                f'{len(farm_changes)} farm(s) and {len(user_changes)} farmer(s) would change. '
                'Run again with --apply to save.'))
            return
        for farm, found in farm_changes:
            Farm.objects.filter(pk=farm.pk).update(barangay=found)
        for user, b in user_changes:
            user.barangay = b
            user.save(update_fields=['barangay'])
        self.stdout.write(self.style.SUCCESS(
            f'Saved {len(farm_changes)} farm(s) and {len(user_changes)} farmer(s).'))
