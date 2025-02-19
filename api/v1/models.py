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

    class Meta:
        db_table = "user_master"
        verbose_name = "User Master"
        verbose_name_plural = "User Masters"
    

class UserProfile(models.Model):
    """Profile model for storing additional user details"""

    user = models.OneToOneField(UserMaster, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(upload_to="profile_pics/", null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    
    # MSME-specific fields
    brand_name = models.CharField(max_length=255, null=True, blank=True)
    number_of_outlets = models.TextField(null=True, blank=True)  # Store names
    daily_approximate_footfalls = models.IntegerField(null=True, blank=True)
    brand_logo = models.ImageField(upload_to="brand_logos/", null=True, blank=True)
    area = models.CharField(max_length=100, null=True, blank=True)  # Main branch area
    city = models.CharField(max_length=100, null=True, blank=True)  # Main branch city
    zip_code = models.CharField(max_length=15, null=True, blank=True)  # Main branch zipcode
    state = models.CharField(max_length=100, null=True, blank=True)  # Main branch state
    gstin = models.CharField(max_length=15, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s MSME"
    class Meta:
        db_table = "user_profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def update_outlet_count(self):
        """Automatically update number_of_outlets with outlet names"""
        outlet_names = self.outlets.values_list("name", flat=True)  # Get list of names
        self.number_of_outlets = ", ".join(outlet_names) if outlet_names else None  # Store as a comma-separated string
        self.save()


class Outlet(models.Model):
    """Model for multiple outlets under a UserProfile"""

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="outlets")
    name = models.CharField(max_length=255)  # New field for outlet name
    area = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=15)
    state = models.CharField(max_length=100)
    daily_footfalls = models.IntegerField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True, blank=True,null=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} ({self.user_profile.user.username})"
    class Meta:
        db_table = "outlet"
        verbose_name = "Outlet"
        verbose_name_plural = "Outlets"

    def save(self, *args, **kwargs):
        """Override save method to update the number_of_outlets"""
        super().save(*args, **kwargs)
        self.user_profile.update_outlet_count()
        
class Customer(models.Model):
    """ Model for storing customer details """

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    whatsapp_number = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True) 
    dob = models.DateField(null=True, blank=True)
    anniversary_cate = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        db_table = "customer"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"


class CustomerFeedback(models.Model):
    """Model for storing customer feedback"""
    AGE_CHOICES = [
        ("10-15", "10-15"),
        ("16-30", "16-30"),
        ("31-45", "31-45"),
        (">45", "Above 45"),
    ]

    EXPERIENCE_CHOICES = [(i, str(i)) for i in range(1, 6)]
    EMOTION_CHOICES = [
        ("Happy", "Happy"),
        ("Excited", "Excited"),
        ("Neutral", "Neutral"),
        ("Disappointed", "Disappointed"),
        ("Frustrated", "Frustrated"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="feedbacks")
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, related_name="feedbacks")

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    whatsapp_number = models.CharField(max_length=15)

    birthday = models.DateField(null=True, blank=True)
    anniversary = models.DateField(null=True, blank=True)
    age_group = models.CharField(max_length=10, choices=AGE_CHOICES)
    city = models.CharField(max_length=100)

    visit_frequency = models.CharField(max_length=255)
    date_of_visit = models.DateField()

    favorite_services = models.TextField(blank=True, null=True)
    overall_experience = models.IntegerField(choices=EXPERIENCE_CHOICES)
    service_quality_rating = models.IntegerField(choices=EXPERIENCE_CHOICES)
    item_quality_rating = models.IntegerField(choices=EXPERIENCE_CHOICES)
    value_for_money = models.IntegerField(choices=EXPERIENCE_CHOICES)

    would_recommend = models.BooleanField(default=False)
    likelihood_to_return = models.IntegerField(choices=EXPERIENCE_CHOICES)
    emotions = models.CharField(max_length=20, choices=EMOTION_CHOICES)

    suggestions = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.first_name} {self.last_name} - {self.overall_experience}/5"

    class Meta:
        db_table = "customer_feedback"
        verbose_name = "Customer Feedback"
        verbose_name_plural = "Customer Feedbacks"




class Campaign(models.Model):
    """Model to store campaign details"""

    CHANNEL_CHOICES = [
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("sms", "SMS"),
        ("all", "All"),
    ]

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=255)
    message = models.TextField()
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expiry_date = models.DateField()
    image_url = models.URLField(null=True, blank=True)
    button_url = models.URLField(null=True, blank=True)
    channel_type = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="whatsapp")

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "campaign"
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        return f"{self.name} - {self.channel_type}"





class Profession(models.Model):
    """Model for storing profession details"""
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "profession"
        verbose_name = "Profession"
        verbose_name_plural = "Professions"

class RewardChoice(models.Model):
    """Model for storing reward choices"""
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "reward_choice"
        verbose_name = "Reward Choice"
        verbose_name_plural = "Reward Choices"


class CampaignType(models.Model):
    """Model for storing campaign types"""
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "campaign_type"
        verbose_name = "Campaign Type"
        verbose_name_plural = "Campaign Types"




# class Campaign(models.Model):
#     """Model to store campaign details"""

#     CHANNEL_CHOICES = [
#         ("whatsapp", "WhatsApp"),
#         ("email", "Email"),
#         ("sms", "SMS"),
#         ("all", "All"),
#     ]

#     user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="campaigns")
#     name = models.CharField(max_length=255)
#     message = models.TextField()
#     discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
#     expiry_date = models.DateField()
#     image_url = models.URLField(null=True, blank=True)
#     button_url = models.URLField(null=True, blank=True)
#     channel_type = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="whatsapp")

#     # New Fields for Storing Given Data
#     campaign_type = models.ForeignKey(CampaignType, on_delete=models.SET_NULL, null=True, related_name="campaigns")
#     reward_choice = models.ForeignKey(RewardChoice, on_delete=models.SET_NULL, null=True, related_name="campaigns")
#     profession = models.ForeignKey(Profession, on_delete=models.SET_NULL, null=True, related_name="campaigns")
#     outlets = models.ManyToManyField(Outlet, related_name="campaigns")
#     channel = models.ManyToManyField(CampaignType, related_name="campaign_channels")

#     logo = models.ImageField(upload_to="campaign_logos/", null=True, blank=True)
#     bg_image = models.ImageField(upload_to="campaign_bg_images/", null=True, blank=True)
#     button_url = models.URLField(null=True, blank=True)

#     created_on = models.DateTimeField(auto_now_add=True)
#     updated_on = models.DateTimeField(auto_now=True)
#     is_deleted = models.BooleanField(default=False)

#     class Meta:
#         db_table = "campaign"
#         verbose_name = "Campaign"
#         verbose_name_plural = "Campaigns"

#     def __str__(self):
#         return f"{self.name} - {self.channel_type}"
