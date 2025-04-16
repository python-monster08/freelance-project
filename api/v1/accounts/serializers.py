from rest_framework import serializers
from api.v1.accounts.razorpay_utils import generate_emp_id
from api.v1.models import *
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from urllib.parse import urljoin
import re
# Email Regular Expression
email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
# Mobil Number Regular Expression
Pattern = re.compile("^\\+?[1-9][0-9]{7,14}$")
# from api.v1.account.utils import get_access_tokens_for_user, get_refres_tokens_for_user
from api.v1.models import UserMaster
from django.db import transaction
from django.contrib.auth.hashers import make_password,check_password
from django.core.validators import FileExtensionValidator
from rest_framework_simplejwt.tokens import AccessToken
from django.core.mail import EmailMultiAlternatives  

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

# class MSMEProfileSerializer(serializers.ModelSerializer):
#     """Serializer for MSMEProfile model, allowing nested Outlet creation"""
    
#     outlets = OutletSerializer(many=True, required=False)  # Supports multiple outlets

#     class Meta:
#         model = MSMEProfile
#         fields = "__all__"  # Include all fields in the MSMEProfile model

#     def update(self, instance, validated_data):
#         """Custom update method to handle nested outlets"""
        
#         # Extract nested outlets data
#         outlets_data = validated_data.pop("outlets", [])

#         # Update the MSMEProfile fields
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()

#         # Handle outlets (clear old ones and add new ones)
#         instance.outlets.all().delete()
#         for outlet_data in outlets_data:
#             Outlet.objects.create(user_profile=instance, **outlet_data)

#         # Update number_of_outlets with outlet names
#         instance.update_outlet_count()

