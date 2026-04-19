import ssl
import smtplib
import logging
import traceback

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from django.conf import settings
from django.contrib.auth import get_user_model

from gym.models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


# 1) Helper functions for notifications and emails related to memberships, bookings, and account creation.
# a) HELPER: Create in-app notification
def create_notification(user, notification_type, title, message):
    """
    Creates an in-app notification record in the database.
    """
    try:
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
        )
    except Exception as e:
        logger.error(f"[Notification Error] Failed to create notification for {user.username}: {e}")


# b) HELPER: Send email using smtplib directly
def send_email(subject, message, recipient_email):
    """
    Sends plain text email using smtplib directly.
    SSL verification disabled for development due to corporate proxy/firewall
    intercepting SSL on this network (common in Nepal ISPs/institutions).
    NOTE: Re-enable SSL verification in production deployment.
    """
    if not recipient_email or '@' not in recipient_email:
        logger.warning(f"[Email Warning] Invalid or empty email: '{recipient_email}' — skipped.")
        return

    try:
        # Build email message
        msg = MIMEMultipart()
        msg['From'] = settings.DEFAULT_FROM_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        # Disable SSL verification — needed when behind corporate proxy/firewall
        # that inserts self-signed certificates
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Connect via smtplib directly
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(
                settings.EMAIL_HOST_USER,
                recipient_email,
                msg.as_string()
            )

        logger.info(f"[Email Sent] '{subject}' → {recipient_email}")

    except smtplib.SMTPAuthenticationError:
        logger.error(
            f"[Email Error] Gmail authentication failed for {settings.EMAIL_HOST_USER}. "
            f"Check your App Password in the .env file."
        )
    except smtplib.SMTPException as e:
        logger.error(f"[Email Error] SMTP error sending to {recipient_email}: {e}")
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"[Email Error] Unexpected error sending to {recipient_email}: {e}")
        logger.error(traceback.format_exc())


# c) HELPER: Get all admin emails
def get_admin_emails():
    """
    Returns list of email addresses of all active Admin users.
    """
    try:
        admins = User.objects.filter(
            role='Admin',
            is_active=True
        ).exclude(email='')
        emails = [admin.email for admin in admins if admin.email]
        logger.info(f"[Admin Emails] Found {len(emails)} admin(s): {emails}")
        return emails
    except Exception as e:
        logger.error(f"[Email Error] Failed to fetch admin emails: {e}")
        return []


# 2) MEMBERSHIP NOTIFICATIONS
# a) Membership Purchased, Hold, Unhold, Cancelled
def notify_membership_purchased(user, plan, payment_method):
    """
    Notifies client and admins when membership is purchased.
    """
    title = "Membership Purchased"
    client_message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your membership plan '{plan.plan_name}' has been successfully purchased.\n"
        f"Duration: {plan.duration} month(s)\n"
        f"Price: Rs. {plan.price}\n"
        f"Payment Method: {payment_method}\n\n"
        f"{'Please visit the front desk to complete your cash payment.' if payment_method == 'Cash' else 'Your online payment has been confirmed.'}\n\n"
        f"Thank you for joining Shadow Fit!\n"
        f"Shadow Fit Team"
    )

    # In-app notification for client
    create_notification(user, 'membership_purchased', title, client_message)

    # Email to client
    send_email(
        subject=f"Shadow Fit — {title}",
        message=client_message,
        recipient_email=user.email,
    )

    # Email to all admins
    admin_message = (
        f"New Membership Purchased\n\n"
        f"Client: {user.get_full_name()} (@{user.username})\n"
        f"Email: {user.email}\n"
        f"Plan: {plan.plan_name}\n"
        f"Price: Rs. {plan.price}\n"
        f"Payment Method: {payment_method}\n"
    )
    for admin_email in get_admin_emails():
        send_email(
            subject="Shadow Fit — New Membership Purchased",
            message=admin_message,
            recipient_email=admin_email,
        )

# b) Membership Hold, Unhold, Cancelled
def notify_membership_hold(user, subscription):
    """
    Notifies client when membership is put on hold.
    """
    title = "Membership On Hold"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your '{subscription.plan.plan_name}' membership has been put on hold.\n"
        f"Your remaining days will be preserved and counted from when you resume.\n\n"
        f"You can resume anytime from My Membership page.\n\n"
        f"Shadow Fit Team"
    )
    create_notification(user, 'membership_hold', title, message)
    send_email(
        subject=f"Shadow Fit — {title}",
        message=message,
        recipient_email=user.email,
    )

# c) Membership Unhold
def notify_membership_unhold(user, subscription, new_end_date):
    """
    Notifies client when membership is resumed with new expiry date.
    """
    title = "Membership Resumed"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your '{subscription.plan.plan_name}' membership has been resumed.\n"
        f"New Expiry Date: {new_end_date.strftime('%B %d, %Y')}\n\n"
        f"Welcome back to Shadow Fit!\n"
        f"Shadow Fit Team"
    )
    create_notification(user, 'membership_unhold', title, message)
    send_email(
        subject=f"Shadow Fit — {title}",
        message=message,
        recipient_email=user.email,
    )

