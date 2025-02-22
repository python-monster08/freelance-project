from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.v1.models import *
from .serializers import *
from .utils import *
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from io import BytesIO
from PIL import Image
import base64
import requests
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# class CampaignListCreateView(generics.ListCreateAPIView):
#     """API to list all campaigns or create a new campaign"""

#     serializer_class = CampaignSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         return Campaign.objects.filter(is_deleted=False)

#     def list(self, request, *args, **kwargs):
#         """Return all campaigns with a structured response"""
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)

#         return Response({
#             "status": True,
#             "message": "Campaigns retrieved successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)

#     def create(self, request, *args, **kwargs):
#         """Create a new campaign with structured response"""
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             try:
#                 # Extract images from request (multipart/form-data)
#                 bg_image = request.FILES.get("bgimage")
#                 logo_image = request.FILES.get("logoImage")
#                 # button_url = request.data.get("button_url")

#                 if not (bg_image and logo_image):
#                     return Response({"status": False, "message": "Both bgimage and logoImage are required", "data": []}, status=status.HTTP_400_BAD_REQUEST)

#                 # Process images (overlay logo on background)
#                 final_image_b64 = self.process_images(bg_image, logo_image)

#                 # Upload to ImgBB
#                 image_url = self.upload_image_to_imgbb(final_image_b64)
#                 if not image_url:
#                     return Response({"status": False, "message": "Image upload failed", "data": []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#                 # Save campaign
#                 campaign = serializer.save(user_profile=self.request.user.profile, image_url=image_url)
#                 print("Campaign created:", campaign)

#                 # Get customers associated with the user's outlets
#                 customers = campaign.user_profile.outlets.first().feedbacks.all()
#                 print("Customers:", customers)

#                 # Send messages based on channel type
#                 for customer in customers:
#                     if campaign.channel_type in ["whatsapp", "all"]:
#                         send_whatsapp_message(customer.whatsapp_number, campaign.message, campaign.image_url, campaign.button_url)
#                         print("WhatsApp sent to", customer.whatsapp_number)
#                     if campaign.channel_type in ["email", "all"]:
#                         send_email_message(customer.email, campaign.message, campaign.image_url, campaign.button_url)
#                         print("Email sent to", customer.email)
#                     if campaign.channel_type in ["sms", "all"]:
#                         send_sms_message(customer.whatsapp_number, campaign.message)
#                         print("SMS sent to", customer.whatsapp_number)

#                 return Response({
#                     "status": True,
#                     "message": "Campaign created successfully",
#                     "data": {"image_url": image_url}
#                 }, status=status.HTTP_201_CREATED)

#             except Exception as e:
#                 return Response({"status": False, "message": str(e), "data": []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         return Response({"status": False, "message": "Invalid data", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

#     def process_images(self, bg_image, logo_image):
#         """Overlay the logo on the background image and return as base64."""
#         try:
#             from io import BytesIO
#             from PIL import Image
#             import base64

#             # Read images
#             bg_image_pil = Image.open(bg_image).convert("RGBA")
#             logo_image_pil = Image.open(logo_image).convert("RGBA")

#             # Resize logo
#             logo_image_pil = logo_image_pil.resize((1000, 1000))

#             # Position logo at bottom-right corner
#             position = (bg_image_pil.width - logo_image_pil.width - 10, bg_image_pil.height - logo_image_pil.height - 10)
#             bg_image_pil.paste(logo_image_pil, position, logo_image_pil)

#             # Convert to base64
#             buffered = BytesIO()
#             bg_image_pil.save(buffered, format="PNG")
#             return base64.b64encode(buffered.getvalue()).decode("utf-8")

#         except Exception as e:
#             raise ValueError(f"Image processing error: {e}")

#     def upload_image_to_imgbb(self, image_data):
#         """Upload image to ImgBB and return URL."""
#         import requests
#         from django.conf import settings

#         url = "https://api.imgbb.com/1/upload"
#         payload = {"key": settings.IMGBB_API_KEY, "image": image_data}
#         response = requests.post(url, data=payload)

#         if response.status_code == 200:
#             return response.json()["data"]["url"]
#         return None


# class CampaignListCreateView(generics.ListCreateAPIView):
#     """API to list all campaigns or create a new campaign"""

