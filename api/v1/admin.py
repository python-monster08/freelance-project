from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import *

class UserMasterAdmin(UserAdmin):
    model = UserMaster
    list_display = ("id","email", "username", "phone_number", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    ordering = ("id", "email", "role")
    
    fieldsets = (
        (None, {"fields": ("email", "username", "phone_number", "password")}),
        (_("Personal Info"), {"fields": ("first_name", "last_name")}),
        (_("Social Accounts"), {"fields": ("social_account_id", "social_account_provider")}),
        (_("Permissions"), {"fields": ("is_active", "is_deleted", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "phone_number", "password1", "password2"),
        }),
    )

    search_fields = ("email", "username", "phone_number")
    ordering = ("email",)

    def save_model(self, request, obj, form, change):
        """Ensure password is hashed when changed in admin"""
        if change and "password" in form.changed_data:
            obj.set_password(obj.password)
        obj.save()


class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "id","user", "brand_name", "area", "city", "zip_code", "state", "number_of_outlets", "daily_approximate_footfalls", "gstin", "website"
    ]
    search_fields = ["user__username", "user__email", "brand_name", "city", "state"]
    list_filter = ["city", "state"]


class OutletAdmin(admin.ModelAdmin):
    list_display = ["id","user_profile", "name", "area", "city", "zip_code", "state", "daily_footfalls"]
    search_fields = ["user_profile__user__username", "user_profile__brand_name", "name", "city", "state"]
    list_filter = ["city", "state"]


class CustomerFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "id","first_name", "last_name", "email", "whatsapp_number", "city", "date_of_visit",
        "overall_experience", "service_quality_rating", "item_quality_rating", "value_for_money",
        "would_recommend", "likelihood_to_return", "emotions", "created_at"
    ]
    search_fields = ["first_name", "last_name", "email", "city"]
    list_filter = ["city", "overall_experience", "service_quality_rating", "item_quality_rating", "value_for_money", "would_recommend", "emotions"]

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id",'first_name', 'last_name', 'email', 'whatsapp_number', 'gender', 'city')
    search_fields = ('first_name', 'last_name', 'email', 'whatsapp_number', 'city')
    list_filter = ('gender', 'city')
    ordering = ('first_name',)



@admin.register(Profession)
class ProfessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')  # Display ID and name in the admin panel
    search_fields = ('name',)  # Enable search by name
    ordering = ('id',)  # Order by ID

@admin.register(RewardChoice)
class RewardChoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('id',)

@admin.register(CampaignType)
class CampaignTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('id',)

@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("id", "name")  # Display ID and Name in the admin list
    search_fields = ("name",)  # Allow searching by channel name
    ordering = ("id",)  # Order by ID

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("id","name", "user_profile", "expiry_date", "is_deleted", "created_on")
    list_filter = ("expiry_date", "is_deleted", "channels", "campaign_type")
    search_fields = ("name", "message", "user_profile__user__username")
    ordering = ("-created_on",)
    filter_horizontal = ("channels", "outlets")
    readonly_fields = ("created_on", "updated_on", "image_url")

    fieldsets = (
        ("Basic Information", {
            "fields": ("user_profile", "name", "message", "expiry_date", "button_url")
        }),
        ("Campaign Details", {
            "fields": ("channels", "campaign_type", "reward_choice", "profession", "outlets", "reward_choice_text")
        }),
        ("Media", {
            "fields": ("logo", "bg_image", "image_url")
        }),
        ("System Information", {
            "fields": ("is_deleted", "created_on", "updated_on")
        }),
    )

admin.site.register(UserMaster, UserMasterAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Outlet, OutletAdmin)
admin.site.register(CustomerFeedback, CustomerFeedbackAdmin)
