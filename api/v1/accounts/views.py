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
from rest_framework.parsers import MultiPartParser, FormParser
import pandas as pd
from django.core.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


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
            user.is_profile_update = True  # Mark profile as complete

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

# class CustomerCreateView(APIView):
#     """ API to add a single customer via form submission """

#     def post(self, request):
#         serializer = CustomerSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "Customer created successfully!", "data": serializer.data}, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class CustomerCreateView(APIView):
#     """API to add a single customer via form submission"""

#     def post(self, request):
#         serializer = AddSingleCustomerSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"status": True, "message": "Customer created successfully!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        
#         return Response({"status": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# class CustomerUploadView(APIView):
#     """API to upload customer data via an Excel or CSV file"""
    
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request):
#         file = request.FILES.get('file')
#         if not file:
#             return Response({"status":False, "error": "No file uploaded!"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Determine the file type based on the extension
#             file_extension = file.name.split('.')[-1].lower()
#             if file_extension == 'xlsx' or file_extension == 'xls':
#                 df = pd.read_excel(file)
#             elif file_extension == 'csv':
#                 df = pd.read_csv(file)
#             else:
#                 return Response({"status":False, "error": "Unsupported file format. Please upload an Excel or CSV file."}, status=status.HTTP_400_BAD_REQUEST)

#             # Ensure required columns exist in the DataFrame
#             required_columns = {"first_name", "last_name", "email", "whatsapp_number", "gender", "dob", "anniversary_date", "city"}
#             if not required_columns.issubset(set(df.columns)):
#                 return Response({"status":False, "error": f"Missing required columns. Required: {required_columns}"}, status=status.HTTP_400_BAD_REQUEST)

#             customers = []
#             for _, row in df.iterrows():
#                 try:
#                     customer = Customer(
#                         first_name=row["first_name"],
#                         last_name=row["last_name"],
#                         email=row["email"],
#                         whatsapp_number=row["whatsapp_number"],
#                         gender=row["gender"],
#                         dob=row["dob"] if pd.notna(row["dob"]) else None,
#                         anniversary_date=row["anniversary_date"] if pd.notna(row["anniversary_date"]) else None,
#                         city=row["city"]
#                     )
#                     customer.full_clean()  # Validate fields
#                     customers.append(customer)
#                 except ValidationError as e:
#                     return Response({"status":False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#             Customer.objects.bulk_create(customers)
#             return Response({"status":True, "message": "Customers uploaded successfully!"}, status=status.HTTP_201_CREATED)
 
#         except Exception as e:
#             return Response({"status":False, "error": f"Invalid file format or data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        

# class CustomerCreateView(APIView):
#     """API to add a single customer via form submission"""
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         request_data = request.data.copy()
#         request_data["msme"] = request.user.id  # Assign logged-in MSME

#         serializer = AddSingleCustomerSerializer(data=request_data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(
#                 {"status": True, "message": "Customer created successfully!", "data": serializer.data},
#                 status=status.HTTP_201_CREATED,
#             )

#         return Response({"status": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# class CustomerCreateView(APIView):
#     """API to add a single customer via form submission"""

#     def post(self, request):
#         user_profile = None  # Default to None if unauthenticated

#         if request.user and request.user.is_authenticated:
#             try:
#                 user_profile = UserProfile.objects.get(user=request.user.id)  # Get the authenticated user's profile
#             except UserProfile.DoesNotExist:
#                 return Response({"status": False, "error": "User profile not found!"}, status=status.HTTP_400_BAD_REQUEST)
#         serializer = AddSingleCustomerSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save(msme=user_profile)  # Assign msme only if authenticated user exists
#             return Response({"status": True, "message": "Customer created successfully!", "data": serializer.data}, status=status.HTTP_201_CREATED)

#         return Response({"status": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class CustomerCreateView(APIView):
    """API to add, update, and delete customers."""

    def post(self, request):
        """Add single or multiple customers."""
        user_profile = None

        if request.user and request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user.id)
            except UserProfile.DoesNotExist:
                return Response({"status": False, "error": "User profile not found!"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        
        if isinstance(data, list):
            serializer = AddSingleCustomerSerializer(data=data, many=True)
        else:
            serializer = AddSingleCustomerSerializer(data=data)

        if serializer.is_valid():
            customers = serializer.save(msme=user_profile)
            return Response({
                "status": True,
                "message": "Customers created successfully!" if isinstance(customers, list) else "Customer created successfully!",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({"status": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk=None):
        """Update an existing customer by ID."""
        try:
            customer = Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response({"status": False, "error": "Customer not found!"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AddSingleCustomerSerializer(customer, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"status": True, "message": "Customer updated successfully!", "data": serializer.data}, status=status.HTTP_200_OK)
        
        return Response({"status": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk=None):
        """Delete a customer by ID."""
        try:
            customer = Customer.objects.get(pk=pk)
            customer.delete()
            return Response({"status": True, "message": "Customer deleted successfully!"}, status=status.HTTP_200_OK)
        except Customer.DoesNotExist:
            return Response({"status": False, "error": "Customer not found!"}, status=status.HTTP_404_NOT_FOUND)


class CustomerUploadView(APIView):
    """API to upload customer data via an Excel or CSV file"""
    
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"status": False, "error": "No file uploaded!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            file_extension = file.name.split(".")[-1].lower()
            if file_extension in ["xlsx", "xls"]:
                df = pd.read_excel(file)
            elif file_extension == "csv":
                df = pd.read_csv(file)
            else:
                return Response(
                    {"status": False, "error": "Unsupported file format. Please upload an Excel or CSV file."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            required_columns = {"first_name", "last_name", "email", "whatsapp_number", "gender", "dob", "anniversary_date", "city"}
            if not required_columns.issubset(set(df.columns)):
                return Response(
                    {"status": False, "error": f"Missing required columns. Required: {required_columns}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            customers = []
            for _, row in df.iterrows():
                try:
                    customer = Customer(
                        msme=UserProfile.objects.get(user=request.user.id),  # Assign logged-in MSME
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
                    return Response({"status": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            Customer.objects.bulk_create(customers)
            return Response({"status": True, "message": "Customers uploaded successfully!"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"status": False, "error": f"Invalid file format or data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)




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
# API to list customers with pagination
class CustomerListView(generics.ListAPIView):
    queryset = Customer.objects.all().order_by('-id')
    serializer_class = CustomerSerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)

        return Response({
            "status": True,
            "message": "User profiles with outlets retrieved successfully",
            "data": self.get_serializer(queryset, many=True).data
        }, status=status.HTTP_200_OK)

# API to retrieve a specific customer
class CustomerRetrieveView(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            "status": True,
            "message": "User profile retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)



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

    def create(self, request, *args, **kwargs):
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

    def update(self, request, *args, **kwargs):
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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"status": True, "message": "Feedback deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
