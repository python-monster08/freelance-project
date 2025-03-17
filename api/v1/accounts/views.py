from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from api.v1.models import *
from .serializers import *
import requests
from django.contrib.auth.hashers import check_password
from datetime import datetime, timedelta
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import pandas as pd
from django.core.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from django.db import IntegrityError, DatabaseError
from django.core.exceptions import ObjectDoesNotExist




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
                "message": "User already exists"
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

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            # Get token expiry times
            access_token_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
            refresh_token_lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
            is_profile_update = user.is_profile_update
            access_token_expiry = datetime.now() + access_token_lifetime
            refresh_token_expiry = datetime.now() + refresh_token_lifetime

            return Response({
                "status": True,
                "message": "Login successful",
                "is_profile_updated": is_profile_update,
                "role_id": user.role.id,
                "role_name": user.role.role,
                "access": str(access_token),
                "access_expires_at": access_token_expiry.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "refresh": str(refresh),
                "refresh_expires_at": refresh_token_expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
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
            }, status=status.HTTP_200_OK)

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

    def list(self, request, *args, **kwargs):
        """Custom list method to return structured response."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

            # Check if data is empty and respond accordingly
            if not data:
                return Response({
                    "status": True,
                    "message": "No outlets found",
                    "data": []
                }, status=status.HTTP_200_OK)

            return Response({
                "status": True,
                "message": "Data fetched successfully",
                "data": data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

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
        data =  Outlet.objects.filter(user_profile=self.request.user.profile)
        return Response({"status": True, "data": OutletSerializer(data, many=True).data}, status=status.HTTP_200_OK)

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

# class UserProfileView(generics.RetrieveUpdateAPIView):
#     serializer_class = UserProfileSerializer
#     permission_classes = [IsAuthenticated]

#     def get_serializer_class(self):
#         if self.action in ["update", "partial_update"]:
#             return CustomerFeedbackUpdateSerializer
#         return CustomerFeedbackListSerializer

#     def get_object(self):
#         try:
#             return self.request.user.profile
#         except Exception as e:
#             return Response({
#                 "status": False,
#                 "message": str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def retrieve(self, request, *args, **kwargs):
#         """Retrieve user profile with additional details."""
#         try:
#             user = request.user
#             profile = user.profile
#             serializer = self.get_serializer(profile)

#             return Response({
#                 "status": True,
#                 "message": "User profile retrieved successfully",
#                 "data": {
#                     "username": user.username,
#                     "email": user.email,
#                     "first_name": user.first_name,
#                     "last_name": user.last_name,
#                     "profile": serializer.data
#                 }
#             }, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({
#                 "status": False,
#                 "message": str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def update(self, request, *args, **kwargs):
#         """Update user profile including password change."""
#         try:
#             user = request.user
#             data = request.data

#             # Update User fields
#             user.username = data.get("username", user.username)
#             user.email = data.get("email", user.email)
#             user.first_name = data.get("first_name", user.first_name)
#             user.last_name = data.get("last_name", user.last_name)
#             user.is_profile_update = True  # Mark profile as complete

#             # Password update logic
#             if "old_password" in data and "new_password" in data:
#                 old_password = data["old_password"]
#                 new_password = data["new_password"]

#                 if not check_password(old_password, user.password):
#                     return Response({
#                         "status": False,
#                         "message": "Old password is incorrect."
#                     }, status=status.HTTP_400_BAD_REQUEST)

#                 user.set_password(new_password)

#             user.save()

#             # Update Profile fields
#             profile = user.profile
#             serializer = self.get_serializer(profile, data=request.data, partial=True)
#             if serializer.is_valid():
#                 serializer.save()
#                 return Response({
#                     "status": True,
#                     "message": "User profile updated successfully",
#                     "data": {
#                         "username": user.username,
#                         "email": user.email,
#                         "first_name": user.first_name,
#                         "last_name": user.last_name,
#                         "profile": serializer.data
#                     }
#                 }, status=status.HTTP_200_OK)

#             return Response({
#                 "status": False,
#                 "message": str(serializer.errors)
#             }, status=status.HTTP_400_BAD_REQUEST)

#         except Exception as e:
#             return Response({
#                 "status": False,
#                 "message": str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class UpdateProfileView(generics.RetrieveUpdateDestroyAPIView):
#     """
#     API for retrieving, updating, and soft deleting user profiles
#     - Retrieve includes UserProfile + Outlets + UserMaster fields
#     - Update modifies profile but NOT outlets
#     - Delete only sets `is_deleted = True`
#     """
#     serializer_class = UpdateProfileSerializer
#     permission_classes = [IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser, JSONParser]  # Supports file uploads

