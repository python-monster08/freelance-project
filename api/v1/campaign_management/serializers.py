from rest_framework import serializers
from api.v1.models import Campaign

class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model"""

    class Meta:
        model = Campaign
        fields = "__all__"
