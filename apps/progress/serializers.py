from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.guides import sowing
from apps.guides.models import GuideStep
from apps.farms.models import Farm
from apps.varieties.models import GrowthStage
from .models import FarmCycle, ProgressLog, YieldRecord
from .stages import age_stage, stage_today


# Writable foreign keys only accept the requesting user's own records, so a farmer
# cannot attach data to another farmer's farm or cycle. Other users' ids fail the
# same way as ids that do not exist.
class OwnFarmField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return Farm.objects.filter(user=self.context['request'].user)


class OwnFarmCycleField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return FarmCycle.objects.filter(farm__user=self.context['request'].user)


class OwnGuideStepField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return GuideStep.objects.filter(guide__farm__user=self.context['request'].user)


class FarmCycleSerializer(serializers.ModelSerializer):
    farm = OwnFarmField()
    yield_per_ha = serializers.SerializerMethodField()
    variety_name = serializers.CharField(source='variety.common_name', read_only=True, default=None)
    # Today's stage (age or logged guide steps, see stages.py); current_stage is the saved one
    stage = serializers.SerializerMethodField()
    # By the crop's age alone: the app still asks about the harvest if the farmer stopped logging
    age_stage_no = serializers.SerializerMethodField()

    class Meta:
        model = FarmCycle
        fields = '__all__'

    def get_yield_per_ha(self, obj):
        yr = getattr(obj, 'yield_record', None)
        return yr.yield_per_ha if yr else None

    def get_age_stage_no(self, obj):
        stage = age_stage(obj)
        return stage.stage_no if stage else None

    def get_stage(self, obj):
        stage = stage_today(obj)
        return {'stage_no': stage.stage_no, 'name': stage.name} if stage else None

    def validate(self, attrs):
        # One active season per farm: the progress screens and the recommendation
        # step both assume a single active cycle
        farm = attrs.get('farm', getattr(self.instance, 'farm', None))
        status = attrs.get('status', getattr(self.instance, 'status', 'active'))
        if farm and status == 'active':
            others = FarmCycle.objects.filter(farm=farm, status='active')
            if self.instance:
                others = others.exclude(pk=self.instance.pk)
            if others.exists():
                raise serializers.ValidationError(
                    {'farm': 'This farm already has an active season. Complete it before starting another.'}
                )
        return attrs

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
    guide_step = OwnGuideStepField(required=False, allow_null=True)

    class Meta:
        model = ProgressLog
        fields = '__all__'
        read_only_fields = ['advice_tip']   # written by the advice explain endpoint

    def validate_problem_key(self, value):
        from apps.advice.knowledge import PROBLEMS
        if value and value not in PROBLEMS:
            raise serializers.ValidationError('Unknown problem.')
        return value

    def validate(self, attrs):
        step = attrs.get('guide_step')
        cycle = attrs.get('farm_cycle', getattr(self.instance, 'farm_cycle', None))
        if step and cycle and step.guide.farm_id != cycle.farm_id:
            raise serializers.ValidationError({'guide_step': "This step is not in this farm's planting guide."})
        # A step that comes after sowing cannot be done before the crop was sown
        log_date = attrs.get('log_date')
        if (step and log_date and (step.days_after_planting or 0) > 0 and sowing.is_sown(step.guide)
                and log_date < step.guide.start_date):
            raise serializers.ValidationError({'log_date': (
                f'This step comes after sowing. Pick {step.guide.start_date:%b} {step.guide.start_date.day} '
                'or a later day, or change the sowing day first.')})
        # A problem picked from the advice list also fills the problem type
        problem = attrs.get('problem_key')
        if problem and not attrs.get('issue_type'):
            from apps.advice.knowledge import PROBLEMS
            attrs['issue_type'] = PROBLEMS[problem]['category']
        return attrs

    def create(self, validated_data):
        log = super().create(validated_data)
        # Logging a guide step is how the farmer finishes it
        step = log.guide_step
        if step and not step.is_completed:
            step.is_completed = True
            step.completed_at = timezone.now()
            step.save(update_fields=['is_completed', 'completed_at'])
        if step and step.template_key in sowing.SOWING_KEYS:
            # The sowing log is the real sowing day: the whole plan moves to it
            sowing.confirm_sowing(step.guide, log.log_date, log=log)
        else:
            # A later step logged before sowing was: the app asks to confirm this day
            log.sowing_estimate = sowing.sowing_estimate(step, log.log_date)
        return log

    def to_representation(self, instance):
        data = super().to_representation(instance)
        estimate = getattr(instance, 'sowing_estimate', None)
        if estimate:
            data['sowing_estimate'] = estimate.isoformat()
        return data


MAX_YIELD_T_HA = 20


class YieldRecordSerializer(serializers.ModelSerializer):
    # Keeps the one-to-one check that the auto-generated field had
    farm_cycle = OwnFarmCycleField(validators=[UniqueValidator(queryset=YieldRecord.objects.all())])
    yield_per_ha = serializers.ReadOnlyField()

    class Meta:
        model = YieldRecord
        fields = '__all__'

    def validate(self, attrs):
        cycle = attrs.get('farm_cycle') or getattr(self.instance, 'farm_cycle', None)
        harvest = attrs.get('harvest_date') or getattr(self.instance, 'harvest_date', None)
        if cycle and harvest and harvest <= cycle.planting_date:
            raise serializers.ValidationError({'harvest_date': 'The harvest must be after the sowing day.'})
        # Every harvest trains the yield model, so a mistyped one must not get in
        net = attrs.get('net_yield_kg', getattr(self.instance, 'net_yield_kg', None))
        area = attrs.get('area_harvested_ha', getattr(self.instance, 'area_harvested_ha', None))
        if net and area and net / area / 1000 > MAX_YIELD_T_HA:
            raise serializers.ValidationError({'net_yield_kg': 'This yield is too high to be real. '
                                                               'Check the number of sacks and the area.'})
        return attrs