#     serializer_class = CampaignSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         return Campaign.objects.filter(is_deleted=False)

#     def list(self, request, *args, **kwargs):
#         """Return all campaigns with a structured response"""
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)

#         return Response({
#             "status": True,
#             "message": "Campaigns retrieved successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)

#     def create(self, request, *args, **kwargs):
#         """Create a new campaign with structured response"""
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             try:
#                 # ✅ Extract images
#                 bg_image = request.FILES.get("campaign_bg_image")
#                 logo_image = request.FILES.get("campaign_logo")

#                 if not (bg_image and logo_image):
#                     return Response({"status": False, "message": "Both background and logo images are required"}, status=status.HTTP_400_BAD_REQUEST)

#                 # ✅ Process images (overlay logo on background)
#                 final_image_b64 = self.process_images(bg_image, logo_image)

#                 # ✅ Upload to ImgBB
#                 image_url = self.upload_image_to_imgbb(final_image_b64)
#                 if not image_url:
#                     return Response({"status": False, "message": "Image upload failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#                 # ✅ Extract and validate related fields
#                 campaign_channels = request.data.get("campaign_channel", [])  # Expecting list of channel IDs
#                 campaign_outlets = request.data.get("campaign_outlets", [])    # Expecting list of outlet/UserProfile IDs
#                 reward_choice_id = request.data.get("reward_choice")
#                 profession_id = request.data.get("profession")
#                 campaign_type_id = request.data.get("campaign_type")

#                 # ✅ Fetch related objects
#                 reward_choice = RewardChoice.objects.filter(id=reward_choice_id).first()
#                 profession = Profession.objects.filter(id=profession_id).first()
#                 campaign_type = CampaignType.objects.filter(id=campaign_type_id).first()

#                 # ✅ Validate required fields
#                 if not (reward_choice and profession and campaign_type):
#                     return Response({"status": False, "message": "Invalid reward choice, profession, or campaign type"}, status=status.HTTP_400_BAD_REQUEST)

#                 # ✅ Fetch channels
#                 channels = Channel.objects.filter(id__in=campaign_channels)

#                 # ✅ Separate UserProfile & Outlets from campaign_outlets
#                 user_profiles = []
#                 outlets = []
#                 for outlet_id in campaign_outlets:
#                     if outlet_id.startswith("main-"):
#                         user_profile_id = outlet_id.replace("main-", "")
#                         user_profile = UserProfile.objects.filter(id=user_profile_id).first()
#                         if user_profile:
#                             user_profiles.append(user_profile)
#                     elif outlet_id.startswith("sub-"):
#                         outlet_id = outlet_id.replace("sub-", "")
#                         outlet = Outlet.objects.filter(id=outlet_id).first()
#                         if outlet:
#                             outlets.append(outlet)

#                 # ✅ Save campaign
#                 campaign = serializer.save(
#                     user_profile=self.request.user.profile,
#                     image_url=image_url,
#                     reward_choice=reward_choice,
#                     profession=profession,
#                     campaign_type=campaign_type,
#                     reward_choice_text=request.data.get("campaign_reward_choice_text"),
#                     message=request.data.get("campaign_message"),
#                     expiry_date=request.data.get("campaign_expiry_date"),
#                     button_url=request.data.get("button_url")
#                 )
                
#                 # ✅ Add many-to-many relationships
#                 campaign.channels.set(channels)
#                 campaign.outlets.set(outlets)

#                 # ✅ Sending messages to customers
#                 customers = []
#                 for profile in user_profiles:
#                     customers.extend(profile.outlets.first().feedbacks.all())

#                 for outlet in outlets:
#                     customers.extend(outlet.feedbacks.all())

#                 for customer in customers:
#                     if campaign.channel_type in ["whatsapp", "all"]:
#                         send_whatsapp_message(customer.whatsapp_number, campaign.message, campaign.image_url, campaign.button_url)
#                     if campaign.channel_type in ["email", "all"]:
#                         send_email_message(customer.email, campaign.message, campaign.image_url, campaign.button_url)
#                     if campaign.channel_type in ["sms", "all"]:
#                         send_sms_message(customer.whatsapp_number, campaign.message)

