from rest_framework import serializers
from api.v1.models import *
from api.v1.accounts.serializers import OutletSerializer

class GetCampaignSerializer(serializers.ModelSerializer):
    """Serializer for retrieving Campaign details"""

    campaign_channel = serializers.SerializerMethodField()
    # campaign_outlets = serializers.SerializerMethodField()
    campaign_outlets = OutletSerializer(many=True, source="outlets")

    class Meta:
        model = Campaign
        fields = [  # ✅ List all fields except campaign_logo & campaign_bg_image
            "id", "name", "message", "expiry_date", "button_url",
            "reward_choice", "profession", "campaign_type",
            "campaign_channel", "campaign_outlets", "image_url",
            "created_on", "updated_on"
        ]

    def get_campaign_channel(self, obj):
        """Retrieve related campaign channels"""
        return list(obj.channels.values_list("id", flat=True))  # Returns list of channel IDs

    def get_campaign_outlets(self, obj):
        """Retrieve related campaign outlets"""
        return list(obj.outlets.values_list("id", flat=True))  # Returns list of outlet IDs



class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for the Campaign model"""

    campaign_channel = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    campaign_outlets = serializers.ListField(child=serializers.CharField(), write_only=True)
    campaign_reward_choice_text = serializers.CharField(write_only=True, required=False)
    campaign_message = serializers.CharField(write_only=True, required=False)
    campaign_expiry_date = serializers.DateField(write_only=True, required=False)
    button_url = serializers.URLField(write_only=True, required=False)

    campaign_logo = serializers.ImageField(write_only=True, required=True)  # ✅ File field
    campaign_bg_image = serializers.ImageField(write_only=True, required=True)  # ✅ File field

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "campaign_reward_choice_text", "campaign_message",
            "campaign_expiry_date", "button_url", "reward_choice", "profession", "campaign_type",
            "campaign_channel", "campaign_outlets", "campaign_logo", "campaign_bg_image", "image_url"
        ]


# class CampaignSerializer(serializers.ModelSerializer):
#     """Serializer for Campaign model"""

#     class Meta:
#         model = Campaign
#         fields = "__all__"
#         extra_kwargs = {"user_profile": {"required": False}}  # Make `user_profile` optional

#     def create(self, validated_data):
#         """Auto-assign the user_profile from the request"""
#         request = self.context.get("request")
#         validated_data["user_profile"] = request.user.profile
#         return super().create(validated_data)


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

class GetMSMEProfileSerializer(serializers.ModelSerializer):
    """Serializer for MSMEProfile model with nested sub_outlets"""
    
    main_outlet_name = serializers.CharField(source="brand_name")  # Rename brand_name to main_outlet
    daily_footfalls = serializers.CharField(source="daily_approximate_footfalls")  # Rename brand_name to main_outlet
    sub_outlets = GetOutletSerializer(many=True, source="outlets")  # Fetch related outlets

    class Meta:
        model = MSMEProfile
        fields = ["id", "main_outlet_name", "area", "city", "zip_code", "state", "daily_footfalls", "sub_outlets"]


class CreateOutletSerializer(serializers.ModelSerializer):
    """Serializer for creating a new outlet"""

    class Meta:
        model = Outlet
        fields = ["name", "area", "city", "zip_code", "state", "daily_footfalls"]

    def create(self, validated_data):
        """Attach outlet to the logged-in user's profile before saving"""
        request = self.context.get("request")
        user_profile = request.user.profile  # Get the profile of the logged-in user
        validated_data["user_profile"] = user_profile
        return super().create(validated_data)


class UpdateOutletSerializer(serializers.ModelSerializer):
    """Serializer for updating an existing outlet"""

    class Meta:
        model = Outlet
        fields = ["name", "area", "city", "zip_code", "state", "daily_footfalls"]
