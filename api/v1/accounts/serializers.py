from rest_framework import serializers
from api.v1.accounts.razorpay_utils import generate_emp_id, generate_referral_code, send_credentials_email
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



email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

class CustomerRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=20, required=True, allow_null=True)
    last_name = serializers.CharField(max_length=20, required=False, allow_null=True)
    email = serializers.EmailField(max_length=60, required=False, allow_null=True)
    whatsapp_number = serializers.CharField(max_length=60, required=True)
    gender = serializers.CharField(max_length=20, required=False, allow_null=True)
    dob = serializers.CharField(max_length=20, required=False, allow_null=True)
    anniversary_date = serializers.CharField(max_length=20, required=False, allow_null=True)
    city = serializers.CharField(max_length=50, required=False, allow_null=True)
    referral_code = serializers.CharField(max_length=50, required=False, allow_null=True)
    referral_setting = serializers.CharField(max_length=50, required=False, allow_null=True)
    

    def validate(self, attrs):
        request = self.context.get('request')
        first_name = attrs.get('first_name')
        last_name = attrs.get('last_name')
        email = attrs.get('email')
        whatsapp_number = attrs.get('whatsapp_number')
        referral_setting = attrs.get('referral_setting')

        if not re.fullmatch(r'^[A-Za-z\s]+$', first_name or ''):
            raise serializers.ValidationError({'error': "First name must contain only alphabets."})

        if last_name and not re.fullmatch(r'^[A-Za-z\s]+$', last_name):
            raise serializers.ValidationError({'error': "Last name must contain only alphabets."})

        if email:
            if Customer.objects.filter(email=email).exists():
                raise serializers.ValidationError({'error': 'User with this email already exists.'})
            if not re.fullmatch(email_regex, email):
                raise serializers.ValidationError({'error': 'Please enter a valid email.'})

        if whatsapp_number:
            if Customer.objects.filter(whatsapp_number=whatsapp_number).exists():
                raise serializers.ValidationError({'error': 'User with this phone number already exists.'})
        else:
            raise serializers.ValidationError({'error': 'Please provide mobile number.'})
        
        if not referral_setting:
            raise serializers.ValidationError({'error': 'Please provide referral setting id.'})

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            request = self.context.get('request')
            user_id = int(request.user.id)
            referral_setting = validated_data.get('referral_setting')
            referral_code_input = validated_data.get('referral_code')
            generated_referral_code = generate_referral_code()

            # Prepare customer fields
            customer_fields = {
                'first_name': validated_data.get('first_name'),
                'last_name': validated_data.get('last_name'),
                'whatsapp_number': validated_data.get('whatsapp_number'),
                'email': validated_data.get('email'),
                'gender': validated_data.get('gender'),
                'dob': validated_data.get('dob'),
                'anniversary_date': validated_data.get('anniversary_date'),
                'city': validated_data.get('city'),
                'referral_code': generated_referral_code,
                'is_active': True,
                'msme_id': user_id,
                'created_by_id': user_id,
            }

            if not referral_code_input:
                # No referral - create customer and referral master
                customer_obj = Customer.objects.create(**customer_fields)

                ReferralMaster.objects.create(
                    referral_code=generated_referral_code,
                    customer=customer_obj,
                    created_by_id=user_id,
                    referral_setting_id=int(referral_setting) if referral_setting else None,
                )

            else:
                # Referral code provided - validate it
                referral_user = Customer.objects.filter(
                    referral_code=referral_code_input,
                    is_active=True,
                    is_deleted=False
                ).last()

                if not referral_user:
                    raise serializers.ValidationError({'error': 'Invalid referral code.'})

                customer_fields['referral_by'] = referral_user
                customer_obj = Customer.objects.create(**customer_fields)

                # Fetch the referral master instance related to the referral user
                referral_master_instance = ReferralMaster.objects.filter(
                    customer=referral_user
                ).last()

                if not referral_master_instance:
                    raise serializers.ValidationError({'error': 'Referral master not found for the provided code.'})

                # Create referee master record
                RefereeMaster.objects.create(
                    referral=referral_master_instance,  # This should be a ReferralMaster instance
                    customer=customer_obj,
                    referral_code=generated_referral_code,
                    created_by_id=user_id,
                    referral_setting_id=int(referral_setting) if referral_setting else None,
                )

            # Send welcome email
            send_credentials_email(customer_obj)

            return customer_obj



class UpdateCustomerSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=20, required=True,allow_null=True)
    last_name = serializers.CharField(max_length=20, required=False,allow_null=True)
    email = serializers.EmailField(max_length=60, required=False,allow_null=True)
    whatsapp_number = serializers.CharField(max_length=60, required=True)
    gender = serializers.CharField(max_length=20, required=False,allow_null=True)
    dob = serializers.CharField(max_length=20, required=False,allow_null=True)
    anniversary_date = serializers.CharField(max_length=20, required=False,allow_null=True)
    city = serializers.CharField(max_length=50, required=False,allow_null=True)

    class Meta:
        model = Customer

    def validate(self,attrs):
        with transaction.atomic():
            request=self.context.get('request')
            user = self.context.get('user')
            customer_obj = self.instance
            first_name = attrs.get('first_name')
            last_name = attrs.get('last_name')
            email=attrs.get('email')
            whatsapp_number=attrs.get('whatsapp_number')
            gender = attrs.get('gender')
            dob = attrs.get('dob')
            anniversary_date=attrs.get('anniversary_date')
            city=attrs.get('city')
        
            role = request.user.user_role.id
            if not (int(role) in [1,2,3]):    
                raise serializers.ValidationError({'error':'Please provide valid role id.'})
            
            if not re.fullmatch(r'^[A-Za-z\s]+$', first_name):
                raise serializers.ValidationError({'error':"Name must contain only alphabets."})
            if not re.fullmatch(r'^[A-Za-z\s]+$', last_name):
                raise serializers.ValidationError({'error':"Name must contain only alphabets."})
            
            
            customer_obj.first_name = first_name if first_name else customer_obj.first_name
            customer_obj.last_name = last_name if last_name else customer_obj.last_name
            customer_obj.email = email if email else customer_obj.email
            customer_obj.whatsapp_number = whatsapp_number if whatsapp_number else customer_obj.whatsapp_number
            customer_obj.gender = gender if gender else customer_obj.gender
            customer_obj.dob = dob if dob else customer_obj.dob
            customer_obj.anniversary_date = anniversary_date if anniversary_date else customer_obj.anniversary_date
            customer_obj.city = city if city else customer_obj.city
            customer_obj.updated_by_id = int(request.user.id)       
            customer_obj.msme_id=int(request.user.id)

            customer_obj.save()
            
            return attrs

class GetCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'first_name','last_name', 'email', 'whatsapp_number', 'gender', 'dob','city', 'created_by','msme',]
    

    def to_representation(self, instance):
        request = self.context.get('request')
        data = super().to_representation(instance)
        data['first_name'] = data.pop('first_name') if instance.first_name else ""
        data['last_name'] = data.pop('last_name') if instance.last_name else ""
        data['email'] = data.pop('email') if instance.email else ""
        data['whatsapp_number'] = data.pop('whatsapp_number') if instance.whatsapp_number else ""
        data['gender'] = data.pop('gender') if instance.gender else ""
        data['created_by'] = data.pop('created_by') if instance.created_by else None
        data['created_by_name'] = instance.created_by.first_name if instance.created_by else ""
        data['anniversary_date'] = data.pop('anniversary_date') if instance.anniversary_date else ""
        data['city'] = instance.city if instance.city else ""
        data['dob'] = data.pop('dob') if instance.dob else ""
        data['msme'] = data.pop('msme') if instance.msme else None
        data['msme_name'] = instance.msme.brand_name if instance.msme else ""

        return data





class ReferralSettingSerializer(serializers.ModelSerializer):
    referral_terms = serializers.ListField(child=serializers.CharField(), required=False)
    referee_terms = serializers.ListField(child=serializers.CharField(), required=False)
    channels = serializers.PrimaryKeyRelatedField(queryset=Channel.objects.all(), many=True)
    
    is_active = serializers.BooleanField(required=False)
 
    # These are read-only computed fields
    msme_id = serializers.SerializerMethodField()
    msme_name = serializers.SerializerMethodField()
 
    class Meta:
        model = ReferralSetting
        fields = [
            "id", "msme_id", "msme_name", "created_by",
 
            # Referral Details
            "selected_offer", "selected_offer_text",
            "reward_expire_type", "reminder_type", "reminder_value",
            "contact_type", "contact_value", "referral_terms",
 
            # Referee Details
            "referrer_discount", "min_purchase", "post_purchase",
            "time_unit", "time_value", "referee_terms",
 
            # Channels
            "channels",
 
            "is_active",
            "created_on"
        ]
        read_only_fields = ["id", "created_on", "msme_id", "msme_name", "created_by"]
 
    def get_msme_id(self, obj):
        return obj.msme.id if obj.msme else None
 
    def get_msme_name(self, obj):
        return obj.msme.brand_name if obj.msme else "No MSME"
 
    def to_representation(self, instance):
        data = super().to_representation(instance)
 
        response = {
            "referral_details": {
                "selected_offer": data.pop("selected_offer"),
                "selected_offer_text": data.pop("selected_offer_text"),
                "reward_expire_type": data.pop("reward_expire_type"),
                "reminder_type": data.pop("reminder_type"),
                "reminder_type_text": data.pop("reminder_value"),
                "contact_type": data.pop("contact_type"),
                "contact_type_text": data.pop("contact_value"),
                "terms": data.pop("referral_terms", []),
            },
            "referee_details": {
                "referrer_discount": data.pop("referrer_discount"),
                "min_purchase": data.pop("min_purchase"),
                "post_purchase": data.pop("post_purchase"),
                "time_unit": data.pop("time_unit"),
                "time_value": data.pop("time_value"),
                "terms": data.pop("referee_terms", []),
            },
            "channels": data.pop("channels"),
            "id": data.pop("id"),
            "msme_id": data.pop("msme_id"),
            "msme_name": data.pop("msme_name"),
            "created_by": data.pop("created_by"),
            "created_on": data.pop("created_on"),
        }
 
        return response
 
 
 
