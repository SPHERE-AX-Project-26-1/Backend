from rest_framework import serializers

from .models import Region


class RegionListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="region_name", read_only=True)

    class Meta:
        model = Region
        fields = ["id", "name"]


class VideoUploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()

    riverId = serializers.PrimaryKeyRelatedField(
        source="region",
        queryset=Region.objects.all()
    )

    duration = serializers.IntegerField(min_value=1)

    title = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )
