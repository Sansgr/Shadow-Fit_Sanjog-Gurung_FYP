from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from trainer_portal.decorators import trainer_required
from gym.models import Booking, Schedule, Feedback, Trainer
from client_portal.notifications import notify_booking_status_changed


# HELPER: Paginate queryset
def paginate(queryset, request, per_page=10):
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page', 1)
    try:
        return paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        return paginator.page(1)


# 1) TRAINER DASHBOARD
# Shows summary stats and recent bookings
@trainer_required
def trainer_dashboard(request):
    """
    Trainer's home — shows their booking stats and recent activity.
    """
    try:
        # Get the Trainer profile linked to this user
        trainer = get_object_or_404(Trainer, user=request.user)

        # Count bookings by status
        pending_count = Booking.objects.filter(
            schedule__trainer=trainer,
            booking_status='Pending'
        ).count()
        confirmed_count = Booking.objects.filter(
            schedule__trainer=trainer,
            booking_status='Confirmed'
        ).count()
        completed_count = Booking.objects.filter(
            schedule__trainer=trainer,
            booking_status='Completed'
        ).count()
        cancelled_count = Booking.objects.filter(
            schedule__trainer=trainer,
            booking_status='Cancelled'
        ).count()

        # Recent 5 pending bookings for quick action
        recent_pending = Booking.objects.select_related(
            'user', 'schedule'
        ).filter(
            schedule__trainer=trainer,
            booking_status='Pending'
        ).order_by('-booking_date')[:5]

    except Exception as e:
        import traceback
        print(f"[Trainer Dashboard Error] {e}")
        print(traceback.format_exc())
        trainer = None
        pending_count = confirmed_count = completed_count = cancelled_count = 0
        recent_pending = []
        messages.error(request, "Failed to load dashboard data.")

    return render(request, 'trainer_portal/dashboard.html', {
        'trainer': trainer,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'recent_pending': recent_pending,
    })


# 2) TRAINER PROFILE MANAGEMENT
@trainer_required
def trainer_profile(request):
    """
    Trainer views and updates their own profile.
    Also shows their trainer-specific info.
    """
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
    except Exception:
        trainer = None

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            try:
                user = request.user
                user.first_name = request.POST.get('first_name', '').strip()
                user.last_name = request.POST.get('last_name', '').strip()
                user.email = request.POST.get('email', '').strip()
                user.phone = request.POST.get('phone', '').strip()

                if request.FILES.get('photo'):
                    user.photo = request.FILES['photo']

                user.save()
                messages.success(request, "Profile updated successfully!")
            except Exception:
                messages.error(request, "Failed to update profile.")

        elif form_type == 'password':
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if not request.user.check_password(old_password):
                messages.error(request, "Current password is incorrect.")
            elif new_password1 != new_password2:
                messages.error(request, "New passwords do not match.")
            elif len(new_password1) < 8:
                messages.error(request, "Password must be at least 8 characters.")
            else:
                try:
                    request.user.set_password(new_password1)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Password updated successfully!")
                except Exception:
                    messages.error(request, "Failed to update password.")

        return redirect('trainer_profile')

    return render(request, 'trainer_portal/profile.html', {
        'trainer': trainer,
    })


# 3) BOOKINGS MANAGEMENT
# Trainer can view, accept and reject bookings
@trainer_required
def trainer_bookings(request):
    """
    Shows all bookings for this trainer with filter by status.
    """
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        status_filter = request.GET.get('status', '')

        bookings = Booking.objects.select_related(
            'user', 'schedule'
        ).filter(
            schedule__trainer=trainer
        ).order_by('-booking_date')

        # Filter by status if provided
        if status_filter:
            bookings = bookings.filter(booking_status=status_filter)

    except Exception:
        bookings = []
        trainer = None
        status_filter = ''
        messages.error(request, "Failed to load bookings.")

    bookings_page = paginate(bookings, request, 10)

    return render(request, 'trainer_portal/bookings.html', {
        'bookings': bookings_page,
        'status_filter': status_filter,
        'status_choices': ['Pending', 'Confirmed', 'Cancelled', 'Completed'],
    })


