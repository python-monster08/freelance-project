from django.urls import path
from api.v1.accounts.views import UserSignupView, UserLoginView, UserProfileUpdateView, SocialLoginView

urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('social-login/', SocialLoginView.as_view(), name='social-login'),
]
