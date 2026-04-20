from django.conf import settings
from gym.models import Notification


def notification_count(request):
    """
    Injects unread notification count into every template context.
    This allows the navbar bell icon to show badge count globally.
    """
    unread_count = 0
    try:
        if request.user.is_authenticated and hasattr(request.user, 'role'):
            if request.user.role == 'Member':
                unread_count = Notification.objects.filter(
                    user=request.user,
                    is_read=False
                ).count()
    except Exception:
        pass  # Silently fail — don't break page if DB issue

    # Pass session age in milliseconds for JS countdown
    session_age_ms = getattr(settings, 'SESSION_COOKIE_AGE', 120) * 1000

    return {
        'unread_notification_count': unread_count,
        'session_age_ms': session_age_ms,
    }