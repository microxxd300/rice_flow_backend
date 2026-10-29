from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status

from apps.farms.models import Farm
from apps.varieties.models import RiceVariety

from .models import YieldPredictionModel
from .serializers import YieldPredictionModelSerializer
from .services import train_all_models, predict_yield, seed_type_for


class ModelComparisonView(APIView):
    """GET /api/predictions/models/ — list all trained model results."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        models = YieldPredictionModel.objects.all()
        return Response(YieldPredictionModelSerializer(models, many=True).data)


class TrainModelsView(APIView):
    """POST /api/predictions/train/ — retrain all 3 models (admin only)."""
    permission_classes = [IsAdminUser]

    def post(self, request):
        results = train_all_models()

        # Clear old records, save new ones
        YieldPredictionModel.objects.all().delete()
        for r in results:
            YieldPredictionModel.objects.create(**r)

        models = YieldPredictionModel.objects.all()
        return Response({
            'message': 'Models trained successfully.',
            'results': YieldPredictionModelSerializer(models, many=True).data,
        })


class PredictYieldView(APIView):
    """
    POST /api/predictions/predict/ — predict yield for a farm scan.

    Optional farm_id and variety_id fill in what the real-harvest model needs
    (barangay, ecosystem, seed type) when the request doesn't send them.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        features = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)

        farm = Farm.objects.filter(pk=features.get('farm_id'), user=request.user).first() \
            if str(features.get('farm_id') or '').isdigit() else None
        if farm:
            features.setdefault('barangay', farm.barangay)
            features.setdefault('ecosystem', farm.ecosystem)

        variety = RiceVariety.objects.filter(pk=features.get('variety_id')).first() \
            if str(features.get('variety_id') or '').isdigit() else None
        if variety:
            features.setdefault('seed_type', seed_type_for(variety))
            features.setdefault('maturity_days', variety.maturity_days)
            features.setdefault('variety_avg_yield', variety.avg_yield_t_ha)

        result = predict_yield(features)
        return Response(result, status=status.HTTP_200_OK)