#                 return Response({
#                     "status": True,
#                     "message": "Campaign created successfully",
#                     "data": {"image_url": image_url}
#                 }, status=status.HTTP_201_CREATED)

#             except Exception as e:
#                 return Response({"status": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         return Response({"status": False, "message": "Invalid data", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

#     def process_images(self, bg_image, logo_image):
#         """Overlay the logo on the background image and return as base64."""
#         try:
#             from io import BytesIO
#             from PIL import Image
#             import base64

#             bg_image_pil = Image.open(bg_image).convert("RGBA")
#             logo_image_pil = Image.open(logo_image).convert("RGBA")

#             # Resize logo
#             logo_image_pil = logo_image_pil.resize((1000, 1000))

#             # Position logo at bottom-right corner
#             position = (bg_image_pil.width - logo_image_pil.width - 10, bg_image_pil.height - logo_image_pil.height - 10)
#             bg_image_pil.paste(logo_image_pil, position, logo_image_pil)

#             # Convert to base64
#             buffered = BytesIO()
#             bg_image_pil.save(buffered, format="PNG")
#             return base64.b64encode(buffered.getvalue()).decode("utf-8")

#         except Exception as e:
#             raise ValueError(f"Image processing error: {e}")

#     def upload_image_to_imgbb(self, image_data):
#         """Upload image to ImgBB and return URL."""
#         import requests
#         from django.conf import settings

#         url = "https://api.imgbb.com/1/upload"
#         payload = {"key": settings.IMGBB_API_KEY, "image": image_data}
#         response = requests.post(url, data=payload)

#         if response.status_code == 200:
#             return response.json()["data"]["url"]
#         return None


