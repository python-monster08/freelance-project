from django.urls import path, include
from api.v1.campaign_management.views import *

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'professions', ProfessionViewSet, basename='profession')
router.register(r'reward_choices', RewardChoiceViewSet, basename='reward-choice')
router.register(r'campaign_types', CampaignTypeViewSet, basename='campaign-type')
router.register(r'outlets', OutletViewSet, basename='outlets')

urlpatterns = [ 
    path("campaigns/", CampaignListCreateView.as_view(), name="campaign-list-create"),
    path("campaigns/<int:pk>/", CampaignRetrieveUpdateDeleteView.as_view(), name="campaign-detail"),
    path("", include(router.urls)),
]