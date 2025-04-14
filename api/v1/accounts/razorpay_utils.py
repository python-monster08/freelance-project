import razorpay
import time
from django.conf import settings

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