class CampaignListCreateView(generics.ListCreateAPIView):
    """API to list all campaigns or create a new campaign"""

    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']
    parser_classes = [MultiPartParser, FormParser,JSONParser]  # ✅ Support file uploads

    def get_queryset(self):
        return Campaign.objects.filter(is_deleted=False).order_by('-id')[:5]

    @swagger_auto_schema(
        operation_description="Retrieve all campaigns",
        responses={200: CampaignSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        """Return all campaigns with a structured response"""
        try:
            queryset = self.get_queryset()
            serializer = GetCampaignSerializer(queryset, many=True)

            return Response({
                "status": True,
                "message": "Campaigns retrieved successfully",
                "data": {
                    "campaigns": serializer.data  # ✅ Consistent structured response
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": False,
                "message": f"Error retrieving campaigns: {str(e)}",
                "data": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
  
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("campaign_name", openapi.IN_FORM, description="Campaign Name", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("campaign_message", openapi.IN_FORM, description="Campaign Message", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("campaign_expiry_date", openapi.IN_FORM, description="Campaign Expiry Date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("button_url", openapi.IN_FORM, description="Call-to-Action URL", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("campaign_type", openapi.IN_FORM, description="Campaign Type ID", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter("reward_choice", openapi.IN_FORM, description="Reward Choice ID", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("campaign_reward_choice_text", openapi.IN_FORM, description="Campaign Reward choice detail", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter("profession", openapi.IN_FORM, description="Profession ID", type=openapi.TYPE_INTEGER, required=False),
            openapi.Parameter("campaign_channel", openapi.IN_FORM, description="List of Channel IDs", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_INTEGER), required=True),
            openapi.Parameter("campaign_outlets", openapi.IN_FORM, description="List of Outlet IDs (Format: main-1, sub-2)", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), required=True),
            openapi.Parameter("campaign_bg_image", openapi.IN_FORM, description="Campaign Background Image", type=openapi.TYPE_FILE, required=True),
            openapi.Parameter("campaign_logo", openapi.IN_FORM, description="Campaign Logo Image", type=openapi.TYPE_FILE, required=True),
        ],
        responses={201: "Campaign Created Successfully", 400: "Bad Request"},
    )
    def create(self, request, *args, **kwargs):
        """Create a new campaign with structured response"""
        # serializer = self.get_serializer(data=request.data)
        # print(request.data)

        # if serializer.is_valid():
        try:
                # validated_data = serializer.validated_data

                # ✅ Extract and convert channel IDs from request (Fix applied)
                # campaign_channels = list(map(int, request.data.get("campaign_channel", "").split(","))) if request.data.get("campaign_channel") else []
                campaign_channel_data = request.data.get("campaign_channel")

                if isinstance(campaign_channel_data, str):  # If comma-separated string
                    campaign_channels = list(map(int, campaign_channel_data.split(",")))
                elif isinstance(campaign_channel_data, list):  # If list format
                    campaign_channels = list(map(int, campaign_channel_data))
                else:
                    campaign_channels = []  # Default empty list if no valid input

                # print(campaign_channels, type(campaign_channels), "campaign_channels")
                # ✅ Extract and convert outlet IDs properly (Fix applied)
                import json
                campaign_outlets = json.loads(request.data.get("campaign_outlets", "[]"))

                user_profiles, outlets = [], []

                for outlet_id in campaign_outlets:
                    if outlet_id.startswith("main-"):  # Extract UserProfile ID
                        user_profile_id = outlet_id.replace("main-", "")
                        if user_profile_id.isdigit():
                            user_profile = UserProfile.objects.filter(id=int(user_profile_id)).first()
                            if user_profile:
                                user_profiles.append(user_profile)
                    elif outlet_id.startswith("sub-"):  # Extract Outlet ID
                        outlet_id = outlet_id.replace("sub-", "")
                        if outlet_id.isdigit():
                            outlet = Outlet.objects.filter(id=int(outlet_id)).first()
                            if outlet:
                                outlets.append(outlet)
                # print(user_profiles, outlets)
                # ✅ Extract Foreign Keys properly
                campaign_type = CampaignType.objects.filter(id=int(request.data.get("campaign_type", 0))).first()
                reward_choice = RewardChoice.objects.filter(id=int(request.data.get("reward_choice", 0))).first()
                profession = Profession.objects.filter(id=int(request.data.get("profession", 0))).first()

                # ✅ Extract images
                bg_image = request.FILES.get("campaign_bg_image")
                logo_image = request.FILES.get("campaign_logo")

                if not (bg_image and logo_image):
                    return Response({"status": False, "message": "Both background and logo images are required"}, status=status.HTTP_400_BAD_REQUEST)

                # ✅ Process images (overlay logo on background)
                final_image_b64 = self.process_images(bg_image, logo_image)
                # ✅ Upload to ImgBB
                image_url = self.upload_image_to_imgbb(final_image_b64)
                if not image_url:
                    return Response({"status": False, "message": "Image upload failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                # ✅ Create Campaign
                campaign = Campaign.objects.create(
                    user_profile=request.user.profile,
                    name=request.data.get("name"),
                    message=request.data.get("campaign_message"),
                    expiry_date=request.data.get("campaign_expiry_date"),
                    button_url=request.data.get("button_url"),
                    reward_choice_text=request.data.get("campaign_reward_choice_text"),
                    campaign_type=campaign_type,
                    reward_choice=reward_choice,
                    profession=profession,
                    bg_image=bg_image,
                    logo=logo_image,
                    image_url=image_url
                )
                print("logo_image",campaign.logo)
                # ✅ Assign Many-to-Many relations
                campaign.channels.set(Channel.objects.filter(id__in=campaign_channels))
                campaign.outlets.set(outlets)

                # ✅ Send campaign messages
                self.send_campaign_messages(campaign)

                return Response({
                    "status": True,
                    "message": "Campaign created successfully",
                    "data": {
                        "campaign_name": campaign.name,
                        "campaign_message": campaign.message,
                        "campaign_expiry_date": campaign.expiry_date,
                        "image_url": image_url,
                        "button_url": campaign.button_url,
                        "reward_choice": reward_choice.name if reward_choice else "",
                        "profession": profession.name if profession else "",
                        "campaign_type": campaign_type.name if campaign_type else "",
                        "campaign_channels": campaign_channels,
                        "campaign_outlets": campaign_outlets
                    }
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
                    return Response({"status": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # return Response({"status": False, "message": "Invalid data", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


    # def process_images(self, bg_image, logo_image):
    #     """Overlay the logo on the background image and return as base64."""
    #     try:
    #         bg_image_pil = Image.open(bg_image).convert("RGBA")
    #         logo_image_pil = Image.open(logo_image).convert("RGBA")

    #         # Resize logo proportionally
    #         max_logo_size = min(bg_image_pil.width // 3, bg_image_pil.height // 3)
    #         logo_image_pil.thumbnail((max_logo_size, max_logo_size), Image.LANCZOS)

    #         # Position logo at center-bottom
    #         position = (
    #             (bg_image_pil.width - logo_image_pil.width) // 2,
    #             bg_image_pil.height - logo_image_pil.height - 20
    #         )
    #         bg_image_pil.paste(logo_image_pil, position, logo_image_pil)

    #         # Convert to base64
    #         buffered = BytesIO()
    #         bg_image_pil.save(buffered, format="PNG")
    #         return base64.b64encode(buffered.getvalue()).decode("utf-8")

    #     except Exception as e:
    #         raise ValueError(f"Image processing error: {e}")

    def process_images(self, bg_image, logo_image):
        """Overlay the logo on the background image and return as base64."""
        try:
            from io import BytesIO
            from PIL import Image
            import base64

            # Read images
            bg_image_pil = Image.open(bg_image).convert("RGBA")
            logo_image_pil = Image.open(logo_image).convert("RGBA")

            # Resize logo
            logo_image_pil = logo_image_pil.resize((1000, 1000))

            # Position logo at bottom-right corner
            position = (bg_image_pil.width - logo_image_pil.width - 10, bg_image_pil.height - logo_image_pil.height - 10)
            bg_image_pil.paste(logo_image_pil, position, logo_image_pil)

            # Convert to base64
            buffered = BytesIO()
            bg_image_pil.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")

        except Exception as e:
            raise ValueError(f"Image processing error: {e}")

    # def upload_image_to_imgbb(self, image_data):
    #     """Upload image to ImgBB and return URL."""
    #     if not hasattr(settings, "IMGBB_API_KEY") or not settings.IMGBB_API_KEY:
    #         raise ValueError("IMGBB API Key is missing in settings.")

    #     url = "https://api.imgbb.com/1/upload"
    #     payload = {"key": settings.IMGBB_API_KEY, "image": image_data}
        
    #     try:
    #         response = requests.post(url, data=payload)
    #         response.raise_for_status()  # Raises HTTPError if status is not 200
    #         return response.json().get("data", {}).get("url")
    #     except requests.RequestException as e:
    #         raise ValueError(f"Failed to upload image to ImgBB: {e}")
        
    def upload_image_to_imgbb(self, image_data):
        """Upload image to ImgBB and return URL."""
        import requests
        from django.conf import settings

        url = "https://api.imgbb.com/1/upload"
        payload = {"key": settings.IMGBB_API_KEY, "image": image_data}
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            return response.json()["data"]["url"]
        return None

    # def send_campaign_messages(self, campaign):
    #     """Send WhatsApp, Email, and SMS messages to customers."""
    #     customers = set()  # Use a set to avoid duplicate customers

    #     for outlet in campaign.outlets.all():
    #         customers.update(outlet.feedbacks.all())
    #         print("Customers from outlet", outlet.id, ":", outlet.feedbacks.all())

    #     for customer in customers:
    #         for channel in campaign.channels.all():
    #             print("Sending message via channel:", channel)
    #             if channel.id == 1:  # WhatsApp
    #                 send_whatsapp_message(customer.phone_number, campaign.message, campaign.image_url, campaign.button_url)
    #                 print("WhatsApp sent to", customer.phone_number)
    #             elif channel.id == 2:  # Email
    #                 send_email_message(customer.email, campaign.message, campaign.image_url, campaign.button_url)
    #                 print("Email sent to", customer.email)
    #             elif channel.id == 3:  # SMS
    #                 send_sms_message(customer.phone_number, campaign.message)

    def send_campaign_messages(self, campaign):
        """Send WhatsApp, Email, and SMS messages to customers."""
        
        customers = set()  # Use a set to avoid duplicate customers

        # ✅ Fetch unique customers from campaign outlets
        for outlet in campaign.outlets.all():
            outlet_customers = Customer.objects.all().distinct()
            customers.update(outlet_customers)
            # print(f"Customers from outlet {outlet.id}: {outlet_customers}")

        # ✅ Send messages based on campaign channels
        for customer in customers:
            for channel in campaign.channels.all():

                # ✅ Send WhatsApp Message
                if channel.id == 1 and customer.whatsapp_number:
                    send_whatsapp_message(customer.whatsapp_number, campaign.message, campaign.image_url, campaign.button_url)

                # ✅ Send Email
                elif channel.id == 2 and customer.email:
                    send_email_message(customer.email, campaign.message, campaign.image_url, campaign.button_url)

                # ✅ Send SMS
                elif channel.id == 3 and customer.whatsapp_number:
                    send_sms_message(customer.whatsapp_number, campaign.message)

class CampaignRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """API to retrieve, update, or delete a campaign"""
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Campaign.objects.filter(is_deleted=False)

    def retrieve(self, request, *args, **kwargs):
        """Return a single campaign with complete response"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                "status": True,
                "message": "Campaign retrieved successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": False,
                "message": f"Error retrieving campaign: {str(e)}",
                "data": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Update campaign details and return complete response"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response({
                    "status": True,
                    "message": "Campaign updated successfully",
                    "data": serializer.data  # ✅ Returning complete updated response
                }, status=status.HTTP_200_OK)

            return Response({
                "status": False,
                "message": "Invalid data provided",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "status": False,
                "message": f"Error updating campaign: {str(e)}",
                "data": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Soft delete a campaign and return full response"""
        try:
            instance = self.get_object()
            instance.is_deleted = True
            instance.save()
            serializer = self.get_serializer(instance)  # ✅ Return deleted campaign data
            return Response({
                "status": True,
                "message": "Campaign deleted successfully",
                "data": serializer.data  # ✅ Returning full campaign details after deletion
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": False,
                "message": f"Error deleting campaign: {str(e)}",
                "data": None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ProfessionViewSet(ModelViewSet):
    queryset = Profession.objects.all()
    serializer_class = ProfessionSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": True,
            "message": "List of all professions",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class RewardChoiceViewSet(ModelViewSet):
    queryset = RewardChoice.objects.all()
    serializer_class = RewardChoiceSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": True,
            "message": "List of all reward choices",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class CampaignTypeViewSet(ModelViewSet):
    queryset = CampaignType.objects.all()
    serializer_class = CampaignTypeSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": True,
            "message": "List of all campaign types",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



# class OutletListViewSet(ModelViewSet):
#     """ViewSet for listing user profiles with their sub_outlets"""

#     queryset = UserProfile.objects.all()
#     serializer_class = GetUserProfileSerializer

#     def list(self, request, *args, **kwargs):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)
        
#         return Response({
#             "status": True,
#             "message": "User profiles with outlets retrieved successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)





# class OutletListViewSet(ModelViewSet):
#     """ViewSet for listing user profiles with their sub_outlets"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = GetUserProfileSerializer

#     def get_queryset(self):
#         """Filter data to return only the logged- in user's profile"""
#         return UserProfile.objects.filter(user=self.request.user)

#     def list(self, request, *args, **kwargs):
#         queryset = self.get_queryset()
#         serializer = self.get_serializer(queryset, many=True)

#         return Response({
#             "status": True,
#             "message": "User profile with outlets retrieved successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)



class OutletListViewSet(ModelViewSet):
    """ViewSet for listing user profiles with their sub_outlets"""
    permission_classes = [IsAuthenticated]
    serializer_class = GetUserProfileSerializer

    def get_queryset(self):
        """Filter data to return only the logged-in user's profile"""
        return UserProfile.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        response_data = []

        for profile in queryset:
            # ✅ Add the main outlet (UserProfile)
            response_data.append({
                "id": f"main-{profile.id}",  # Unique ID with prefix
                "name": f"{profile.brand_name} (Main Outlet)"
            })

            # ✅ Add sub_outlets (Outlets under UserProfile)
            for outlet in profile.outlets.all():
                response_data.append({
                    "id": f"sub-{outlet.id}",  # Unique ID with prefix
                    "name": f"{outlet.name}"  # Indent sub-outlets
                })

        return Response({
            "status": True,
            "message": "User profile with outlets retrieved successfully",
            "data": response_data
        }, status=status.HTTP_200_OK)




