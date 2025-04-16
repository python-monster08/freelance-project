import random
import string
import razorpay
import time
from django.conf import settings
import pandas as pd

from api.v1.models import Customer, UserMaster
from msme_marketing_analytics.settings import EMAIL_HOST_USER
from django.core.mail import EmailMultiAlternatives


razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# def create_customer(msme):
#     if msme.razorpay_customer_id:
#         return {"id": msme.razorpay_customer_id}
#     res = razorpay_client.customer.create({
#         "name": msme.brand_name,
#         "email": msme.user.email,
#         "contact": msme.user.phone_number
#     })
#     msme.razorpay_customer_id = res['id']
#     msme.save()
#     return res


def create_customer(msme):
    # Already exists locally
    if msme.razorpay_customer_id:
        return {"id": msme.razorpay_customer_id}
    
    # ✅ Try searching Razorpay customers by email
    existing_customers = razorpay_client.customer.all({'email': msme.user.email}).get('items', [])
    if existing_customers:
        customer_id = existing_customers[0]['id']
        msme.razorpay_customer_id = customer_id
        msme.save()
        return {"id": customer_id}

    # ❌ If not found, create a new one
    res = razorpay_client.customer.create({
        "name": msme.brand_name,
        "email": msme.user.email,
        "contact": msme.user.phone_number
    })
    msme.razorpay_customer_id = res['id']
    msme.save()
    return res


def create_plan(plan):
    res = razorpay_client.plan.create({
        "period": "monthly",
        "interval": 1,
        "item": {
            "name": plan.name,
            "amount": int(plan.price * 100),  # e.g., 999.99 becomes 99999 paisa
            "currency": "INR",
            "description": f"{plan.name} - Recurring"
        }
    })
    return res


def create_subscription(customer_id, plan_id, plan_price):
    # Removed the 'addons' section to prevent double-charging
    return razorpay_client.subscription.create({
        "plan_id": plan_id,
        "customer_notify": 1,
        "total_count": 12,
        "quantity": 1,
        "customer_id": customer_id
    })


def fetch_subscription(subscription_id):
    return razorpay_client.subscription.fetch(subscription_id)

def verify_signature(payment_id, subscription_id, signature):
    return razorpay_client.utility.verify_subscription_payment_signature({
        "razorpay_payment_id": payment_id,
        "razorpay_subscription_id": subscription_id,
        "razorpay_signature": signature
    })

def cancel_auto_renew(subscription_id):
    return razorpay_client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": True})

# ************************************ Generate Invoice PDF *********************************
from weasyprint import HTML
from django.template.loader import render_to_string

def generate_invoice_pdf(subscription, payment):
    html = render_to_string("subscription_invoice.html", {
        "subscription": subscription,
        "payment": payment,
    })
    return HTML(string=html).write_pdf()


