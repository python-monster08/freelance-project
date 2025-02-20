from rest_framework import serializers
from api.v1.models import *
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

User = get_user_model()

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password']

    def validate(self, attrs):
        if User.objects.filter(username=attrs['username']).exists() or \
           User.objects.filter(email=attrs['email']).exists() or \
           User.objects.filter(phone_number=attrs['phone_number']).exists():
            raise serializers.ValidationError("User already exists.")  # Single message
        return attrs

    def create(self, validated_data):
        user = User(
            **validated_data,
            is_active=True
        )
        user.set_password(validated_data['password'])
        user.save()
        return user



class UserLoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        # Ensure either username or email is provided
        if not attrs.get('username_or_email'):
            raise ValidationError(_('This field is required.'))
        if not attrs.get('password'):
            raise ValidationError(_('This field is required.'))
        return attrs





class OutletSerializer(serializers.ModelSerializer):
    """Serializer for Outlet model"""
    
    class Meta:
        model = Outlet
        fields = ["id", "name", "area", "city", "zip_code", "state", "daily_footfalls"]
        read_only_fields = ["id"]  # Auto-generated field

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model, allowing nested Outlet creation"""
    
    outlets = OutletSerializer(many=True, required=False)  # Supports multiple outlets

    class Meta:
        model = UserProfile
        fields = "__all__"  # Include all fields in the UserProfile model

    def update(self, instance, validated_data):
        """Custom update method to handle nested outlets"""
        
        # Extract nested outlets data
        outlets_data = validated_data.pop("outlets", [])

        # Update the UserProfile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle outlets (clear old ones and add new ones)
        instance.outlets.all().delete()
        for outlet_data in outlets_data:
            Outlet.objects.create(user_profile=instance, **outlet_data)

        # Update number_of_outlets with outlet names
        instance.update_outlet_count()

        return instance


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'




class AddSingleCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'first_name', 'last_name', 'email', 'whatsapp_number','gender', 'dob', 'anniversary_date', 'city']

    def to_internal_value(self, data):
        """ Convert empty strings to None before validation """
        if "dob" in data and data["dob"] == "":
            data["dob"] = None
        if "anniversary_date" in data and data["anniversary_date"] == "":
            data["anniversary_date"] = None
        return super().to_internal_value(data)