# d) Membership Cancelled
def notify_membership_cancelled(user, subscription):
    """
    Notifies client and admins when membership is cancelled.
    """
    title = "Membership Cancelled"
    client_message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your '{subscription.plan.plan_name}' membership has been cancelled.\n"
        f"We hope to see you back soon!\n\n"
        f"Shadow Fit Team"
    )
    create_notification(user, 'membership_cancelled', title, client_message)
    send_email(
        subject=f"Shadow Fit — {title}",
        message=client_message,
        recipient_email=user.email,
    )

    admin_message = (
        f"Membership Cancelled\n\n"
        f"Client: {user.get_full_name()} (@{user.username})\n"
        f"Email: {user.email}\n"
        f"Plan: {subscription.plan.plan_name}\n"
    )
    for admin_email in get_admin_emails():
        send_email(
            subject="Shadow Fit — Membership Cancelled",
            message=admin_message,
            recipient_email=admin_email,
        )


# 3) BOOKING NOTIFICATIONS
# a) Booking Created (Pending Confirmation or Confirmed based on payment method)
def notify_booking_created(user, booking):
    """
    Notifies client and admins when a booking is created.
    """
    title = "Trainer Booked"
    trainer_name = booking.schedule.trainer.user.get_full_name()
    is_online = booking.booking_status == 'Confirmed'
    payment_method = 'Online (Khalti)' if is_online else 'Cash'

    client_message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your trainer booking has been "
        f"{'confirmed' if is_online else 'submitted and is pending confirmation'}.\n\n"
        f"Trainer: {trainer_name}\n"
        f"Shift: {booking.schedule.shift_name} "
        f"({booking.schedule.start_time.strftime('%I:%M %p')} — "
        f"{booking.schedule.end_time.strftime('%I:%M %p')})\n"
        f"Duration: {booking.duration}\n"
        f"Start Date: {booking.start_date.strftime('%B %d, %Y')}\n"
        f"End Date: {booking.end_date.strftime('%B %d, %Y')}\n"
        f"Payment Method: {payment_method}\n\n"
        f"{'Please visit the front desk to complete your cash payment.' if not is_online else ''}\n\n"
        f"Shadow Fit Team"
    )

    create_notification(user, 'booking_created', title, client_message)
    send_email(
        subject=f"Shadow Fit — {title}",
        message=client_message,
        recipient_email=user.email,
    )

    admin_message = (
        f"New Trainer Booking\n\n"
        f"Client: {user.get_full_name()} (@{user.username})\n"
        f"Email: {user.email}\n"
        f"Trainer: {trainer_name}\n"
        f"Shift: {booking.schedule.shift_name}\n"
        f"Duration: {booking.duration}\n"
        f"Start: {booking.start_date.strftime('%B %d, %Y')}\n"
        f"Status: {booking.booking_status}\n"
        f"Payment: {payment_method}\n"
    )
    for admin_email in get_admin_emails():
        send_email(
            subject="Shadow Fit — New Trainer Booking",
            message=admin_message,
            recipient_email=admin_email,
        )

# b) Booking Status Changed (Confirmed, Cancelled, Completed)
def notify_booking_status_changed(user, booking, new_status):
    """
    Notifies client when booking status changes.
    Called for Confirmed, Cancelled, Completed.
    """
    status_map = {
        'Confirmed': ('Booking Confirmed', 'booking_confirmed'),
        'Cancelled': ('Booking Cancelled', 'booking_cancelled'),
        'Completed': ('Booking Completed', 'booking_completed'),
    }
    title, notification_type = status_map.get(
        new_status,
        ('Booking Update', 'booking_created')
    )

    trainer_name = booking.schedule.trainer.user.get_full_name()
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your booking with {trainer_name} has been {new_status.lower()}.\n\n"
        f"Shift: {booking.schedule.shift_name}\n"
        f"Duration: {booking.duration}\n"
        f"Start Date: {booking.start_date.strftime('%B %d, %Y')}\n\n"
        f"Shadow Fit Team"
    )

    create_notification(user, notification_type, title, message)
    send_email(
        subject=f"Shadow Fit — {title}",
        message=message,
        recipient_email=user.email,
    )


# 4) ACCOUNT NOTIFICATIONS
# Account Created by Admin (with default password)
def notify_account_created(user, default_password):
    """
    Notifies client/trainer when admin creates their account.
    Sends login credentials to their email.
    """
    title = "Your Shadow Fit Account is Ready"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your Shadow Fit account has been created by the admin.\n\n"
        f"Username: {user.username}\n"
        f"Password: {default_password}\n\n"
        f"Please login and change your password immediately.\n"
        f"Login at: http://127.0.0.1:8000/login/\n\n"
        f"Shadow Fit Team"
    )
    create_notification(user, 'membership_purchased', title, message)
    send_email(
        subject=f"Shadow Fit — {title}",
        message=message,
        recipient_email=user.email,
    )