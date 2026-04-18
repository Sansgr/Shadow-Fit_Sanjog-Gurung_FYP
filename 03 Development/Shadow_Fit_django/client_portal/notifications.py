from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from gym.models import Notification

# Get CustomUser model
User = get_user_model()


# ─────────────────────────────────────────────────────
# HELPER: Create in-app notification for a user
# ─────────────────────────────────────────────────────
def create_notification(user, notification_type, title, message):
    """
    Creates an in-app notification record in the database.
    Called for every event — membership, booking, etc.
    """
    try:
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
        )
    except Exception as e:
        # Log error but don't crash the main flow
        print(f"[Notification Error] Failed to create notification: {e}")


# ─────────────────────────────────────────────────────
# HELPER: Send email to a single recipient
# ─────────────────────────────────────────────────────
def send_email(subject, message, recipient_email):
    """
    Sends a plain text email to the given recipient.
    Wrapped in try/except to prevent email errors from breaking the app.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception as e:
        # Log error but don't crash the main flow
        print(f"[Email Error] Failed to send email to {recipient_email}: {e}")


# ─────────────────────────────────────────────────────
# HELPER: Get all admin users to notify
# ─────────────────────────────────────────────────────
def get_admin_emails():
    """
    Returns list of email addresses of all Admin role users.
    """
    try:
        admins = User.objects.filter(role='Admin', is_active=True).exclude(email='')
        return [admin.email for admin in admins]
    except Exception as e:
        print(f"[Email Error] Failed to fetch admin emails: {e}")
        return []


# ═════════════════════════════════════════════════════
# 1) MEMBERSHIP NOTIFICATIONS
# ═════════════════════════════════════════════════════

# a) Membership Purchased
def notify_membership_purchased(user, plan, payment_method):
    """
    Notifies client and admin when a membership is purchased.
    """
    title = "Membership Purchased"
    client_message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your membership plan '{plan.plan_name}' has been successfully purchased.\n"
        f"Duration: {plan.duration} month(s)\n"
        f"Price: Rs. {plan.price}\n"
        f"Payment Method: {payment_method}\n\n"
        f"{'Please visit the front desk to complete your cash payment.' if payment_method == 'Cash' else 'Your online payment has been confirmed.'}\n\n"
        f"Thank you for joining Shadow Fit!"
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


# b) Membership Hold
def notify_membership_hold(user, subscription):
    """
    Notifies client when membership is put on hold.
    """
    title = "Membership On Hold"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your '{subscription.plan.plan_name}' membership has been put on hold.\n"
        f"Your remaining days will be preserved and counted from the date you resume.\n\n"
        f"You can resume your membership anytime from My Membership page.\n\n"
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
    Notifies client when membership is resumed.
    """
    title = "Membership Resumed"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your '{subscription.plan.plan_name}' membership has been resumed.\n"
        f"New Expiry Date: {new_end_date.strftime('%B %d, %Y')}\n\n"
        f"Welcome back to Shadow Fit!"
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
    Notifies client and admin when membership is cancelled.
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

    # Notify admins
    admin_message = (
        f"Membership Cancelled\n\n"
        f"Client: {user.get_full_name()} (@{user.username})\n"
        f"Plan: {subscription.plan.plan_name}\n"
    )
    for admin_email in get_admin_emails():
        send_email(
            subject="Shadow Fit — Membership Cancelled",
            message=admin_message,
            recipient_email=admin_email,
        )


# ═════════════════════════════════════════════════════
# 2) BOOKING NOTIFICATIONS
# ═════════════════════════════════════════════════════

# a) Booking Created
def notify_booking_created(user, booking):
    """
    Notifies client and admin when a booking is created.
    """
    title = "Trainer Booked"
    trainer_name = booking.schedule.trainer.user.get_full_name()
    payment_method = 'Online (Khalti)' if booking.booking_status == 'Confirmed' else 'Cash'

    client_message = (
        f"Hi {user.get_full_name()},\n\n"
        f"Your trainer booking has been {'confirmed' if booking.booking_status == 'Confirmed' else 'submitted'}.\n\n"
        f"Trainer: {trainer_name}\n"
        f"Shift: {booking.schedule.shift_name} "
        f"({booking.schedule.start_time.strftime('%I:%M %p')} — "
        f"{booking.schedule.end_time.strftime('%I:%M %p')})\n"
        f"Duration: {booking.duration}\n"
        f"Start Date: {booking.start_date.strftime('%B %d, %Y')}\n"
        f"End Date: {booking.end_date.strftime('%B %d, %Y')}\n"
        f"Payment Method: {payment_method}\n\n"
        f"{'Please visit the front desk to complete your cash payment.' if payment_method == 'Cash' else ''}\n\n"
        f"Shadow Fit Team"
    )

    create_notification(user, 'booking_created', title, client_message)
    send_email(
        subject=f"Shadow Fit — {title}",
        message=client_message,
        recipient_email=user.email,
    )

    # Notify admins
    admin_message = (
        f"New Trainer Booking\n\n"
        f"Client: {user.get_full_name()} (@{user.username})\n"
        f"Trainer: {trainer_name}\n"
        f"Shift: {booking.schedule.shift_name}\n"
        f"Duration: {booking.duration}\n"
        f"Start: {booking.start_date.strftime('%B %d, %Y')}\n"
        f"Status: {booking.booking_status}\n"
    )
    for admin_email in get_admin_emails():
        send_email(
            subject="Shadow Fit — New Trainer Booking",
            message=admin_message,
            recipient_email=admin_email,
        )


# b) Booking Status Changed
def notify_booking_status_changed(user, booking, new_status):
    """
    Notifies client when booking status changes
    (Confirmed, Cancelled, Completed).
    """
    status_titles = {
        'Confirmed': 'Booking Confirmed',
        'Cancelled': 'Booking Cancelled',
        'Completed': 'Booking Completed',
    }
    status_types = {
        'Confirmed': 'booking_confirmed',
        'Cancelled': 'booking_cancelled',
        'Completed': 'booking_completed',
    }

    title = status_titles.get(new_status, 'Booking Update')
    notification_type = status_types.get(new_status, 'booking_created')
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