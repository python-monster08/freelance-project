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

                # Create MSMEProfile if not exists
                MSMEProfile.objects.get_or_create(user=user)

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
        return Outlet.objects.filter(user_profile=self.request.user.profile, is_deleted=False).order_by('-id')

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
        data =  Outlet.objects.filter(user_profile=self.request.user.profile, is_deleted=False)
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



class UpdateProfileView(generics.RetrieveUpdateDestroyAPIView):
    """
    API for retrieving, updating, and soft deleting user profiles
    - Retrieve includes MSMEProfile + Outlets + UserMaster fields
    - Update modifies profile but NOT outlets
    - Delete only sets `is_deleted = True`
    """
    serializer_class = UpdateProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Supports file uploads

    def get_object(self):
        """Retrieve the authenticated user's profile, ensuring it exists"""
        return get_object_or_404(MSMEProfile, user=self.request.user, is_deleted=False)

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
        """Update UserMaster fields separately before saving MSMEProfile"""
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
            user_profile = MSMEProfile.objects.get(user=request.user.id)
        except MSMEProfile.DoesNotExist:
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
                user_profile = MSMEProfile.objects.get(user=request.user.id)
            except MSMEProfile.DoesNotExist:
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




class MembershipPlanViewSet(ModelViewSet):
    # queryset = MembershipPlan.objects.filter(is_deleted=False)
    queryset = MembershipPlan.objects.filter(is_deleted=False)

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action in ["create", "update", "partial_update"]:
            return MembershipPlanCreateUpdateSerializer
        return MembershipPlanListSerializer

    def list(self, request, *args, **kwargs):
        """Retrieve all active membership plans with a consistent response"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": True,
            "message": "Membership Plans fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single membership plan with a consistent response"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            "status": True,
            "message": "Membership Plan fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """Handles single and bulk plan creation"""
        data = request.data

        if isinstance(data, list):  # Bulk creation
            serializer = self.get_serializer(data=data, many=True)
        else:  # Single creation
            serializer = self.get_serializer(data=data)

        if serializer.is_valid():
            instance = serializer.save()
            response_data = MembershipPlanListSerializer(instance).data  # Serialize with correct structure

            return Response({
                "status": True,
                "message": "Membership Plan created successfully",
                "data": response_data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "status": False,
            "message": "Validation error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Update a membership plan"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            instance = serializer.save()
            response_data = MembershipPlanListSerializer(instance).data  # Serialize with correct structure

            return Response({
                "status": True,
                "message": "Membership Plan updated successfully",
                "data": response_data
            }, status=status.HTTP_200_OK)

        return Response({
            "status": False,
            "message": "Validation error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


    def destroy(self, request, *args, **kwargs):
        """Soft delete a membership plan by setting is_deleted = True"""
        instance = self.get_object()
        instance.is_deleted = True  # Mark as deleted
        instance.save()

        return Response({
            "status": True,
            "message": "Membership Plan deleted successfully"
        }, status=status.HTTP_200_OK)


# Support System

class SupportSystemViewSet(ModelViewSet):
    """CRUD API for Support System"""

    queryset = SupportSystem.objects.filter(is_deleted=False, plan__is_active=True).order_by("id")

    def get_serializer_class(self):
        """Use different serializers for GET, POST, and PATCH/PUT"""
        if self.request.method == "GET":
            return SupportSystemGetSerializer
        if self.request.method == "POST":
            return SupportSystemCreateSerializer
        return SupportSystemUpdateSerializer

    def list(self, request, *args, **kwargs):
        """Retrieve all support system records with a structured response"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        support_table = [
            {
                "id": item["id"],
                "plan_name": item["plan_name"],
                "plan_support": item["plan_support"]
            }
            for item in serializer.data
        ]

        return Response(
            {"status": True, "message": "Membership Plan Support list retrieved successfully", "data": support_table},
            status=status.HTTP_200_OK
        )

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Retrieve a single support system record"""
        try:
            support_instance = self.get_object()
        except SupportSystem.DoesNotExist:
            return Response(
                {"status": False, "message": f"SupportSystem ID {pk} not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "status": True,
                "message": "Support System retrieved successfully!",
                "data": {
                    "id": support_instance.id,
                    "plan_name": support_instance.plan.name,
                    "plan_support": {
                        "support": support_instance.support,
                        "training": support_instance.training,
                        "staff_re_training": support_instance.staff_re_training,
                        "dedicated_poc": support_instance.dedicated_poc,
                    }
                }
            },
            status=status.HTTP_200_OK
        )

    def create(self, request, *args, **kwargs):
        """Create a new support system"""
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            support_instance = serializer.save()
            return Response(
                {
                    "status": True,
                    "message": "Support System Created!",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"status": False, "message": "Validation failed!", "data": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def update(self, request, pk=None, *args, **kwargs):
        """Update support system record (PUT or PATCH)"""
        try:
            support_instance = self.get_object()
        except SupportSystem.DoesNotExist:
            return Response(
                {"status": False, "message": f"SupportSystem ID {pk} not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(support_instance, data=request.data, partial=True)

        if serializer.is_valid():
            updated_instance = serializer.save()
            return Response(
                {
                    "status": True,
                    "message": "Support System Updated!",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {"status": False, "message": "Update failed!", "data": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, *args, **kwargs):
        """Soft delete instead of hard delete"""
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"status": True, "message": "Support System Deleted!", "data": []}, status=status.HTTP_200_OK)




# ****************************** Payment Order API ******************************
import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.mail import send_mail
from msme_marketing_analytics.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    user = request.user
    msme = get_object_or_404(MSMEProfile, user=user)
    plan_id = request.data.get("plan_id")
    plan = get_object_or_404(MembershipPlan, id=plan_id, is_active=True)

    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    order_amount = int(plan.price * (100*100))  # Convert to paisa
    order_currency = "INR"

    # Check if an active subscription exists
    active_subscription = Subscription.objects.filter(msme=msme, is_active=True).first()
    
    if active_subscription:
        # Update existing subscription details
        active_subscription.membership_plan = plan
        active_subscription.end_date = now() + timedelta(days=plan.duration_days)
        active_subscription.auto_renew = True
        active_subscription.save()
    else:
        # Create a new subscription
        active_subscription = Subscription.objects.create(
            msme=msme,
            membership_plan=plan,
            status="pending",
            start_date=now(),
            end_date=now() + timedelta(days=plan.duration_days),
            auto_renew=True,
        )
    
    # Create a new Razorpay order
    order_data = {
        "amount": order_amount,
        "currency": order_currency,
        "receipt": f"order_rcpt_{msme.id}",
        "payment_capture": 1,
    }
    order = client.order.create(data=order_data)
    
    # Store Razorpay order ID in subscription
    active_subscription.razorpay_order_id = order["id"]
    active_subscription.save()

    return Response({
        "status":True,
        "order_id": order["id"],
        "amount": order_amount,
        "currency": order_currency,
        "message": "Order created successfully. Active plan updated."
    })



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_payment(request):
    razorpay_payment_id = request.data.get("razorpay_payment_id")
    razorpay_order_id = request.data.get("razorpay_order_id")
    razorpay_signature = request.data.get("razorpay_signature")

    subscription = get_object_or_404(Subscription, razorpay_order_id=razorpay_order_id)
    user = subscription.msme.user
    new_plan = subscription.membership_plan  # The plan the user is trying to buy

    # 🚀 Check if payment already exists before verification
    existing_payment = PaymentHistory.objects.filter(razorpay_signature=razorpay_signature).first()
    print("sdfghjkl", existing_payment)
    if existing_payment:
        return Response({"status":True,"message": "Payment already processed"}, status=status.HTTP_400_BAD_REQUEST)

    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

    try:
        params_dict = {
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_signature": razorpay_signature,
        }
        client.utility.verify_payment_signature(params_dict)

        # ✅ Check if user already has an active plan
        active_subscription = Subscription.objects.filter(msme=subscription.msme, is_active=True).first()
        if active_subscription and active_subscription.membership_plan != new_plan:
            # 1️⃣ Cancel old subscription
            active_subscription.is_active = False
            active_subscription.status = "expired"
            active_subscription.save()

        # 2️⃣ Activate the new plan
        subscription.status = "active"
        subscription.is_active = True
        subscription.razorpay_payment_id = razorpay_payment_id
        subscription.razorpay_signature = razorpay_signature
        subscription.save()

        # 3️⃣ Save payment history **(With try-except block to prevent IntegrityError)**
        try:
            PaymentHistory.objects.create(
                msme=subscription.msme,
                subscription=subscription,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_order_id=razorpay_order_id,
                razorpay_signature=razorpay_signature,
                amount=subscription.membership_plan.price,
                status="success",
            )
        except IntegrityError:
            return Response({"status":False, "message": "Duplicate payment detected."}, status=status.HTTP_400_BAD_REQUEST)

        # 4️⃣ Send confirmation email
        send_mail(
            "Subscription Upgrade Successful",
            f"Dear {user.username}, your plan has been upgraded to {new_plan.name}.",
            "support@yourdomain.com",
            [user.email],
        )

        return Response({"status":True, "message": f"Payment successful, upgraded to {new_plan.name}."})

    except razorpay.errors.SignatureVerificationError:
        return Response({"status":False, "message": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)


# ***************************************************************************
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .razorpay_utils import *

from django.core.mail import send_mail

class CreateSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            msme = MSMEProfile.objects.get(user=request.user)
            plan_id = request.data.get("membership_plan_id")
            print(plan_id, "plan_id")
            plan = MembershipPlan.objects.get(id=plan_id)
            print("plan", plan)

            if Subscription.objects.filter(msme=msme, is_active=True).exists():
                return Response({
                    "status": False,
                    "message": "Active subscription already exists.",
                    "data": []
                }, status=400)

            existing = Subscription.objects.filter(msme=msme).last()
            customer_id = existing.razorpay_customer_id if existing and existing.razorpay_customer_id else create_customer(msme)["id"]

            razorpay_plan = create_plan(plan)
            razorpay_sub = create_subscription(customer_id, razorpay_plan["id"], plan.price)

            Subscription.objects.create(
                msme=msme,
                membership_plan=plan,
                razorpay_customer_id=customer_id,
                razorpay_subscription_id=razorpay_sub["id"],
                status="pending",
                is_active=False,
                auto_renew=True,
                end_date=timezone.now() + timedelta(days=plan.duration_days)
            )

            return Response({
                "status": True,
                "message": "Subscription initiated. Complete payment.",
                "data": {
                    "subscription_id": razorpay_sub["id"],
                    # "payment_link": razorpay_sub.get("short_url")
                }
            })

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e),
                "data": []
            }, status=500)


# class ConfirmPaymentView(APIView):
#     permission_classes = [IsAuthenticated]
#     def post(self, request):
#         try:
#             data = request.data
#             payment_id = data.get("razorpay_payment_id")
#             subscription_id = data.get("razorpay_subscription_id")
#             signature = data.get("razorpay_signature")

#             verify_signature(payment_id, subscription_id, signature)

#             subscription = Subscription.objects.get(razorpay_subscription_id=subscription_id)
#             subscription.razorpay_payment_id = payment_id
#             subscription.razorpay_signature = signature
#             subscription.status = "active"
#             subscription.is_active = True
#             subscription.start_date = timezone.now()

#             subscription_data = fetch_subscription(subscription.razorpay_subscription_id)
#             end_timestamp = subscription_data.get("current_end")
#             if end_timestamp:
#                 subscription.end_date = timezone.make_aware(datetime.fromtimestamp(end_timestamp))
#             else:
#                 subscription.end_date = timezone.now() + timedelta(days=subscription.membership_plan.duration_days)

#             subscription.save()

#             PaymentHistory.objects.create(
#                 msme=subscription.msme,
#                 subscription=subscription,
#                 razorpay_payment_id=payment_id,
#                 razorpay_signature=signature,
#                 amount=subscription.membership_plan.price,
#                 currency="INR",
#                 status="success"
#             )

#             send_mail(
#                 subject="Subscription Successful",
#                 message=f"Hi {subscription.msme.brand_name}, your payment was successful!",
#                 recipient_list=[subscription.msme.user.email],
#                 from_email=settings.DEFAULT_FROM_EMAIL
#             )

#             return Response({
#                 "status": True,
#                 "message": "Payment confirmed and subscription activated.",
#                 "data": {
#                     "subscription_id": subscription.razorpay_subscription_id,
#                     "payment_id": payment_id
#                 }
#             })

#         except razorpay.errors.SignatureVerificationError:
#             return Response({
#                 "status": False,
#                 "message": "Invalid signature",
#                 "data": []
#             }, status=400)
#         except Exception as e:
#             return Response({
#                 "status": False,
#                 "message": str(e),
#                 "data": []
#             }, status=500)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils import timezone
from django.conf import settings

from datetime import datetime, timedelta
from io import BytesIO
import razorpay
import logging

from weasyprint import HTML

logger = logging.getLogger(__name__)

class ConfirmPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            payment_id = data.get("razorpay_payment_id")
            subscription_id = data.get("razorpay_subscription_id")
            signature = data.get("razorpay_signature")

            if not all([payment_id, subscription_id, signature]):
                return Response({
                    "status": False,
                    "message": "Missing Razorpay payment data.",
                    "data": []
                }, status=400)

            # ✅ Verify the Razorpay signature
            verify_signature(payment_id, subscription_id, signature)

            # ✅ Fetch and update subscription object
            subscription = Subscription.objects.get(razorpay_subscription_id=subscription_id)
            subscription.razorpay_payment_id = payment_id
            subscription.razorpay_signature = signature
            subscription.status = "active"
            subscription.is_active = True
            subscription.start_date = timezone.now()

            subscription_data = fetch_subscription(subscription_id)
            end_timestamp = subscription_data.get("current_end")
            if end_timestamp:
                subscription.end_date = timezone.make_aware(datetime.fromtimestamp(end_timestamp))
            else:
                subscription.end_date = timezone.now() + timedelta(days=subscription.membership_plan.duration_days)

            subscription.save()

            # ✅ Save payment history
            payment = PaymentHistory.objects.create(
                msme=subscription.msme,
                subscription=subscription,
                razorpay_payment_id=payment_id,
                razorpay_signature=signature,
                amount=subscription.membership_plan.price,
                currency="INR",
                status="success"
            )

            # ✅ RENDER EMAIL TEMPLATE
            email_html = render_to_string("emails/subscription_confirmation.html", {
                "user": subscription.msme.user,
                "subscription": subscription,
                "payment": payment
            })

            # ✅ RENDER INVOICE TEMPLATE TO PDF
            invoice_html = render_to_string("invoices/subscription_invoice.html", {
                "subscription": subscription,
                "payment": payment
            })

            pdf_file = BytesIO()
            HTML(string=invoice_html).write_pdf(pdf_file)
            pdf_file.seek(0)

            # ✅ SEND EMAIL
            email = EmailMessage(
                subject="🎉 Your Subscription is Confirmed!",
                body=email_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[subscription.msme.user.email]
            )
            email.content_subtype = "html"
            email.attach("subscription_invoice.pdf", pdf_file.read(), "application/pdf")
            email.send()

            return Response({
                "status": True,
                "message": "Payment confirmed, subscription activated, and invoice emailed.",
                "data": {
                    "subscription_id": subscription.razorpay_subscription_id,
                    "payment_id": payment_id
                }
            })

        except razorpay.errors.SignatureVerificationError:
            logger.error("Invalid Razorpay signature", exc_info=True)
            return Response({
                "status": False,
                "message": "Invalid Razorpay signature.",
                "data": []
            }, status=400)

        except Subscription.DoesNotExist:
            logger.error("Subscription not found", exc_info=True)
            return Response({
                "status": False,
                "message": "Subscription not found.",
                "data": []
            }, status=404)

        except Exception as e:
            logger.error(f"Payment confirmation error: {str(e)}", exc_info=True)
            return Response({
                "status": False,
                "message": f"Error: {str(e)}",
                "data": []
            }, status=500)


class CancelAutoRenewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            msme = MSMEProfile.objects.get(user=request.user)
            sub = Subscription.objects.filter(msme=msme, is_active=True).last()

            if not sub:
                return Response({
                    "status": False,
                    "message": "No active subscription found.",
                    "data": []
                }, status=404)

            subscription_data = fetch_subscription(sub.razorpay_subscription_id)
            if subscription_data.get("status") != "active":
                return Response({
                    "status": False,
                    "message": "Subscription must be active before auto-renewal can be cancelled.",
                    "data": []
                }, status=400)

            cancel_auto_renew(sub.razorpay_subscription_id)
            sub.auto_renew = False
            sub.save()

            send_mail(
                subject="Auto-Renew Cancelled",
                message=f"Hi {sub.msme.brand_name}, auto-renewal has been disabled.",
                recipient_list=[sub.msme.user.email],
                from_email=settings.DEFAULT_FROM_EMAIL
            )

            return Response({
                "status": True,
                "message": "Auto-renewal cancelled successfully.",
                "data": {
                    "subscription_id": sub.razorpay_subscription_id
                }
            })

        except Exception as e:
            return Response({
                "status": False,
                "message": str(e),
                "data": []
            }, status=500)
        


from api.v1.accounts.razorpay_utils import razorpay_client


class MySubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            msme = MSMEProfile.objects.get(user=request.user)
            sub = Subscription.objects.filter(msme=msme, is_active=True).last()
            if not sub:
                return Response({"message": "No active subscription."})
            
            razorpay_sub = razorpay_client.subscription.fetch(sub.razorpay_subscription_id)
            status = ''
            if sub.status == razorpay_sub["status"]:
                status = razorpay_sub["status"]
            return Response({
                "status": True,
                "message": "Your Subcription Details fetched successfully.",
                "data": {
                    "membership_plan": sub.membership_plan.name,
                    "membership_plan": sub.membership_plan.name,
                    "membership_status":status,
                    # "local_status": sub.status,
                    "auto_renew": sub.auto_renew,
                    # "razorpay_status": razorpay_sub["status"],
                    "ends_on": sub.end_date
                }
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)




class PaymentHistoryViewSet(ModelViewSet):
    queryset = PaymentHistory.objects.all()
    serializer_class = PaymentHistorySerializer
    pagination_class = CustomPagination



# *************************** Webhook Implementation *******************************************
# *************************** Webhook Implementation *******************************************
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    def post(self, request):
        payload = request.body
        received_signature = request.headers.get('X-Razorpay-Signature')
        event = "unknown"
        log_entry = None

        try:
            data = json.loads(payload)
            event = data.get("event", "unknown")

            # Save the initial log
            log_entry = RazorpayWebhookLog.objects.create(
                event=event,
                payload=data,
                status="received"
            )

            # Signature verification
            secret = settings.RAZORPAY_WEBHOOK_SECRET
            expected_signature = hmac.new(
                key=bytes(secret, 'utf-8'),
                msg=payload,
                digestmod=hashlib.sha256
            ).hexdigest()

            if received_signature != expected_signature:
                if log_entry:
                    log_entry.status = "failed"
                    log_entry.notes = "Invalid signature"
                    log_entry.save()
                return Response({"status": False, "message": "Invalid signature"}, status=400)

            if event == "subscription.charged":
                payload_sub = data.get("payload", {}).get("subscription", {}).get("entity", {})
                payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})

                razorpay_subscription_id = payload_sub.get("id")
                payment_id = payment_entity.get("id")

                subscription = Subscription.objects.get(razorpay_subscription_id=razorpay_subscription_id)
                subscription.status = "active"
                subscription.is_active = True
                subscription.razorpay_payment_id = payment_id
                subscription.start_date = timezone.now()

                # Set end date
                end_timestamp = payload_sub.get("current_end")
                if end_timestamp:
                    subscription.end_date = timezone.make_aware(datetime.fromtimestamp(end_timestamp))
                else:
                    subscription.end_date = timezone.now() + timedelta(days=subscription.membership_plan.duration_days)

                subscription.save()

                # Save payment
                payment = PaymentHistory.objects.create(
                    msme=subscription.msme,
                    subscription=subscription,
                    razorpay_payment_id=payment_id,
                    razorpay_signature=received_signature,
                    amount=subscription.membership_plan.price,
                    currency="INR",
                    status="success"
                )

                # Send confirmation
                send_subscription_confirmation(subscription, payment)

                # Update log
                log_entry.status = "processed"
                log_entry.notes = f"Subscription {subscription.id} activated"
                log_entry.save()

                return Response({"status": True, "message": "Subscription activated via webhook"})

            # If not processed
            log_entry.status = "processed"
            log_entry.notes = f"Unhandled event type: {event}"
            log_entry.save()
            return Response({"status": True, "message": "Webhook received (event not handled)"})

        except Exception as e:
            logger.exception("Error processing Razorpay webhook")
            if log_entry:
                log_entry.status = "failed"
                log_entry.notes = str(e)
                log_entry.save()
            return Response({"status": False, "message": str(e)}, status=500)

