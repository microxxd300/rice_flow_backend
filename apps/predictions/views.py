from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.accounts.permissions import IsSuperUser
from apps.activity.record import log_change

from apps.farms.models import Farm
from apps.progress.models import FarmCycle
from apps.varieties.models import RiceVariety

from .history import save_training
from .models import YieldPredictionModel
from .serializers import YieldPredictionModelSerializer
from .services import train_all_models, predict_yield, fill_features, save_prediction


class ModelComparisonView(APIView):
    """GET /api/predictions/models/ — every training, newest first; is_active marks the one in use."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        models = YieldPredictionModel.objects.all()
        return Response(YieldPredictionModelSerializer(models, many=True).data)


class TrainModelsView(APIView):
    """POST /api/predictions/train/ — retrain the yield model now (admin only). The new
    model is used from now on; older trainings are kept for their saved predictions."""
    permission_classes = [IsSuperUser]

    def post(self, request):
        save_training(train_all_models())

        models = YieldPredictionModel.objects.all()
        log_change(request.user, 'model.trained', 'retrained the yield prediction models')
        return Response({
            'message': 'Models trained successfully.',
            'results': YieldPredictionModelSerializer(models, many=True).data,
        })


class PredictYieldView(APIView):
    """
    POST /api/predictions/predict/ — predict yield for a farm scan.

    Optional farm_id and variety_id fill in what the real-harvest model needs
    (barangay, ecosystem, seed type) when the request doesn't send them.

    With a farm, the prediction is also saved for the farm's current crop (or cycle_id),
    so its harvest can later be compared with what was predicted.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        features = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        farm = Farm.objects.filter(pk=features.get('farm_id'), user=request.user).first() \
            if str(features.get('farm_id') or '').isdigit() else None
        variety = RiceVariety.objects.filter(pk=features.get('variety_id')).first() \
            if str(features.get('variety_id') or '').isdigit() else None
        fill_features(features, farm, variety)

        result = predict_yield(features)

        if farm:
            cycles = FarmCycle.objects.filter(farm=farm)
            cycle_id = features.get('cycle_id')
            cycle = (cycles.filter(pk=cycle_id).first() if str(cycle_id or '').isdigit()
                     else cycles.order_by('-created_at', '-id').first())
            save_prediction(cycle, result)

        result.pop('model_id', None)
        return Response(result, status=status.HTTP_200_OK)