# ************************************ core/emails.py ***********************
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_subscription_confirmation(subscription, payment):
    user = subscription.msme.user
    subject = f"🎉 Subscription Confirmed – {subscription.membership_plan.name}"
    
    html_content = render_to_string("subscription_confirmation.html", {
        "user": user,
        "subscription": subscription,
        "payment": payment,
    })
    
    try:
        email = EmailMessage(
            subject,
            html_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email.content_subtype = "html"

        # Attach invoice PDF
        pdf_file = generate_invoice_pdf(subscription, payment)
        email.attach(f"Invoice-{payment.razorpay_payment_id}.pdf", pdf_file, "application/pdf")

        email.send()
        logger.info(f"[EMAIL SENT] Subscription confirmation sent to {user.email}")
    
    except Exception as e:
        logger.error(f"[EMAIL FAILED] Subscription email to {user.email} failed: {str(e)}")


# # razorpay_utils.py

# import razorpay
# import time
# from django.conf import settings

# razorpay_client = razorpay.Client(
#     auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
# )

# def create_customer(msme):
#     if msme.razorpay_customer_id:
#         return {"id": msme.razorpay_customer_id}
#     res = razorpay_client.customer.create({
#         "name": msme.brand_name,
#         "email": msme.user.email,
#         "contact": msme.user.phone_number
#     })
#     msme.razorpay_customer_id = res['id']
#     msme.save()
#     return res

# def create_plan(plan):
#     res = razorpay_client.plan.create({
#         "period": "monthly",
#         "interval": 1,
#         "item": {
#             "name": plan.name,
#             "amount": int(plan.price * 100),
#             "currency": "INR",
#             "description": f"{plan.name} - Recurring"
#         }
#     })
#     return res

# def create_subscription(customer_id, plan_id):
#     return razorpay_client.subscription.create({
#         "plan_id": plan_id,
#         "customer_notify": 1,
#         "total_count": 12,  # optional, for 12 months
#         "quantity": 1,
#         "customer_id": customer_id,
#         "start_at": int(time.time()) + 60
#     })

# def fetch_subscription(subscription_id):
#     return razorpay_client.subscription.fetch(subscription_id)

# def verify_signature(payment_id, subscription_id, signature):
#     return razorpay_client.utility.verify_subscription_payment_signature({
#         "razorpay_payment_id": payment_id,
#         "razorpay_subscription_id": subscription_id,
#         "razorpay_signature": signature
#     })

# def cancel_auto_renew(subscription_id):
#     return razorpay_client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": True})




# import razorpay
# from django.conf import settings
# import time
# razorpay_client = razorpay.Client(
#     auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
# )


# def create_customer(msme):
#     if msme.razorpay_customer_id:
#         # Customer already created earlier
#         return {"id": msme.razorpay_customer_id}

#     response = razorpay_client.customer.create({
#         "name": msme.brand_name,
#         "email": msme.user.email,
#         "contact": msme.user.phone_number
#     })

#     # Save Razorpay customer ID
#     msme.razorpay_customer_id = response['id']
#     msme.save()

#     return response


# def create_plan(plan):
#     response = razorpay_client.plan.create({
#         "period": "monthly",
#         "interval": 1,
#         "item": {
#             "name": plan.name,
#             "amount": int(plan.price * 100),  # in paise
#             "currency": "INR",
#             "description": f"{plan.name} - Recurring"
#         }
#     })
#     return response



# def create_subscription(customer_id, plan_id):
#     return razorpay_client.subscription.create({
#         "plan_id": plan_id,
#         "customer_notify": 1,
#         "total_count": 12,
#         "quantity": 1,
#         "customer_id": customer_id,
#         "start_at": int(time.time()) + 60  # starts in 1 minute
#     })

# def fetch_subscription(subscription_id):
#     return razorpay_client.subscription.fetch(subscription_id)

# def cancel_auto_renew(subscription_id):
#     res = razorpay_client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": True})
#     print(res)
#     return res

# def verify_signature(payment_id, subscription_id, signature):
#     return razorpay_client.utility.verify_subscription_payment_signature({
#         'razorpay_payment_id': payment_id,
#         'razorpay_subscription_id': subscription_id,
#         'razorpay_signature': signature
#     })


def SearchUserRecord(dataframe, search):
    try:
        results = dataframe[
            dataframe['name'].str.contains(search, case=False)|
            dataframe['email'].str.contains(search, case=False) |
            dataframe['phone_number'].str.contains(search, case=False) |
            dataframe['role_name'].str.contains(search, case=False) |
            dataframe['created_by_name'].str.contains(search, case=False) |
            dataframe['assigned_by_name'].str.contains(search, case=False) |
            dataframe['assigned_by_email'].str.contains(search, case=False) |
            dataframe['employee_id'].str.contains(search, case=False)
            ]
        return results
    except:
        return pd.DataFrame()
    

def generate_emp_id(role_id):
    S = 10  # Number of characters in the numeric part
    role_prefix_map = {
        '1': 'CM',
        # '2': 'ME',
        # '3': 'EX',
       
    }

    prefix = role_prefix_map.get(str(1), "")  # Default to empty if role_id is invalid

    if not prefix:
        return None  # Return None for invalid roles

    while True:
        # Generate a 10-digit random number
        ran_data = ''.join(random.choices(string.digits, k=S))
        new_emp_id = f"{prefix}{ran_data}"

        # Check uniqueness in the database
        if not UserMaster.objects.filter(user_code=new_emp_id).exists():
            return new_emp_id
        

def generate_referral_code():
    code_length = 10  # You can adjust this length
    charset = string.ascii_uppercase + string.digits

    while True:
        referral_code = ''.join(random.choices(charset, k=code_length))
        if not Customer.objects.filter(referral_code=referral_code).exists():
            return referral_code
        

def send_credentials_email(user_obj):
    subject = "[ Cambridge ] Your Credentials"
    
    html_message = f"""
    <html>
    <body>
        <p>Hi {user_obj.first_name},</p>
        <p>Welcome to our platform! We're thrilled to have you on board.</p>

        <p><strong>Here are your login details:</strong></p>

        <p><strong>URL:</strong> <a href="http://127.0.0.1:8080/api/v1/account/login/</a></p>
        <p><strong>Email:</strong> {user_obj.email}</p>

        <p>Please log in and explore our services. If you have any questions, feel free to reach out.</p>
        <p>Best regards,<br>The Team</p>
    </body>
    </html>
    """

    from_email = EMAIL_HOST_USER  # Replace with your actual email address or settings.EMAIL_HOST_USER
    # MY_EMAIL = MY_EMAIL         # Replace with the admin email you want to receive a copy

    recipient_list = [user_obj.email,"ashishk140@triazinesoft.com"]

    email = EmailMultiAlternatives(subject, '', from_email, recipient_list)
    email.attach_alternative(html_message, "text/html")
    email.send()