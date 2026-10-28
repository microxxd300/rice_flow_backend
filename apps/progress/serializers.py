from datetime import timedelta

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.farms.models import Farm
from apps.varieties.models import GrowthStage
from .models import FarmCycle, ProgressLog, YieldRecord


# Writable foreign keys only accept the requesting user's own records, so a farmer
# cannot attach data to another farmer's farm or cycle. Other users' ids fail the
# same way as ids that do not exist.
class OwnFarmField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return Farm.objects.filter(user=self.context['request'].user)


class OwnFarmCycleField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return FarmCycle.objects.filter(farm__user=self.context['request'].user)


class FarmCycleSerializer(serializers.ModelSerializer):
    farm = OwnFarmField()
    yield_per_ha = serializers.SerializerMethodField()

    class Meta:
        model = FarmCycle
        fields = '__all__'

    def get_yield_per_ha(self, obj):
        yr = getattr(obj, 'yield_record', None)
        return yr.yield_per_ha if yr else None

    def create(self, validated_data):
        # Same defaults as the cycle the recommendation step creates, so a cycle started
        # from the app's progress screens is not left without a harvest date or stage
        variety, planted = validated_data.get('variety'), validated_data.get('planting_date')
        if not validated_data.get('expected_harvest_date') and variety and variety.maturity_days and planted:
            validated_data['expected_harvest_date'] = planted + timedelta(days=int(variety.maturity_days))
        if not validated_data.get('current_stage'):
            validated_data['current_stage'] = GrowthStage.objects.order_by('stage_no').first()
        return super().create(validated_data)


class ProgressLogSerializer(serializers.ModelSerializer):
    farm_cycle = OwnFarmCycleField()

    class Meta:
        model = ProgressLog
        fields = '__all__'


class YieldRecordSerializer(serializers.ModelSerializer):
    # Keeps the one-to-one check that the auto-generated field had
    farm_cycle = OwnFarmCycleField(validators=[UniqueValidator(queryset=YieldRecord.objects.all())])
    yield_per_ha = serializers.ReadOnlyField()

    class Meta:
        model = YieldRecord
        fields = '__all__'
