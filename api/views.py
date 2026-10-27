from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response

from .models import Doctor, Patient, PatientDoctorMapping
from .serializers import DoctorSerializer, MappingSerializer, PatientSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class PatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer

    def get_queryset(self):
        return Patient.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer


class MappingViewSet(viewsets.ModelViewSet):
    serializer_class = MappingSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        return PatientDoctorMapping.objects.filter(patient__created_by=self.request.user).select_related("doctor")

    def retrieve(self, request, pk=None):
        """Per the spec, GET /api/mappings/<patient_id>/ lists that patient's doctors."""
        patient = generics.get_object_or_404(Patient, pk=pk, created_by=request.user)
        return Response(self.get_serializer(self.get_queryset().filter(patient=patient), many=True).data)
