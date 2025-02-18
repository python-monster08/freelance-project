from rest_framework import serializers
from api.v1.models import *

class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model"""

    class Meta:
        model = Campaign
        fields = "__all__"


class ProfessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profession
        fields = ['id', 'name']

class RewardChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardChoice
        fields = ['id', 'name']

class CampaignTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignType
        fields = ['id', 'name']




class GetOutletSerializer(serializers.ModelSerializer):
    """Serializer for Outlet model"""
    
    class Meta:
        model = Outlet
        fields = ["id", "name", "area", "city", "zip_code", "state", "daily_footfalls"]

class GetUserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model with nested sub_outlets"""
    
    main_outlet_name = serializers.CharField(source="brand_name")  # Rename brand_name to main_outlet
    daily_footfalls = serializers.CharField(source="daily_approximate_footfalls")  # Rename brand_name to main_outlet
    sub_outlets = GetOutletSerializer(many=True, source="outlets")  # Fetch related outlets

    class Meta:
        model = UserProfile
        fields = ["id", "main_outlet_name", "area", "city", "zip_code", "state", "daily_footfalls", "sub_outlets"]




