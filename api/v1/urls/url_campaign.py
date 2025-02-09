from django.urls import path
from api.v1.campaign_management.views import *



urlpatterns = [ 
    path("campaigns/", CampaignListCreateView.as_view(), name="campaign-list-create"),
    path("campaigns/<int:pk>/", CampaignRetrieveUpdateDeleteView.as_view(), name="campaign-detail"),
]