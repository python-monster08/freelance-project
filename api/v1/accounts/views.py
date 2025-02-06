from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from api.v1.models import *
from .serializers import *
import requests

UserMaster = get_user_model()

class UserSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = UserSignupSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()

                # Create UserProfile if not exists
                UserProfile.objects.get_or_create(user=user)

                return Response({
                    "status": True,
                    "message": "User created successfully!",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                "status": False,
                "message": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            username_or_email = serializer.validated_data['username_or_email']
            password = serializer.validated_data['password']

            user = authenticate(request, username=username_or_email, password=password)

            if user is None:
                return Response({
                    "status": False,
                    "message": "Invalid credentials"
                }, status=status.HTTP_401_UNAUTHORIZED)

            if not user.is_active:
                return Response({
                    "status": False,
                    "message": "Account is not activated yet."
                }, status=status.HTTP_403_FORBIDDEN)

            refresh = RefreshToken.for_user(user)
            return Response({
                "status": True,
                "message": "Login successful",
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            })

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SocialLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            provider = request.data.get('provider')
            token = request.data.get('token')

            if provider == 'google':
                return self.google_login(token)

            return Response({
                "status": False,
                "message": "Invalid provider"
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def google_login(self, token):
        try:
            response = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
            if response.status_code != 200:
                return Response({
                    "status": False,
                    "message": "Invalid token"
                }, status=status.HTTP_400_BAD_REQUEST)

            user_info = response.json()
            email = user_info.get('email')
            username = user_info.get('name')

            user, created = UserMaster.objects.get_or_create(
                email=email,
                defaults={'username': username, 'is_active': True}
            )

            refresh = RefreshToken.for_user(user)
            return Response({
                "status": True,
                "message": "Social login successful",
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            })

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OutletListCreateView(generics.ListCreateAPIView):
    serializer_class = OutletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the logged-in user's outlets."""
        return Outlet.objects.filter(user_profile=self.request.user.profile)

    def create(self, request, *args, **kwargs):
        """Custom create method to return a structured response."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            outlet = serializer.save(user_profile=self.request.user.profile)  # Assign user profile

            # Update outlet count
            self.request.user.profile.update_outlet_count()

            return Response({
                "status": True,
                "message": "Outlet created successfully!",
                "data": OutletSerializer(outlet).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class OutletDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OutletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Ensure users can only update/delete their own outlets"""
        return Outlet.objects.filter(user_profile=self.request.user.profile)

    def update(self, request, *args, **kwargs):
        """Custom update method for structured responses."""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({
                "status": True,
                "message": "Outlet updated successfully!",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Custom delete method for structured responses."""
        try:
            instance = self.get_object()
            instance.delete()

            # Update outlet count after deletion
            instance.user_profile.update_outlet_count()

            return Response({
                "status": True,
                "message": "Outlet deleted successfully!"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)



class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.profile
        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve user profile with additional details."""
        try:
            user = request.user
            profile = user.profile
            serializer = self.get_serializer(profile)

            return Response({
                "status": True,
                "message": "User profile retrieved successfully",
                "data": {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "profile": serializer.data
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Update user profile including password change."""
        try:
            user = request.user
            data = request.data

            # Update User fields
            user.username = data.get("username", user.username)
            user.email = data.get("email", user.email)
            user.first_name = data.get("first_name", user.first_name)
            user.last_name = data.get("last_name", user.last_name)

            # Password update logic
            if "old_password" in data and "new_password" in data:
                old_password = data["old_password"]
                new_password = data["new_password"]

                if not check_password(old_password, user.password):
                    return Response({
                        "status": False,
                        "message": "Old password is incorrect."
                    }, status=status.HTTP_400_BAD_REQUEST)

                user.set_password(new_password)

            user.save()

            # Update Profile fields
            profile = user.profile
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "status": True,
                    "message": "User profile updated successfully",
                    "data": {
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "profile": serializer.data
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "status": False,
                "message": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



