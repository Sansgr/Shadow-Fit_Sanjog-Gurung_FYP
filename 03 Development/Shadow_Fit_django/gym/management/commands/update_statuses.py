from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from gym.models import Subscription, Booking


class Command(BaseCommand):
    """
    Management command to auto-update statuses:
    1. Subscriptions past end_date → Expired
    2. Bookings past end_date → Completed

    Run manually:
        python manage.py update_statuses

    Schedule with Windows Task Scheduler or cron:
        # Linux/Mac cron (every day at midnight):
        0 0 * * * cd /path/to/project && python manage.py update_statuses

        # Windows Task Scheduler:
        Program: python
        Arguments: manage.py update_statuses
        Start in: D:\path\to\Shadow_Fit_django
    """
    help = 'Auto-expires subscriptions and completes bookings past their end date'

    def handle(self, *args, **kwargs):
        today = date.today()
        self.stdout.write(f"[update_statuses] Running for date: {today}")

        # ─── 1. Expire Subscriptions ──────────────────
        try:
            # Only expire Active or On Hold subscriptions past end_date
            expired_subs = Subscription.objects.filter(
                end_date__lt=today,
                subs_status__in=['Active', 'On Hold']
            )
            expired_count = expired_subs.count()
            expired_subs.update(subs_status='Expired')
            self.stdout.write(
                self.style.SUCCESS(
                    f"[Subscriptions] {expired_count} subscription(s) marked as Expired."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[Subscriptions] Error: {e}")
            )

        # ─── 2. Complete Bookings ─────────────────────
        try:
            # Only complete Confirmed bookings past end_date
            completed_bookings = Booking.objects.filter(
                end_date__lt=today,
                booking_status='Confirmed'
            )
            completed_count = completed_bookings.count()
            completed_bookings.update(booking_status='Completed')
            self.stdout.write(
                self.style.SUCCESS(
                    f"[Bookings] {completed_count} booking(s) marked as Completed."
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[Bookings] Error: {e}")
            )

        self.stdout.write(
            self.style.SUCCESS("[update_statuses] Done.")
        )