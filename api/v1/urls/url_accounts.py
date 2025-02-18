from django.urls import path
from api.v1.accounts.views import *



urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('profile_update/', UserProfileView.as_view(), name='profile_update'),
    path('social_login/', SocialLoginView.as_view(), name='social_login'),
    
    # Outlet URLs
    # path('outlets/', OutletListCreateView.as_view(), name='outlet_list_create'),  # List and create outlets
    # path('outlets/<int:pk>/', OutletDetailView.as_view(), name='outlet_detail'),  # Retrieve, update, delete a specific outlet
    path('add_customer/', CustomerCreateView.as_view(), name='add-customer'),  # API to add a single customer
    path('upload_customers/', CustomerUploadView.as_view(), name='upload-customers'),  # API to upload customers via Excel
    
]