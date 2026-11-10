from rest_framework import serializers
from .limits import variety_problems
from .models import RiceVariety, GrowthStage, FertilizerSchedule, PestDisease


class RiceVarietySerializer(serializers.ModelSerializer):
    class Meta:
        model = RiceVariety
        fields = '__all__'

    def validate(self, attrs):
        # An edit may send a few fields: check them against the saved ones
        saved = {f: getattr(self.instance, f) for f in self.fields if hasattr(self.instance, f)}
        problems = variety_problems({**saved, **attrs})
        # An old value that is already off must not block fixing something else
        old_problems = variety_problems(saved)
        problems = {k: m for k, m in problems.items() if k not in old_problems or attrs.get(k, saved.get(k)) != saved.get(k)}

        # The CSV import finds a variety by its NSIC code, so two rows must not share one
        nsic = attrs.get('nsic_code')
        if nsic and nsic != saved.get('nsic_code'):
            same = RiceVariety.objects.filter(nsic_code__iexact=nsic)
            if self.instance:
                same = same.exclude(pk=self.instance.pk)
            if same.exists():
                problems['nsic_code'] = 'Another variety already has this NSIC code.'
        if problems:
            raise serializers.ValidationError(problems)
        return attrs


class GrowthStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrowthStage
        fields = '__all__'


class FertilizerScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FertilizerSchedule
        fields = '__all__'


class PestDiseaseSerializer(serializers.ModelSerializer):
    resistant_varieties = RiceVarietySerializer(many=True, read_only=True)

    class Meta:
        model = PestDisease
        fields = '__all__'