#     def get_object(self):
#         """Retrieve the authenticated user's profile, ensuring it exists"""
#         return get_object_or_404(UserProfile, user=self.request.user, is_deleted=False)

    
#     def perform_update(self, serializer):
#         """Update UserMaster fields separately before saving UserProfile"""
#         profile = serializer.instance
#         user = profile.user

#         user_data = self.request.data
#         user.first_name = user_data.get("first_name", user.first_name)
#         user.last_name = user_data.get("last_name", user.last_name)
#         user.phone_number = user_data.get("phone_number", user.phone_number)
#         user.is_profile_update = True
#         user.save()

#         # Remove number_of_outlets update logic
#         profile_data = serializer.validated_data

#         serializer.save(**profile_data)

#     def perform_destroy(self, instance):
#         """Soft delete profile (set is_deleted = True)"""
#         instance.is_deleted = True
#         instance.user.is_active = False
#         instance.user.save()
#         instance.save()
#         return Response({"message": "Profile deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class UpdateProfileView(generics.RetrieveUpdateDestroyAPIView):
    """
    API for retrieving, updating, and soft deleting user profiles
    - Retrieve includes UserProfile + Outlets + UserMaster fields
    - Update modifies profile but NOT outlets
    - Delete only sets `is_deleted = True`
    """
    serializer_class = UpdateProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Supports file uploads

    def get_object(self):
        """Retrieve the authenticated user's profile, ensuring it exists"""
        return get_object_or_404(UserProfile, user=self.request.user, is_deleted=False)

    def retrieve(self, request, *args, **kwargs):
        """Custom response format for retrieving profile"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {"status": True, "message": "Profile retrieved successfully", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        except ObjectDoesNotExist:
            return Response(
                {"status": False, "message": "Profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            return Response(
                {"status": False, "message": "An unexpected error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_update(self, serializer):
        """Update UserMaster fields separately before saving UserProfile"""
        profile = serializer.instance
        user = profile.user

        user_data = self.request.data
        user.first_name = user_data.get("first_name", user.first_name)
        user.last_name = user_data.get("last_name", user.last_name)
        user.phone_number = user_data.get("phone_number", user.phone_number)
        user.is_profile_update = True
        user.save()

        profile_data = serializer.validated_data
        serializer.save(**profile_data)

    def update(self, request, *args, **kwargs):
        """Custom response format after updating the profile"""
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(
                {"status": True, "message": "Profile updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        except ValidationError as e:
            return Response(
                {"status": False, "message": "Validation error", "data": e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            return Response(
                {"status": False, "message": "An error occurred while updating profile", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_destroy(self, instance):
        """Soft delete profile (set is_deleted = True)"""
        instance.is_deleted = True
        instance.user.is_active = False
        instance.user.save()
        instance.save()

    def destroy(self, request, *args, **kwargs):
        """Custom response format for soft deletion"""
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(
                {"status": True, "message": "Profile deleted successfully", "data": {}},
                status=status.HTTP_200_OK
            )
        except ObjectDoesNotExist:
            return Response(
                {"status": False, "message": "Profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            return Response(
                {"status": False, "message": "An error occurred while deleting profile", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




class CustomerCreateView(APIView):
    """API to add, update, and delete customers."""

    def post(self, request):
        """Add single or multiple customers."""
        if not request.user or not request.user.is_authenticated:
            return Response({"status": False, "message": "Authentication required!"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user_profile = UserProfile.objects.get(user=request.user.id)
        except UserProfile.DoesNotExist:
            return Response({"status": False, "message": "User profile not found!"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = request.data

        if isinstance(data, list):
            serializer = AddSingleCustomerSerializer(data=data, many=True)
        else:
            serializer = AddSingleCustomerSerializer(data=data)

        if serializer.is_valid():
            try:
                customers = serializer.save(msme=user_profile)
                return Response({
                    "status": True,
                    "message": "Customers created successfully!" if isinstance(customers, list) else "Customer created successfully!",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response({"status": False, "message": "Integrity error while saving data!"}, status=status.HTTP_400_BAD_REQUEST)
            except DatabaseError:
                return Response({"status": False, "message": "Database error!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"status": False, "message": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": False, "message": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        """Update an existing customer by ID."""
        if not pk:
            return Response({"status": False, "message": "Customer ID is required!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response({"status": False, "message": "Customer not found!"}, status=status.HTTP_404_NOT_FOUND)
        except DatabaseError:
            return Response({"status": False, "message": "Database error!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = AddSingleCustomerSerializer(customer, data=request.data, partial=True)

        if serializer.is_valid():
            try:
                serializer.save()
                return Response({"status": True, "message": "Customer updated successfully!", "data": serializer.data}, status=status.HTTP_200_OK)
            except IntegrityError:
                return Response({"status": False, "message": "Integrity error while updating data!"}, status=status.HTTP_400_BAD_REQUEST)
            except DatabaseError:
                return Response({"status": False, "message": "Database error!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                return Response({"status": False, "message": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": False, "message": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        """Delete a customer by ID."""
        if not pk:
            return Response({"status": False, "message": "Customer ID is required!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(pk=pk)
            customer.delete()
            return Response({"status": True, "message": "Customer deleted successfully!"}, status=status.HTTP_200_OK)
        except Customer.DoesNotExist:
            return Response({"status": False, "message": "Customer not found!"}, status=status.HTTP_404_NOT_FOUND)
        except DatabaseError:
            return Response({"status": False, "message": "Database error!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CustomerUploadView(APIView):
    """API to upload customer data via an Excel or CSV file"""
    
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"status": False, "message": "No file uploaded!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Validate file extension
            file_extension = file.name.split(".")[-1].lower()
            if file_extension in ["xlsx", "xls"]:
                df = pd.read_excel(file)
            elif file_extension == "csv":
                df = pd.read_csv(file)
            else:
                return Response(
                    {"status": False, "message": "Unsupported file format. Please upload an Excel or CSV file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check required columns
            required_columns = {"first_name", "last_name", "email", "whatsapp_number", "gender", "dob", "anniversary_date", "city"}
            missing_columns = required_columns - set(df.columns)
            if missing_columns:
                return Response(
                    {"status": False, "message": f"Missing required columns: {missing_columns}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Fetch user profile
            try:
                user_profile = UserProfile.objects.get(user=request.user.id)
            except UserProfile.DoesNotExist:
                return Response({"status": False, "message": "User profile not found!"}, status=status.HTTP_400_BAD_REQUEST)

            customers = []
            for _, row in df.iterrows():
                try:
                    customer = Customer(
                        msme=user_profile,  # Assign logged-in MSME
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        email=row["email"],
                        whatsapp_number=row["whatsapp_number"],
                        gender=row["gender"],
                        dob=row["dob"] if pd.notna(row["dob"]) else None,
                        anniversary_date=row["anniversary_date"] if pd.notna(row["anniversary_date"]) else None,
                        city=row["city"],
                    )
                    customer.full_clean()  # Validate fields
                    customers.append(customer)
                except ValidationError as e:
                    return Response({"status": False, "message": f"Data validation error: {e.message_dict}"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    return Response({"status": False, "message": f"Unexpected error while processing row: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            if customers:
                try:
                    Customer.objects.bulk_create(customers)
                    return Response({"status": True, "message": "Customers uploaded successfully!"}, status=status.HTTP_201_CREATED)
                except IntegrityError:
                    return Response({"status": False, "message": "Integrity error: Possible duplicate records."}, status=status.HTTP_400_BAD_REQUEST)
                except DatabaseError:
                    return Response({"status": False, "message": "Database error occurred!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as e:
                    return Response({"status": False, "message": f"Unexpected database error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"status": False, "message": "No valid customer data found!"}, status=status.HTTP_400_BAD_REQUEST)

        except pd.errors.EmptyDataError:
            return Response({"status": False, "message": "Uploaded file is empty!"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"status": False, "message": f"Invalid file format or data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
 

# Custom Pagination Class
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size =100

    def get_paginated_response(self, data):
        limit = self.request.query_params.get('page_size', 10)
        return Response({
            'status': True,
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'page_size':int(limit),
            'data': data
        })  

class CustomerListView(generics.ListAPIView):
    serializer_class = CustomerSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        """Retrieve customers for the authenticated user."""
        try:
            return Customer.objects.all().order_by('-id')
        except DatabaseError:
            return Response({"status": False, "message": "Database error occurred while fetching customers."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request, *args, **kwargs):
        """List customers with pagination and error handling."""
        try:
            queryset = self.get_queryset()
            if isinstance(queryset, Response):  # Return error response if `get_queryset()` failed
                return queryset  

            page = self.paginate_queryset(queryset)
            if page is not None:
                return self.get_paginated_response(self.get_serializer(page, many=True).data)

            return Response({
                "status": True,
                "message": "Customers retrieved successfully",
                "data": self.get_serializer(queryset, many=True).data
            }, status=status.HTTP_200_OK)

        except DatabaseError:
            return Response({"status": False, "message": "Database error occurred while fetching customers."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CustomerRetrieveView(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific customer by ID with error handling."""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            return Response({
                "status": True,
                "message": "Customer retrieved successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Customer.DoesNotExist:
            return Response({"status": False, "message": "Customer not found!"}, 
                            status=status.HTTP_404_NOT_FOUND)

        except DatabaseError:
            return Response({"status": False, "message": "Database error occurred while retrieving customer."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomerFeedbackViewSet(ModelViewSet):
    queryset = CustomerFeedback.objects.all().order_by("-created_at")
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "list":
            return CustomerFeedbackListSerializer
        elif self.action == "create":
            return CustomerFeedbackCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CustomerFeedbackUpdateSerializer
        return CustomerFeedbackListSerializer

    def list(self, request, *args, **kwargs):
        """Fetch all customer feedback entries."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "status": True,
                    "message": "Feedback list fetched successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except DatabaseError:
            return Response({"status": False, "message": "Database error while fetching feedback list."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        """Fetch a single feedback entry by ID."""
        try:
            instance = self.get_object()
            
            serializer = self.get_serializer(instance)
            return Response(
                {
                    "status": True,
                    "message": "Feedback retrieved successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except CustomerFeedback.DoesNotExist:
            return Response({"status": False, "message": "Feedback not found!"}, 
                            status=status.HTTP_404_NOT_FOUND)
        except DatabaseError:
            return Response({"status": False, "message": "Database error while fetching feedback."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """Create new customer feedback."""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                feedback = serializer.save()
                return Response(
                    {
                        "status": True,
                        "message": "Feedback submitted successfully",
                        "data": CustomerFeedbackListSerializer(feedback).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            return Response({"status": False, "message": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"status": False, "message": f"Validation error: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            return Response({"status": False, "message": "Database error while saving feedback."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """Update existing feedback."""
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                feedback = serializer.save()
                return Response(
                    {
                        "status": True,
                        "message": "Feedback updated successfully",
                        "data": CustomerFeedbackListSerializer(feedback).data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response({"status": False, "message": str(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        except CustomerFeedback.DoesNotExist:
            return Response({"status": False, "message": "Feedback not found!"}, 
                            status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"status": False, "message": f"Validation error: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            return Response({"status": False, "message": "Database error while updating feedback."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, *args, **kwargs):
        """Delete feedback by ID."""
        try:
            instance = self.get_object()
            instance.delete()
            return Response({"status": True, "message": "Feedback deleted successfully"}, 
                            status=status.HTTP_204_NO_CONTENT)
        except CustomerFeedback.DoesNotExist:
            return Response({"status": False, "message": "Feedback not found!"}, 
                            status=status.HTTP_404_NOT_FOUND)
        except DatabaseError:
            return Response({"status": False, "message": "Database error while deleting feedback."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"status": False, "message": f"Unexpected error: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
