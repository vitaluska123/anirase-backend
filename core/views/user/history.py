from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from core.models import History
from core.serializers import HistorySerializer

class HistoryListCreateView(generics.ListCreateAPIView):
    serializer_class = HistorySerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return History.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
