from rest_framework import serializers
from api.v1.models import UserMaster, UserProfile
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
        # Custom validation
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": _("Email already exists.")})
        if User.objects.filter(phone_number=attrs['phone_number']).exists():
            raise serializers.ValidationError({"phone_number": _("Phone number already exists.")})
        return attrs

    def create(self, validated_data):
        user = User(
            **validated_data,
            is_active=True  # User is not active until approved by super_admin
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['address', 'date_of_birth', 'profile_picture', 'bio', 'website']


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
