from rest_framework import serializers
from sports.models.sport import Sport

class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ["id", "name", "slug", "icon", "is_active"]
        read_only_fields = ["slug"]  # ⬅️ Slug plus obligatoire dans le POST
