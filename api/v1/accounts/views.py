from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from api.v1.models import UserProfile, UserMaster
from .serializers import UserSignupSerializer, UserProfileSerializer, UserLoginSerializer
from rest_framework.response import Response
from social_core.exceptions import AuthCanceled, AuthForbidden
from rest_framework.views import APIView
from social_core.backends.google import GoogleOAuth2
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import requests

class UserSignupView(APIView):
    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # This saves the user instance

            # Check if the user profile already exists
            UserProfile.objects.get_or_create(user=user)

            return Response({"status": True,'message': 'User created successfully!', "data":serializer.data}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username_or_email = serializer.validated_data['username_or_email']
        password = serializer.validated_data['password']

        user = authenticate(username=username_or_email, password=password) or \
               authenticate(email=username_or_email, password=password)

        if not user.is_active:
            return Response({'detail': 'Account is not activated yet.'}, status=status.HTTP_403_FORBIDDEN)
        
        if user is None:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return self.request.user.profile

    def update(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)





UserMaster = get_user_model()

class SocialLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider')
        token = request.data.get('token')

        if provider == 'google':
            return self.google_login(token)
        return Response({'error': 'Invalid provider'}, status=400)

    def google_login(self, token):
        # Validate the token with Google
        response = requests.get(f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}')
        if response.status_code != 200:
            return Response({'error': 'Invalid token'}, status=400)

        user_info = response.json()
        email = user_info.get('email')
        username = user_info.get('name')

        # Check if user exists
        user, created = UserMaster.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'is_active': True  # Set as active if created or approved by super admin
            }
        )

        # Create JWT tokens for the user
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
