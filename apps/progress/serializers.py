from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.farms.models import Farm
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
