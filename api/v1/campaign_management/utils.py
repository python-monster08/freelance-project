import requests
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client


TWILIO_ACCOUNT_SID = "AC46201cb5e437e25c9267d447cc724543"
TWILIO_AUTH_TOKEN = "7e1a911b5a672e46501f70a032f068ec"
TWILIO_PHONE_NUMBER = "+14155238886"  # Your Twilio phone number

# Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ImgBB API Key
IMGBB_API_KEY = settings.IMGBB_API_KEY


# def send_whatsapp_message(phone_number, message, image_url):
#     """Send WhatsApp message to a customer using Twilio."""
#     if not phone_number.startswith("+"):
#         phone_number = f"+91{phone_number}"  # Add country code if needed
#         print(phone_number, "88888888888888888")

#     try:
#         print(phone_number, "777777777777777")

#         response = twilio_client.messages.create(
#             body=message,
#             from_="whatsapp:+14155238886",
#             to=f"whatsapp:{phone_number}",
#             media_url=[image_url],
#         )
#         print(response)
#         print(f"WhatsApp sent to {phone_number}! SID: {response.sid}")
#     except Exception as e:
#         print(f"Error sending WhatsApp to {phone_number}: {e}")


def send_whatsapp_message(phone_number, message, image_url, button_url):
    """Send WhatsApp message to a customer using Twilio."""
    if not phone_number.startswith("+"):
        phone_number = f"+91{phone_number}"  # Add country code if needed
        print(phone_number, "88888888888888888")

    try:
        print(phone_number, "777777777777777")

        # Append button URL to message
        message = f"{message}\n\n🔗 Visit Now: {button_url}"

        response = twilio_client.messages.create(
            body=message,
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{phone_number}",
            media_url=[image_url],
        )
        print(response)
        print(f"WhatsApp sent to {phone_number}! SID: {response.sid}")
    except Exception as e:
        print(f"Error sending WhatsApp to {phone_number}: {e}")

# def send_email_message(email, message, image_url):
#     """Send email to a customer."""
#     if not email:
#         return

#     try:
#         send_mail(
#             subject="New Campaign Notification",
#             message=message,
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[email],
#             fail_silently=False,
#         )
#         print(f"Email sent to {email}!")
#     except Exception as e:
#         print(f"Error sending email to {email}: {e}")

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import format_html


def send_email_message(email, message, image_url, button_url):
    """Send a well-formatted email with an image and button."""
    if not email:
        print("No email provided!")
        return

    try:
        subject = "Exclusive Offer for You! 🎉"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]

        # Plain text fallback (for email clients that don't support HTML)
        text_content = f"{message}\n\nVisit Now: {button_url}"

        # HTML Email Content
        html_content = format_html(
            """
            <html>
                <body style="font-family: Arial, sans-serif; color: #333; text-align: center;">
                    <h2 style="color: #f33;">Exclusive Offer Just for You! 🎉</h2>
                    <p>{}</p>
                    <img src="{}" alt="Exclusive Offer" style="width: 100%; max-width: 500px; border-radius: 10px; margin-top: 10px;">
                    <br>
                    <a href="{}" style="display: inline-block; background-color: #007BFF; color: white; padding: 12px 24px; text-decoration: none; font-size: 16px; border-radius: 5px; margin-top: 20px;">
                        Visit Now 🚀
                    </a>
                </body>
            </html>
            """,
            message,
            image_url,
            button_url,
        )

        # Create the email
        email_message = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email_message.attach_alternative(html_content, "text/html")

        # Send the email
        email_message.send()
        print(f"Email sent successfully to {email}!")

    except Exception as e:
        print(f"Error sending email to {email}: {e}")


def send_sms_message(phone_number, message):
    """Send SMS message to a customer using Twilio."""
    if not phone_number.startswith("+"):
        phone_number = f"+91{phone_number}"

    try:
        response = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number,
        )
        print(f"SMS sent to {phone_number}! SID: {response.sid}")
    except Exception as e:
        print(f"Error sending SMS to {phone_number}: {e}")
