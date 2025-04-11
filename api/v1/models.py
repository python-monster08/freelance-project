from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import os
from django.utils.timezone import now
from django.utils.text import slugify

# Create your models here.

class UserRole(models.Model):
    """Role model for defining user roles"""
    id = models.IntegerField(primary_key=True)
    role = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.role

    class Meta:
        db_table = "user_role"
        verbose_name = "User Role"
        verbose_name_plural = "User Roles"

# class UserManager(BaseUserManager):
#     """Custom manager for UserMaster model"""

#     def create_user(self, email, username, phone_number, password=None, **extra_fields):
#         """Create a normal user"""
#         if not email:
#             raise ValueError("Email is required")
#         if not username:
#             raise ValueError("Username is required")
#         if not phone_number:
#             raise ValueError("Phone number is required")

#         email = self.normalize_email(email)
#         user = self.model(email=email, username=username, phone_number=phone_number, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, email, username, phone_number, password=None, **extra_fields):
#         """Create a superuser with admin privileges"""
#         extra_fields.setdefault("is_active", True)
#         extra_fields.setdefault("is_staff", True)
#         extra_fields.setdefault("is_superuser", True)

#         return self.create_user(email, username, phone_number, password, **extra_fields)

class UserManager(BaseUserManager):
    """Custom manager for UserMaster model"""

    def create_user(self, email, username, phone_number, password=None, role_id=None, **extra_fields):
        """Create a normal user"""
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        if not phone_number:
            raise ValueError("Phone number is required")

        email = self.normalize_email(email)

        # Fetch or set role
        role = UserRole.objects.filter(id=role_id).first() if role_id else None

        user = self.model(email=email, username=username, phone_number=phone_number, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, phone_number, password=None, **extra_fields):
        """Create a superuser with role_id=1"""
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        # Ensure role_id=1 exists or create it
        super_admin_role, _ = UserRole.objects.get_or_create(id=1, defaults={"role": "Super Admin"})

        return self.create_user(email, username, phone_number, password, role_id=super_admin_role.id, **extra_fields)


class UserMaster(AbstractUser):
    ROLE_CHOICES = [
        (1, "Super Admin"),
        (2, "Admin"),
        (3, "Executive"),
    ]

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    # role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="executive")
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True, blank=True)  # Updated field
    social_account_id = models.CharField(max_length=255, blank=True, null=True)
    social_account_provider = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_profile_update = models.BooleanField(default=False)
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
    
class MSMEProfile(models.Model):
    """Profile model for storing additional user details"""

    user = models.OneToOneField(UserMaster, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(upload_to="profile_pics/", null=True, blank=True)
    website = models.URLField(null=True, blank=True)

    # Razorpay fields
    razorpay_customer_id = models.CharField(max_length=100, null=True, blank=True)

    # MSME-specific fields
    brand_name = models.CharField(max_length=255, null=True, blank=True)
    daily_approximate_footfalls = models.IntegerField(null=True, blank=True)
    brand_logo = models.ImageField(upload_to="brand_logos/", null=True, blank=True)
    area = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=15, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    gstin = models.CharField(max_length=15, null=True, blank=True)
    pan_number = models.CharField(max_length=15, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s MSME"

    class Meta:
        db_table = "user_profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

class Outlet(models.Model):
    """Model for multiple outlets under a MSMEProfile"""

    user_profile = models.ForeignKey(MSMEProfile, on_delete=models.CASCADE, related_name="outlets")
    name = models.CharField(max_length=255)
    area = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=15)
    state = models.CharField(max_length=100)
    daily_footfalls = models.IntegerField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} ({self.user_profile.user.username})"

    class Meta:
        db_table = "outlet"
        verbose_name = "Outlet"
        verbose_name_plural = "Outlets"

    def delete(self, *args, **kwargs):
        """Override delete to handle soft deletion"""
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])

        
class Customer(models.Model):
    """ Model for storing customer details """

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    msme = models.ForeignKey(MSMEProfile, on_delete=models.CASCADE, related_name="customers", null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    whatsapp_number = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True) 
    dob = models.DateField(null=True, blank=True)
    anniversary_date = models.DateField(null=True, blank=True)
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


class Channel(models.Model):
    """Model to store communication channels"""
    id = models.IntegerField(primary_key=True)  # Storing integer values (1=WhatsApp, 2=Email, etc.)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "channel"
        verbose_name = "Channel"
        verbose_name_plural = "Channels"