#         return instance
class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating and retrieving MSMEProfile details"""

    # UserMaster fields
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    phone_number = serializers.CharField(source="user.phone_number")
    created_on = serializers.DateTimeField(source="user.created_on", read_only=True)

    # MSMEProfile fields
    website = serializers.CharField(required=False, allow_blank=True)
    brand_name = serializers.CharField(required=False, allow_blank=True)
    number_of_outlets = serializers.SerializerMethodField()  # Dynamic field
    daily_approximate_footfalls = serializers.IntegerField(required=False)
    area = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    zip_code = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    gstin = serializers.CharField(required=False, allow_blank=True)
    pan_number = serializers.CharField(required=False, allow_blank=True)

    # Images
    profile_picture = serializers.SerializerMethodField()
    brand_logo = serializers.SerializerMethodField()

    # Related Outlets
    outlets = OutletSerializer(many=True, read_only=True)

    class Meta:
        model = MSMEProfile
        fields = [
            "username", "email", "first_name", "last_name", "is_active", "phone_number",
            "profile_picture", "website", "brand_name", "number_of_outlets",
            "daily_approximate_footfalls", "brand_logo", "area", "city", "zip_code",
            "state", "gstin", "pan_number", "created_on", "updated_on", "outlets"
        ]

    def get_number_of_outlets(self, obj):
        """Return the dynamic count of active outlets"""
        return obj.outlets.filter(is_deleted=False).count()

    def get_image_url(self, obj, field_name):
        """Returns the full URL for an image field."""
        request = self.context.get("request")
        image = getattr(obj, field_name)
        if image:
            return request.build_absolute_uri(image.url) if request else image.url
        return None

    def get_profile_picture(self, obj):
        return self.get_image_url(obj, "profile_picture")

    def get_brand_logo(self, obj):
        return self.get_image_url(obj, "brand_logo")

    def update(self, instance, validated_data):
        """Ensure UserMaster fields are updated when MSMEProfile is updated"""
        user_data = self.context["request"].data  # Get request data
        request = self.context.get("request")  # Get request context

        # Update UserMaster fields
        user = instance.user
        user.first_name = user_data.get("first_name", user.first_name)
        user.last_name = user_data.get("last_name", user.last_name)
        user.phone_number = user_data.get("phone_number", user.phone_number)
        user.save()

        # Update MSMEProfile fields
        instance.brand_name = validated_data.get("brand_name", instance.brand_name)
        instance.website = validated_data.get("website", instance.website)
        instance.daily_approximate_footfalls = validated_data.get("daily_approximate_footfalls", instance.daily_approximate_footfalls)
        instance.area = validated_data.get("area", instance.area)
        instance.city = validated_data.get("city", instance.city)
        instance.zip_code = validated_data.get("zip_code", instance.zip_code)
        instance.state = validated_data.get("state", instance.state)
        instance.gstin = validated_data.get("gstin", instance.gstin)
        instance.pan_number = validated_data.get("pan_number", instance.pan_number)

        # Handle profile_picture update
        if "profile_picture" in request.FILES:
            instance.profile_picture = request.FILES["profile_picture"]

        # Handle brand_logo update
        if "brand_logo" in request.FILES:
            instance.brand_logo = request.FILES["brand_logo"]

        instance.save()
        return instance

class CustomerSerializer(serializers.ModelSerializer):
    msme = serializers.SerializerMethodField()
    msme_name = serializers.SerializerMethodField()
    class Meta:
        model = Customer
        fields = '__all__'

    def get_msme(self, obj):
        return obj.msme.id
    def get_msme_name(self, obj):
        return obj.msme.brand_name
    




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




# Serializer for listing feedback
class CustomerFeedbackListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    outlet_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerFeedback
        fields = [
            "id",
            "customer_name",
            "outlet_name",
            "overall_experience",
            "service_quality_rating",
            "item_quality_rating",
            "value_for_money",
            "would_recommend",
            "likelihood_to_return",
            "emotions",
            "created_at",
        ]

    def get_customer_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_outlet_name(self, obj):
        return obj.outlet.name

# Serializer for creating feedback
class CustomerFeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerFeedback
        fields = "__all__"

# Serializer for updating feedback
class CustomerFeedbackUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerFeedback
        fields = [
            "overall_experience",
            "service_quality_rating",
            "item_quality_rating",
            "value_for_money",
            "would_recommend",
            "likelihood_to_return",
            "emotions",
            "suggestions",
        ]


import json
# # MembershipPlan Serializer
# class MembershipPlanSerializer(serializers.ModelSerializer):
#     features = serializers.JSONField(write_only=True)  # Accept JSON input directly

#     class Meta:
#         model = MembershipPlan
#         fields = ['id', 'name', 'price', 'is_active', 'features', 'campaign', 'referral_system', 'loyalty_points', 'feedback_analysis']

#     def create(self, validated_data):
#         """Handles both single and bulk creation"""
#         features = validated_data.pop("features", {})  # Extract `features` field

#         # Extract individual fields from features
#         validated_data["campaign"] = features.get("campaign", [])
#         validated_data["referral_system"] = features.get("referralSystem", False)
#         validated_data["loyalty_points"] = features.get("loyaltyPoints", False)
#         validated_data["feedback_analysis"] = features.get("feedbackAnalysis", False)

#         return MembershipPlan.objects.create(**validated_data)

#     def update(self, instance, validated_data):
#         """Update plan with nested features"""
#         features = validated_data.pop("features", {})

#         instance.campaign = features.get("campaign", instance.campaign)
#         instance.referral_system = features.get("referralSystem", instance.referral_system)
#         instance.loyalty_points = features.get("loyaltyPoints", instance.loyalty_points)
#         instance.feedback_analysis = features.get("feedbackAnalysis", instance.feedback_analysis)

#         instance.name = validated_data.get("name", instance.name)
#         instance.price = validated_data.get("price", instance.price)
#         instance.is_active = validated_data.get("is_active", instance.is_active)

#         instance.save()
#         return instance


# Serializer for listing plans (GET)
class MembershipPlanListSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    class Meta:
        model = MembershipPlan
        fields = ["id", "name", "price", "duration_days", "is_active", "features"]

    def get_features(self, obj):
        """Convert model fields into a nested features JSON"""
        return {
            "campaign": obj.campaign,
            "referral_system": obj.referral_system,
            "loyalty_points": obj.loyalty_points,
            "feedback_analysis": obj.feedback_analysis,
        }

# Serializer for creating and updating plans (POST & PUT)
class MembershipPlanCreateUpdateSerializer(MembershipPlanListSerializer):
    features = serializers.JSONField(write_only=True)  # Accept features as JSON input

    class Meta:
        model = MembershipPlan
        fields = ["id", "name", "price", "duration_days", "is_active", "features"]

    def create(self, validated_data):
        """Create a new MembershipPlan"""
        features = validated_data.pop("features", {})

        validated_data["campaign"] = features.get("campaign", [])
        validated_data["referral_system"] = features.get("referral_system", False)
        validated_data["loyalty_points"] = features.get("loyalty_points", False)
        validated_data["feedback_analysis"] = features.get("feedback_analysis", False)

        instance = MembershipPlan.objects.create(**validated_data)

        return instance  # Returning instance ensures full data serialization

    def update(self, instance, validated_data):
        """Update an existing MembershipPlan"""
        features = validated_data.pop("features", {})

        instance.name = validated_data.get("name", instance.name)
        instance.price = validated_data.get("price", instance.price)
        instance.duration_days = validated_data.get("duration_days", instance.duration_days)
        instance.is_active = validated_data.get("is_active", instance.is_active)

        instance.campaign = features.get("campaign", instance.campaign)
        instance.referral_system = features.get("referral_system", instance.referral_system)
        instance.loyalty_points = features.get("loyalty_points", instance.loyalty_points)
        instance.feedback_analysis = features.get("feedback_analysis", instance.feedback_analysis)

        instance.save()
        return instance
    
    
# class SupportSystemGetSerializer(serializers.ModelSerializer):
#     """Serializer for retrieving SupportSystem records"""
#     plan_name = serializers.CharField(source="plan.name", read_only=True)  # Fetching related plan name

#     plan_support = serializers.SerializerMethodField()

#     class Meta:
#         model = SupportSystem
#         fields = ["id", "plan", "plan_name", "plan_support"]

#     def get_plan_support(self, instance):
#         """Returns structured plan support details"""
#         return {
#             "support": instance.support,
#             "training": instance.training,
#             "staff_re_training": instance.staff_re_training,
#             "dedicated_poc": instance.dedicated_poc
#         }


# class SupportSystemCreateUpdateSerializer(serializers.ModelSerializer):
#     """Serializer for creating/updating SupportSystem records"""

#     class Meta:
#         model = SupportSystem
#         fields = ["plan", "support", "training", "staff_re_training", "dedicated_poc"]

#     def validate_plan(self, value):
#         """Ensure the plan exists and is not deleted"""
#         if not MembershipPlan.objects.filter(id=value.id, is_deleted=False).exists():
#             raise serializers.ValidationError("Invalid or deleted Plan ID")
#         return value

#     def to_representation(self, instance):
#         """Ensure the response includes plan_name"""
#         data = super().to_representation(instance)
#         data["plan_name"] = instance.plan.name if instance.plan else None  # Handle cases where plan might be null
#         return data



class SupportSystemGetSerializer(serializers.ModelSerializer):
    """Serializer for retrieving SupportSystem records"""
    plan_name = serializers.CharField(source="plan.name", read_only=True)  # Fetching related plan name
    plan_support = serializers.SerializerMethodField()

    class Meta:
        model = SupportSystem
        fields = ["id", "plan", "plan_name", "plan_support"]

    def get_plan_support(self, instance):
        """Returns structured plan support details"""
        return {
            "support": instance.support,
            "training": instance.training,
            "staff_re_training": instance.staff_re_training,
            "dedicated_poc": instance.dedicated_poc
        }


class SupportSystemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating SupportSystem records"""

    class Meta:
        model = SupportSystem
        fields = ["plan", "support", "training", "staff_re_training", "dedicated_poc"]

    def validate_plan(self, value):
        """Ensure the plan exists and is not deleted"""
        if not MembershipPlan.objects.filter(id=value.id, is_deleted=False).exists():
            raise serializers.ValidationError("Invalid or deleted Plan ID")
        return value

    def to_representation(self, instance):
        """Ensure the response includes plan_name"""
        data = super().to_representation(instance)
        data["plan_name"] = instance.plan.name if instance.plan else None
        return data


class SupportSystemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating SupportSystem records"""
    
    plan_support = serializers.DictField(child=serializers.BooleanField(), write_only=True)

    class Meta:
        model = SupportSystem
        fields = ["plan_support"]

    def update(self, instance, validated_data):
        """Update support system fields based on provided data"""
        plan_support_data = validated_data.get("plan_support", {})

        # Mapping request keys to model fields
        field_map = {
            "support": "support",
            "training": "training",
            "staff_re_training": "staff_re_training",
            "dedicated_poc": "dedicated_poc"
        }

        for request_field, model_field in field_map.items():
            if request_field in plan_support_data:
                setattr(instance, model_field, plan_support_data[request_field])

        instance.save()
        return instance

    def to_representation(self, instance):
        """Return structured response"""
        return {
            "id": instance.id,
            "plan_name": instance.plan.name if instance.plan else None,
            "plan_support": {
                "support": instance.support,
                "training": instance.training,
                "staff_re_training": instance.staff_re_training,
                "dedicated_poc": instance.dedicated_poc,
            }
        }


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = "__all__"




##########################################

class SubAdminRegisterSerializer(serializers.Serializer):
    assigned_by = serializers.CharField(max_length=60, required=False,allow_null=True)
    name = serializers.CharField(max_length=20, required=True)
    email = serializers.EmailField(max_length=60, required=True)
    # address = serializers.CharField(max_length=60, required=True)
    # access = serializers.ListSerializer(child=RoleAccessWithSubModule())
    class Meta:
        model = UserMaster
        fields = ['assigned_by','name','email','role','access']


    def validate(self, attrs):
        request=self.context.get('request')
        assigned_by = attrs.get('assigned_by')
        role_access = attrs.get('access')
        name=attrs.get('name')
        email=attrs.get('email')

        role = request.user.user_role.id

        if not role_access:
            raise serializers.ValidationError({'error':'role access are mandatory fields.'})

        if role not in [1,2]:
            raise serializers.ValidationError({"error": "Registration is only allowed for admin."})

        with transaction.atomic():
        
            if not re.fullmatch(r'^[A-Za-z\s]+$', name):
                raise serializers.ValidationError({'error':"Name must contain only alphabets."})
            
            if email:
                if UserMaster.objects.filter(email=email).exists():
                    raise serializers.ValidationError({'error':'User with this email already exists.'})
                if not re.fullmatch(email_regex, email):
                    raise serializers.ValidationError({'error':'Please enter a valid email.'})
            else:
                raise serializers.ValidationError({'error':'Please provide email.'})
        
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            request=self.context.get('request')
            role_access = validated_data.get('access')
            assigned_by = validated_data.get('assigned_by')
            role_data=request.user.role.id
            user_code=generate_emp_id(role_data)
            user = UserMaster(
                full_name=validated_data['name'],
                # phone_number=validated_data['phone_number'],
                email=validated_data['email'],
                username=validated_data['email'],
                # address=validated_data['address'],
                user_role_id=2,
                user_code=user_code,
                is_active=True,
                created_by_id=int(request.user.id),
            )
            user.save()
            user_id = user.id

        
            ## Send welcome email
            send_credentials_email(user)

        return user

class UpdateSubAdminSerializer(serializers.Serializer):
    assigned_by = serializers.CharField(max_length=60, required=False,allow_null=True)
    name = serializers.CharField(required = False,error_messages={'invalid': 'Please enter a valid name.'})
    role_id = serializers.CharField(required = False,allow_null=True,error_messages={'invalid': 'Please enter a valid role.'})
    class Meta:
        
        model = UserMaster
        fields = ['id','name','role_id','access','assigned_by']

    def validate(self,attrs):
        with transaction.atomic():
            request=self.context.get('request')
            user = self.context.get('user')
            userMaster = self.instance
            name = attrs.get('name')
            role_id = attrs.get('role_id')
            role_access = attrs.get('access')
            assigned_by = attrs.get('assigned_by')
        
            role = request.user.user_role.id
            if not (int(role) in [1,2]):    
                raise serializers.ValidationError({'error':'Please provide valid role id.'})
            
            if not re.fullmatch(r'^[A-Za-z\s]+$', name):
                raise serializers.ValidationError({'error':"Name must contain only alphabets."})
            
            
            userMaster.full_name = name if name else userMaster.full_name
            userMaster.user_role_id=int(role_id) if role_id else userMaster.user_role_id
            userMaster.updated_by_id = int(request.user.id)       
            userMaster.assigned_by_id=int(request.user.id)
            # userMaster.created_on=datetime.datetime.now()

            userMaster.save()

            

            
            return attrs

class GetSubAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMaster
        fields = ['id', 'full_name', 'email', 'phone_number', 'address', 'description', 'created_by','assigned_by',]
    

    def to_representation(self, instance):
        request = self.context.get('request')
        data = super().to_representation(instance)
        data['name'] = data.pop('full_name') if instance.full_name else ""
        data['email'] = data.pop('email') if instance.email else ""
        data['phone_number'] = data.pop('phone_number') if instance.phone_number else ""
        data['address'] = data.pop('address') if instance.address else ""
        data['image'] = data.pop('profile_picture') if instance.profile_picture else ""
        data['created_by'] = data.pop('created_by') if instance.created_by else None
        data['created_by_name'] = instance.created_by.full_name if instance.created_by else ""
        data['assigned_by'] = data.pop('assigned_by') if instance.assigned_by else None
        data['assigned_by_name'] = instance.assigned_by.full_name if instance.assigned_by else ""
        data['description'] = data.pop('description') if instance.description else ""

        return data
