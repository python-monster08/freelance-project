from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager for UserMaster model"""

    def create_user(self, email, username, phone_number, password=None, **extra_fields):
        """Create a normal user"""
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        if not phone_number:
            raise ValueError("Phone number is required")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, phone_number, password=None, **extra_fields):
        """Create a superuser with admin privileges"""
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, username, phone_number, password, **extra_fields)


class UserMaster(AbstractUser):
    ROLE_CHOICES = [
        ("super_admin", "Super Admin"),
        ("admin", "Admin"),
        ("executive", "Executive"),
    ]

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="executive")
    social_account_id = models.CharField(max_length=255, blank=True, null=True)
    social_account_provider = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True, blank=True,null=True)
    updated_on = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        "auth.Group", related_name="user_master_groups", blank=True
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission", related_name="user_master_permissions", blank=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "phone_number"]

    objects = UserManager()  # Attach custom manager

    def __str__(self):
        return f"{self.username} - {self.role}"

class UserProfile(models.Model):
    """Profile model for storing additional user details"""

    user = models.OneToOneField(UserMaster, on_delete=models.CASCADE, related_name="profile")
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True, blank=True,null=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"