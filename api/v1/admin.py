from django.contrib import admin
from .models import UserMaster, UserProfile

class UserMasterAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "phone_number", "role", "is_staff", "is_superuser"]
    search_fields = ["username", "email", "phone_number"]
    list_filter = ["role", "is_staff", "is_superuser"]

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "address", "date_of_birth", "website"]
    search_fields = ["user__username", "user__email"]

admin.site.register(UserMaster, UserMasterAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
