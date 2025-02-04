from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserMaster, UserProfile

@receiver(post_save, sender=UserMaster)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a profile for new users"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=UserMaster)
def save_user_profile(sender, instance, **kwargs):
    """Save the user profile when the user is saved"""
    instance.profile.save()
