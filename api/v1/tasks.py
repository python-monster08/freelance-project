# api/v1/tasks.py

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
from api.v1.models import Subscription, PaymentHistory
from api.v1.accounts.razorpay_utils import fetch_subscription
from django.utils import timezone
from django.utils.timezone import localtime
from api.v1.accounts.razorpay_utils import razorpay_client

@shared_task
def send_expiry_alerts():
    upcoming_expiry = timezone.now() + timedelta(days=0)
    print("🔍 Checking for subscriptions expiring on:", upcoming_expiry.date())

    subs = Subscription.objects.filter(
        end_date__date=upcoming_expiry.date(),
        is_active=True,
        auto_renew=True
    )
    print(f"📦 Subscriptions found: {subs.count()}")

    for sub in subs:
        try:
            email = sub.msme.user.email
            brand = sub.msme.brand_name
            print(f"📧 Sending to: {email}")
            
            send_mail(
                subject="Your MSME Subscription is Expiring Soon",
                message=f"Dear {brand},\n\nYour subscription will expire on {sub.end_date.date()}. Please make sure auto-renewal is funded.",
                recipient_list=[email],
                from_email="kamleshlovewanshi2025@gmail.com"
            )
            print(f"✅ Sent to: {email}")
        except Exception as e:
            print(f"❌ Failed for {sub.msme.user.email}: {str(e)}")



import logging

logger = logging.getLogger(__name__)

@shared_task
def check_and_auto_renew_subscriptions():
    now = timezone.now()
    expiring_subs = Subscription.objects.filter(end_date__lte=now, is_active=True, auto_renew=True)

    for sub in expiring_subs:
        try:
            # Fetch current subscription status from Razorpay
            razorpay_sub = fetch_subscription(sub.razorpay_subscription_id)
            logger.info(f"[🔄 Fetched] {sub.msme.brand_name} | Status: {razorpay_sub['status']}")

            # Razorpay should trigger webhook. If not, this fallback checks status
            if razorpay_sub['status'] == 'active':
                current_end = razorpay_sub.get('current_end')
                if current_end:
                    new_end_date = timezone.make_aware(datetime.fromtimestamp(current_end))
                    if new_end_date > sub.end_date:
                        sub.end_date = new_end_date
                        sub.start_date = now
                        sub.save()
                        logger.info(f"[✅ Auto-renewed] {sub.msme.brand_name} | New End: {sub.end_date}")
                else:
                    logger.warning(f"[⚠️ No End Date] {sub.msme.brand_name}")
            else:
                logger.warning(f"[❌ Not Active] {sub.msme.brand_name} | Razorpay Status: {razorpay_sub['status']}")

        except Exception as e:
            logger.exception(f"[🛑 Error] {sub.msme.brand_name} | {str(e)}")

# working code
# @shared_task
# def check_and_auto_renew_subscriptions():
#     now = timezone.now()
#     expiring = Subscription.objects.filter(end_date__lte=now, is_active=True, auto_renew=True)

#     for sub in expiring:
#         try:
#             razorpay_sub = fetch_subscription(sub.razorpay_subscription_id)
#             print("Subscription Fetched:", razorpay_sub)

#             if razorpay_sub['status'] == 'active' and razorpay_sub.get("current_end"):
#                 sub.start_date = now
#                 sub.end_date = now + timedelta(days=sub.membership_plan.duration_days)
#                 sub.save()

#                 invoice_id = razorpay_sub.get("latest_invoice_id", "")
#                 payment_id = ""
#                 signature = ""

#                 if invoice_id:
#                     invoice = razorpay_client.invoice.fetch(invoice_id)
#                     payment_id = invoice.get("payment_id") or ""
#                     # Optional: If you have webhook signature validation, include it here
#                     print("Invoice fetched:", invoice)

#                 PaymentHistory.objects.create(
#                     msme=sub.msme,
#                     subscription=sub,
#                     razorpay_payment_id=payment_id,
#                     razorpay_order_id='',
#                     razorpay_signature=signature,
#                     amount=sub.membership_plan.price,
#                     currency="INR",
#                     status="success" if payment_id else "pending"
#                 )

#         except Exception as e:
#             print(f"[Renew Error] {sub.msme.brand_name}: {str(e)}")

# @shared_task
# def check_and_auto_renew_subscriptions():
#     now = timezone.now()
#     expiring = Subscription.objects.filter(end_date__lte=now, is_active=True, auto_renew=True)

#     for sub in expiring:
#         try:
#             razorpay_sub = fetch_subscription(sub.razorpay_subscription_id)
#             print(razorpay_sub, "resdfghjkl,;")
#             if razorpay_sub['status'] == 'active' and razorpay_sub.get("current_end"):
#                 sub.start_date = now
#                 sub.end_date = now + timedelta(days=sub.membership_plan.duration_days)
#                 sub.save()

#                 PaymentHistory.objects.create(
#                     msme=sub.msme,
#                     subscription=sub,
#                     razorpay_payment_id=razorpay_sub.get("latest_invoice_id", ""),
#                     razorpay_order_id='',
#                     razorpay_signature='',
#                     amount=sub.membership_plan.price,
#                     currency="INR",
#                     status="success"
#                 )
#         except Exception as e:
#             print(f"[Renew Error] {sub.msme.brand_name}: {str(e)}")


{'id': 'sub_QHH36ALWMxpqpU', 'entity': 'subscription', 'plan_id': 'plan_QHH352EYQ4DLll',
  'customer_id': 'cust_QHEldpwEbsbHnF', 'status': 'active', 'current_start': 1744270484, 
  'current_end': 1746815400, 'ended_at': None, 'quantity': 1, 'notes': [], 'charge_at': 1746815400, 
  'start_at': 1744270484, 'end_at': 1773081000, 'auth_attempts': 0, 'total_count': 12, 'paid_count': 1,
    'customer_notify': True, 'created_at': 1744270475, 'expire_by': None, 'short_url': 'https://rzp.io/rzp/elJWNTq', 
    'has_scheduled_changes': False, 'change_scheduled_at': None, 'source': 'api', 'payment_method': 'upi', 
    'offer_id': None, 'remaining_count': 11}
