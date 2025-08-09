from rest_framework import viewsets
from django.utils.text import slugify
from sports.models.sport import Sport
from sports.api.serializers.sport_serializer import SportSerializer
from sports.api.permissions.sport_permissions import IsAdminOrReadOnly

class SportViewSet(viewsets.ModelViewSet):
    queryset = Sport.objects.all()
    serializer_class = SportSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(slug=slugify(serializer.validated_data['name']))

    def perform_update(self, serializer):
        if 'name' in serializer.validated_data:
            serializer.save(slug=slugify(serializer.validated_data['name']))
        else:
            serializer.save()