class Campaign(models.Model):
    """Model to store campaign details"""
    
    user_profile = models.ForeignKey(MSMEProfile, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=255)
    message = models.TextField()
    expiry_date = models.DateField()
    button_url = models.URLField(null=True, blank=True)

    channels = models.ManyToManyField(Channel, related_name="campaign_channels")
    campaign_type = models.ForeignKey(CampaignType, on_delete=models.SET_NULL, null=True, related_name="campaigns")
    reward_choice = models.ForeignKey(RewardChoice, on_delete=models.SET_NULL, null=True, related_name="campaigns")
    profession = models.ForeignKey(Profession, on_delete=models.SET_NULL, null=True, related_name="campaigns")
    outlets = models.ManyToManyField(Outlet, related_name="campaigns", blank=True)

    reward_choice_text = models.CharField(max_length=50, null=True, blank=True)

    logo = models.ImageField(upload_to="campaign_logos/", null=True, blank=True)
    bg_image = models.ImageField(upload_to="campaign_bg_images/", null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "campaign"
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"

    def __str__(self):
        """Return campaign name with channel names"""
        return f"{self.name} - {', '.join([channel.name for channel in self.channels.all()])}"

    def save(self, *args, **kwargs):
        """Rename uploaded images before saving"""
        current_date = now().strftime("%Y%m%d")
        slugified_name = slugify(self.name)

        # Rename logo image
        if self.logo and hasattr(self.logo, "name"):
            ext = os.path.splitext(self.logo.name)[1]
            self.logo.name = f"campaign_logos/{slugified_name}_{current_date}{ext}"

        # Rename background image
        if self.bg_image and hasattr(self.bg_image, "name"):
            ext = os.path.splitext(self.bg_image.name)[1]
            self.bg_image.name = f"campaign_bg_images/{slugified_name}_{current_date}{ext}"

        super().save(*args, **kwargs)

class MembershipPlan(models.Model):
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration_days = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Razorpay mapped Plan ID
    razorpay_plan_id = models.CharField(max_length=255, null=True, blank=True)  
    # Features stored as JSON
    campaign = models.JSONField(default=list)  
    referral_system = models.BooleanField(default=False)
    loyalty_points = models.BooleanField(default=False)
    feedback_analysis = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(UserMaster, on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        """Save MembershipPlan and manage SupportSystem status"""
        is_new = self._state.adding  # Check if it's a new object
        super().save(*args, **kwargs)  # Save MembershipPlan first

        # Get or create SupportSystem
        support_system, created = SupportSystem.objects.get_or_create(
            plan=self,
            defaults={
                "support": False,
                "training": False,
                "staff_re_training": False,
                "dedicated_poc": False,
                "is_deleted": not self.is_active or self.is_deleted,  # Better clarity
            }
        )

        # Update existing SupportSystem's is_deleted status
        if not created:
            support_system.is_deleted = not self.is_active or self.is_deleted
            support_system.save()

class SupportSystem(models.Model):
    """Model to store support system details"""
    plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE, related_name="support_systems")
    support = models.BooleanField(default=False)
    training = models.BooleanField(default=False)
    staff_re_training = models.BooleanField(default=False)
    dedicated_poc = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.plan.name

    class Meta:
        db_table = "support_system"
        verbose_name = "Support System"
        verbose_name_plural = "Support Systems"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("canceled", "Canceled"),
        ("pending", "Pending"),
    ]

    msme = models.ForeignKey(MSMEProfile, on_delete=models.CASCADE)
    membership_plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE)
    
    # Razorpay Payment & Subscription Tracking
    razorpay_payment_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    razorpay_customer_id = models.CharField(max_length=255, unique=True, null=True, blank=True)  # ✅ Store Razorpay Customer ID
    razorpay_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)  # ✅ Store Razorpay Recurring Subscription ID

    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")  # ✅ Track subscription status
    auto_renew = models.BooleanField(default=True)  # ✅ Enable Auto-Renewal
    is_active = models.BooleanField(default=False)

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.msme.brand_name} - {self.membership_plan.name} ({self.status})"



# class PaymentHistory(models.Model):
#     msme = models.ForeignKey(MSMEProfile, on_delete=models.CASCADE)
#     subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    
#     razorpay_payment_id = models.CharField(max_length=255, unique=True)
#     razorpay_order_id = models.CharField(max_length=255, unique=True)
#     razorpay_signature = models.CharField(max_length=255, unique=True)
    
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     currency = models.CharField(max_length=10, default="INR")
#     status = models.CharField(max_length=50, default="pending")  # ✅ pending, success, failed

#     created_on = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.msme.brand_name} - {self.razorpay_payment_id} ({self.status})"

class PaymentHistory(models.Model):
    msme = models.ForeignKey(MSMEProfile, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")

    razorpay_payment_id = models.CharField(max_length=255)
    razorpay_order_id = models.CharField(max_length=255)
    razorpay_signature = models.CharField(max_length=255)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=50, default="pending")

    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.msme.brand_name} - {self.razorpay_payment_id} ({self.status})"



# {
# "campaign_channel":[1,2],   
# "campaign_outlets": ["main-1", "sub-1"],
# "reward_choice":1,  
# "profession":1,
# "campaign_type":1,
# "name":'Spring Sale Campaign 2025', 
# "campaign_message":'Get 20% off on all items!',
# "campaign_reward_choice_text":'20%',
# "campaign_expiry_date":'2025-03-01',
# "button_url":'https://yourwebsite.com/offer',
# "campaign_bg_image":'cat.png',    
# "campaign_logo":'rat.png'      
# }



# name:"Spring Sale Campaign"
# campaign_message:"Big Spring Sale! Get 20% OFF on all products. Hurry, limited time only!"
# campaign_expiry_date:"2025-03-01" 
# button_url: "https://yourwebsite.com/offer"
# reward_choice:1
# profession:1
# campaign_type:1
# campaign_reward_choice_text: "Flat 20% Discount on All Orders!"
# campaign_channel: [1,2,3]
# campaign_outlets: ["main-1", "sub-1"]
# campaign_logo: <Upload logo file>
# campaign_bg_image: <Upload background image file>


