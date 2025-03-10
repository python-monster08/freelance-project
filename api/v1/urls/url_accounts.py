from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.v1.accounts.views import *

# Create a router and register our viewset with it.
router = DefaultRouter()
router.register(r'customer_feedback', CustomerFeedbackViewSet, basename='customer_feedback')
# router.register(r'profile_update', UpdateProfileViewSet, basename='profile_update')


urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('profile_update/', UpdateProfileView.as_view(), name='profile_update'),
    path('social_login/', SocialLoginView.as_view(), name='social_login'),
    
    # Outlet URLs
    # path('outlets/', OutletListCreateView.as_view(), name='outlet_list_create'),  # List and create outlets
    # path('outlets/<int:pk>/', OutletDetailView.as_view(), name='outlet_detail'),  # Retrieve, update, delete a specific outlet
    path('add_customer/', CustomerCreateView.as_view(), name='add_customer'),  # API to add a single customer
    path('update_delete_customer/<int:pk>/', CustomerCreateView.as_view(), name='customer_update_delete'),
    path('upload_customers/', CustomerUploadView.as_view(), name='upload_customers'),  # API to upload customers via Excel
    path('customers/', CustomerListView.as_view(), name='customer_list'),
    path('customers/<int:pk>/', CustomerRetrieveView.as_view(), name='customer_detail'),
    path('', include(router.urls)),  # Includes all ViewSet routes
]