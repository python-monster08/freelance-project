from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.v1.models import *
from .serializers import *
from .utils import *
from rest_framework.viewsets import ModelViewSet

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from io import BytesIO
from PIL import Image
import base64
import requests

from api.v1.models import Campaign
from .serializers import CampaignSerializer
from .utils import *

class CampaignListCreateView(generics.ListCreateAPIView):
    """API to list all campaigns or create a new campaign"""

    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Campaign.objects.filter(is_deleted=False)

    def list(self, request, *args, **kwargs):
        """Return all campaigns with a structured response"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "status": True,
            "message": "Campaigns retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """Create a new campaign with structured response"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                # Extract images from request (multipart/form-data)
                bg_image = request.FILES.get("bgimage")
                logo_image = request.FILES.get("logoImage")
                # button_url = request.data.get("button_url")

                if not (bg_image and logo_image):
                    return Response({"status": False, "message": "Both bgimage and logoImage are required", "data": []}, status=status.HTTP_400_BAD_REQUEST)

                # Process images (overlay logo on background)
                final_image_b64 = self.process_images(bg_image, logo_image)

                # Upload to ImgBB
                image_url = self.upload_image_to_imgbb(final_image_b64)
                if not image_url:
                    return Response({"status": False, "message": "Image upload failed", "data": []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Save campaign
                campaign = serializer.save(user_profile=self.request.user.profile, image_url=image_url)
                print("Campaign created:", campaign)

                # Get customers associated with the user's outlets
                customers = campaign.user_profile.outlets.first().feedbacks.all()
                print("Customers:", customers)

                # Send messages based on channel type
                for customer in customers:
                    if campaign.channel_type in ["whatsapp", "all"]:
                        send_whatsapp_message(customer.whatsapp_number, campaign.message, campaign.image_url, campaign.button_url)
                        print("WhatsApp sent to", customer.whatsapp_number)
                    if campaign.channel_type in ["email", "all"]:
                        send_email_message(customer.email, campaign.message, campaign.image_url, campaign.button_url)
                        print("Email sent to", customer.email)
                    if campaign.channel_type in ["sms", "all"]:
                        send_sms_message(customer.whatsapp_number, campaign.message)
                        print("SMS sent to", customer.whatsapp_number)

                return Response({
                    "status": True,
                    "message": "Campaign created successfully",
                    "data": {"image_url": image_url}
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"status": False, "message": str(e), "data": []}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": False, "message": "Invalid data", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

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



class CampaignRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """API to retrieve, update, or delete a campaign"""

    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Campaign.objects.filter(is_deleted=False)

    def retrieve(self, request, *args, **kwargs):
        """Return a single campaign"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            "status": True,
            "message": "Campaign retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        """Update campaign details"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": True,
                "message": "Campaign updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({"status": False, "message": "Invalid data", "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Soft delete a campaign"""
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({
            "status": True,
            "message": "Campaign deleted successfully",
            "data": []
        }, status=status.HTTP_200_OK)



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



class OutletListViewSet(ModelViewSet):
    """ViewSet for listing user profiles with their sub_outlets"""

    queryset = UserProfile.objects.all()
    serializer_class = GetUserProfileSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            "status": True,
            "message": "User profiles with outlets retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)