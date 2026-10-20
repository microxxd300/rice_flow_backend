from rest_framework import serializers
from .location_check import check_pin, location_flag
from .models import Farm


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Farm
        fields = '__all__'
        read_only_fields = ['user', 'location_flag', 'created_at', 'updated_at']

    # Warn, never block: the app asks the farmer before saving; here we only record
    # the result so admins can review pins kept despite a warning.
    def create(self, validated_data):
        validated_data['location_flag'] = self._flag(validated_data['latitude'], validated_data['longitude'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        lat = validated_data.get('latitude', instance.latitude)
        lon = validated_data.get('longitude', instance.longitude)
        if (lat, lon) != (instance.latitude, instance.longitude):
            validated_data['location_flag'] = self._flag(lat, lon)
            validated_data.setdefault('location_confirmed', False)
        return super().update(instance, validated_data)

    @staticmethod
    def _flag(lat, lon) -> str:
        return location_flag(check_pin(float(lat), float(lon)))


class AdminFarmSerializer(serializers.ModelSerializer):
    owner_name        = serializers.SerializerMethodField()
    owner_email       = serializers.SerializerMethodField()
    latest_flood_risk = serializers.SerializerMethodField()
    latest_yield_t_ha = serializers.SerializerMethodField()

    def get_owner_name(self, obj):
        first = (obj.user.first_name or '').strip()
        last  = (obj.user.last_name  or '').strip()
        # Collapse legacy duplicates where last_name was stored equal
        # to first_name (e.g. "Frank Frank" -> "Frank").
        if first and last and first.casefold() == last.casefold():
            last = ''
        full = f'{first} {last}'.strip()
        return full or obj.user.username

    def get_owner_email(self, obj):
        return obj.user.email

    def get_latest_flood_risk(self, obj):
        """Flood risk from the most recent environmental scan, if any.
        Uses AdminFarmListView's prefetched, pre-ordered scans when present."""
        scans = getattr(obj, 'prefetched_scans', None)
        if scans is not None:
            return scans[0].flood_risk if scans else ''
        scan = obj.scans.order_by('-scanned_at').first()
        return scan.flood_risk if scan else ''

    def get_latest_yield_t_ha(self, obj):
        """Most recent harvest yield in tonnes per hectare, if any.
        Uses prefetched cycles+yield_record when present, else queries."""
        cycles = getattr(obj, 'prefetched_cycles', None)
        if cycles is not None:
            records = [
                c.yield_record for c in cycles
                if getattr(c, 'yield_record', None) is not None
            ]
            if not records:
                return None
            latest = max(records, key=lambda r: (r.harvest_date is not None, r.harvest_date))
            return latest.yield_per_ha
        from apps.progress.models import YieldRecord
        record = (
            YieldRecord.objects
                .filter(farm_cycle__farm=obj)
                .order_by('-harvest_date')
                .first()
        )
        return record.yield_per_ha if record else None

    class Meta:
        model  = Farm
        fields = [
            'id', 'name', 'barangay', 'latitude', 'longitude',
            'area_hectares', 'ecosystem', 'elevation_m', 'is_active',
            'created_at', 'owner_name', 'owner_email',
            'latest_flood_risk', 'latest_yield_t_ha',
            'location_flag', 'location_confirmed',
        ]