# 4) ACCEPT BOOKING
# Changes booking status from Pending to Confirmed
@trainer_required
def accept_booking(request, pk):
    """
    Trainer accepts a pending booking — sets status to Confirmed.
    Notifies the client.
    """
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        # Ensure this booking belongs to this trainer
        booking = get_object_or_404(
            Booking,
            pk=pk,
            schedule__trainer=trainer,
            booking_status='Pending'
        )
    except Exception:
        messages.error(request, "Booking not found.")
        return redirect('trainer_bookings')

    if request.method == 'POST':
        try:
            booking.booking_status = 'Confirmed'
            booking.save()
            # Notify client that booking is confirmed
            notify_booking_status_changed(booking.user, booking, 'Confirmed')
            messages.success(
                request,
                f"Booking for {booking.user.get_full_name()} has been confirmed!"
            )
        except Exception:
            messages.error(request, "Failed to accept booking. Please try again.")
        return redirect('trainer_bookings')

    return render(request, 'trainer_portal/confirm_action.html', {
        'booking': booking,
        'action': 'Accept',
        'action_class': 'trainer-btn-success',
    })



# 5) REJECT BOOKING
# Changes booking status from Pending to Cancelled
@trainer_required
def reject_booking(request, pk):
    """
    Trainer rejects a pending booking — sets status to Cancelled.
    Notifies the client.
    """
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        booking = get_object_or_404(
            Booking,
            pk=pk,
            schedule__trainer=trainer,
            booking_status='Pending'
        )
    except Exception:
        messages.error(request, "Booking not found.")
        return redirect('trainer_bookings')

    if request.method == 'POST':
        try:
            booking.booking_status = 'Cancelled'
            booking.save()
            # Notify client that booking is cancelled
            notify_booking_status_changed(booking.user, booking, 'Cancelled')
            messages.success(
                request,
                f"Booking for {booking.user.get_full_name()} has been rejected."
            )
        except Exception:
            messages.error(request, "Failed to reject booking. Please try again.")
        return redirect('trainer_bookings')

    return render(request, 'trainer_portal/confirm_action.html', {
        'booking': booking,
        'action': 'Reject',
        'action_class': 'trainer-btn-danger',
    })



# 6) TRAINER REVIEWS
# View all reviews/feedback received
@trainer_required
def trainer_reviews(request):
    """
    Shows all feedback/reviews received by this trainer.
    """
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        feedbacks = Feedback.objects.select_related('user').filter(
            trainer=trainer
        ).order_by('-date_given')

        # Calculate average rating
        from django.db.models import Avg
        avg_rating = feedbacks.aggregate(avg=Avg('rating'))['avg'] or 0
        avg_rating = round(avg_rating, 1)

    except Exception:
        feedbacks = []
        avg_rating = 0
        trainer = None
        messages.error(request, "Failed to load reviews.")

    feedbacks_page = paginate(feedbacks, request, 10)

    return render(request, 'trainer_portal/reviews.html', {
        'feedbacks': feedbacks_page,
        'avg_rating': avg_rating,
        'total_reviews': feedbacks.count() if hasattr(feedbacks, 'count') else 0,
    })



# 7) TRAINER SCHEDULE
# View own schedules/shifts
@trainer_required
def trainer_schedule(request):
    """
    Shows this trainer's own schedule/shifts.
    Available Sunday to Friday.
    """
    try:
        trainer = get_object_or_404(Trainer, user=request.user)
        schedules = Schedule.objects.filter(
            trainer=trainer
        ).order_by('shift_name')

    except Exception:
        schedules = []
        trainer = None
        messages.error(request, "Failed to load schedule.")

    return render(request, 'trainer_portal/schedule.html', {
        'trainer': trainer,
        'schedules': schedules,
    })