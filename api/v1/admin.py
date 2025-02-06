from django.contrib import admin
from .models import UserMaster, UserProfile
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _


class UserMasterAdmin(UserAdmin):
    model = UserMaster
    list_display = ("email", "username", "phone_number", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    fieldsets = (
        (None, {"fields": ("email", "username", "phone_number", "password")}),
        (_("Personal Info"), {"fields": ("first_name", "last_name")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
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
        if change:  # If updating an existing user
            original_password = obj.password
            if "password" in form.changed_data:
                obj.set_password(obj.password)  # Hash the new password
        obj.save()




class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "brand_name", "number_of_outlets", "daily_approximate_footfalls", "gstin", "website"]
    search_fields = ["user__username", "user__email"]

admin.site.register(UserMaster, UserMasterAdmin)
admin.site.register(UserProfile, UserProfileAdmin)