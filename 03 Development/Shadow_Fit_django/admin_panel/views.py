import json
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from accounts import models
from admin_panel.decorators import admin_required
from accounts.models import CustomUser
from gym.models import Booking, Feedback, Feedback, MembershipPlan, Payment, Schedule, Subscription, Trainer
from admin_panel.forms import ClientForm, MembershipPlanForm, ScheduleForm, TrainerUserForm, TrainerProfileForm, BookingForm, AdminSubscriptionForm
from client_portal.notifications import (
    notify_membership_purchased,
    notify_membership_hold,
    notify_membership_unhold,
    notify_membership_cancelled,
    notify_booking_status_changed,
    notify_account_created,
) 

# Helper: Pagination function to reuse in list views
def paginate(queryset, request, per_page=10):
    """
    Helper to paginate any queryset.
    Reads 'page' from GET params.
    """
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page', 1)
    try:
        return paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        return paginator.page(1)


# 1) ADMIN DASHBOARD 
@admin_required
def admin_dashboard(request):
    """
    Admin dashboard with real-time stats and charts.
    """
    try:
        # ─── Summary Stats ────────────────────────────
        total_clients = CustomUser.objects.filter(role='Member').count()
        total_trainers = Trainer.objects.count()
        total_bookings = Booking.objects.count()
        active_subscriptions = Subscription.objects.filter(
            subs_status='Active'
        ).count()
        pending_payments = Payment.objects.filter(
            payment_status='Pending'
        ).count()
        total_revenue = Payment.objects.filter(
            payment_status='Completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        recent_bookings = Booking.objects.select_related(
            'user', 'schedule__trainer__user'
        ).order_by('-booking_date')[:5]

        recent_payments = Payment.objects.select_related(
            'user'
        ).order_by('-payment_date')[:5]

        # ─── Monthly Revenue ──────────────────────
        monthly_revenue = list(
            Payment.objects.filter(
                payment_status='Completed'
            ).annotate(
                month=TruncMonth('payment_date')
            ).values('month').annotate(
                total=Sum('amount')
            ).order_by('month')[:6]
        )

        revenue_labels = [item['month'].strftime('%b %Y') for item in monthly_revenue]
        revenue_data = [float(item['total']) for item in monthly_revenue]

        # ─── Booking Status ───────────────────────
        booking_status_qs = list(
            Booking.objects.values('booking_status').annotate(count=Count('id'))
        )
        booking_labels = [item['booking_status'] for item in booking_status_qs]
        booking_counts = [item['count'] for item in booking_status_qs]

        # ─── Subscription Status ──────────────────
        sub_status_qs = list(
            Subscription.objects.values('subs_status').annotate(count=Count('id'))
        )
        sub_labels = [item['subs_status'] for item in sub_status_qs]
        sub_counts = [item['count'] for item in sub_status_qs]

    except Exception as e:
        import traceback
        print(f"[Dashboard Error] {e}")
        print(traceback.format_exc())
        total_clients = total_trainers = total_bookings = 0
        active_subscriptions = pending_payments = total_revenue = 0
        recent_bookings = recent_payments = []
        revenue_labels = revenue_data = []
        booking_labels = booking_counts = []
        sub_labels = sub_counts = []
        messages.error(request, "Failed to load dashboard data.")

    return render(request, 'admin_panel/dashboard.html', {
        'total_clients': total_clients,
        'total_trainers': total_trainers,
        'total_bookings': total_bookings,
        'active_subscriptions': active_subscriptions,
        'pending_payments': pending_payments,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'recent_payments': recent_payments,
        'revenue_labels': revenue_labels,
        'revenue_data': revenue_data,
        'booking_labels': booking_labels,
        'booking_counts': booking_counts,
        'sub_labels': sub_labels,
        'sub_counts': sub_counts,
    })

# b) Admin Profile
@admin_required
def admin_profile(request):
    """
    Admin views and updates their own profile.
    """
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            # Update personal info
            try:
                user = request.user
                user.first_name = request.POST.get('first_name', '').strip()
                user.last_name = request.POST.get('last_name', '').strip()
                user.email = request.POST.get('email', '').strip()
                user.phone = request.POST.get('phone', '').strip()

                # Handle photo upload
                if request.FILES.get('photo'):
                    user.photo = request.FILES['photo']

                user.save()
                messages.success(request, "Profile updated successfully!")
            except Exception:
                messages.error(request, "Failed to update profile. Please try again.")

        elif form_type == 'password':
            # Change password
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

        return redirect('admin_profile')

    return render(request, 'admin_panel/profile.html')

# c) ADD NEW ADMIN
@admin_required
def admin_add(request):
    """
    Admin can create new admin accounts.
    """
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        # Validate
        if not all([first_name, username, email, password]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'admin_panel/admin_add.html')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return render(request, 'admin_panel/admin_add.html')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'admin_panel/admin_add.html')

        try:
            new_admin = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
            )
            new_admin.role = 'Admin'
            new_admin.is_staff = True    # Admin has staff access
            new_admin.save()

            # Notify new admin via email
            from client_portal.notifications import notify_account_created
            notify_account_created(new_admin, password)

            messages.success(
                request,
                f"Admin account for {new_admin.get_full_name()} created successfully!"
            )
            return redirect('admin_dashboard')
        except Exception as e:
            messages.error(request, "Failed to create admin. Please try again.")

    return render(request, 'admin_panel/admin_add.html')


# 2) CLIENT MANAGEMENT VIEWS
# a) CLIENT LIST
@admin_required
def client_list(request):
    clients = CustomUser.objects.filter(role='Member').order_by('-date_joined')
    clients_page = paginate(clients, request, 10)
    return render(request, 'admin_panel/clients/client_list.html', {
        'clients': clients_page,
    })


# b) CLIENT ADD
@admin_required
def client_add(request):
    if request.method == 'POST':
        form = ClientForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save(commit=False)
            client.role = 'Member'
            client.set_password(f"{form.cleaned_data.get('username')}@123")  # default password
            client.save()
            default_password = f"{form.cleaned_data.get('username')}@123"
            notify_account_created(client, default_password)  # sends credentials to client email
            messages.success(request, "Client added successfully!")
            return redirect('client_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ClientForm()
    return render(request, 'admin_panel/clients/client_add.html', {'form': form})


# c) CLIENT UPDATE 
@admin_required
def client_update(request, pk):
    client = get_object_or_404(CustomUser, pk=pk, role='Member')
    if request.method == 'POST':
        form = ClientForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client updated successfully!")
            return redirect('client_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ClientForm(instance=client)
    return render(request, 'admin_panel/clients/client_update.html', {'form': form, 'client': client})


# d) CLIENT DELETE 
@admin_required
def client_delete(request, pk):
    client = get_object_or_404(CustomUser, pk=pk, role='Member')
    if request.method == 'POST':
        client.delete()
        messages.success(request, "Client deleted successfully!")
        return redirect('client_list')
    return render(request, 'admin_panel/clients/client_delete.html', {'client': client})


# 3) MEMBERSHIP PLAN MANAGEMENT VIEWS
# a) PLAN LIST 
@admin_required
def plan_list(request):
    plans = MembershipPlan.objects.all().order_by('price')
    plans_page = paginate(plans, request, 10)
    return render(request, 'admin_panel/plans/plan_list.html', {
        'plans': plans_page,
    })


# b) PLAN ADD 
@admin_required
def plan_add(request):
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Membership plan added successfully!")
            return redirect('plan_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = MembershipPlanForm()
    return render(request, 'admin_panel/plans/plan_add.html', {'form': form})


# c) PLAN UPDATE 
@admin_required
def plan_update(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, "Membership plan updated successfully!")
            return redirect('plan_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = MembershipPlanForm(instance=plan)
    return render(request, 'admin_panel/plans/plan_update.html', {'form': form, 'plan': plan})


# d) PLAN DELETE 
@admin_required
def plan_delete(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, "Membership plan deleted successfully!")
        return redirect('plan_list')
    return render(request, 'admin_panel/plans/plan_delete.html', {'plan': plan})


# 4) TRAINER MANAGEMENT VIEWS
# a) TRAINER LIST 
@admin_required
def trainer_list(request):
    trainers = Trainer.objects.select_related('user').all().order_by('user__first_name')
    trainers_page = paginate(trainers, request, 10)
    return render(request, 'admin_panel/trainers/trainer_list.html', {
        'trainers': trainers_page,
    })


# b) TRAINER ADD 
@admin_required
def trainer_add(request):
    if request.method == 'POST':
        user_form = TrainerUserForm(request.POST, request.FILES)
        profile_form = TrainerProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            # Save user first
            user = user_form.save(commit=False)
            user.role = 'Trainer'
            user.is_staff = True
            user.set_password(f"{user_form.cleaned_data.get('username')}@123")
            user.save()
            # Save trainer profile
            trainer = profile_form.save(commit=False)
            trainer.user = user
            trainer.save()
            # Send account creation notification with credentials
            default_password = f"{user_form.cleaned_data.get('username')}@123"
            notify_account_created(user, default_password)  # sends credentials to trainer email
            messages.success(request, "Trainer added successfully!")
            return redirect('admin_trainer_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        user_form = TrainerUserForm()
        profile_form = TrainerProfileForm()
    return render(request, 'admin_panel/trainers/trainer_add.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


# c) TRAINER UPDATE 
@admin_required
def trainer_update(request, pk):
    trainer = get_object_or_404(Trainer, pk=pk)
    if request.method == 'POST':
        user_form = TrainerUserForm(request.POST, request.FILES, instance=trainer.user)
        profile_form = TrainerProfileForm(request.POST, instance=trainer)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Trainer updated successfully!")
            return redirect('admin_trainer_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        user_form = TrainerUserForm(instance=trainer.user)
        profile_form = TrainerProfileForm(instance=trainer)
    return render(request, 'admin_panel/trainers/trainer_update.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'trainer': trainer
    })


# d) TRAINER DELETE 
@admin_required
def trainer_delete(request, pk):
    trainer = get_object_or_404(Trainer, pk=pk)
    if request.method == 'POST':
        trainer.user.delete()   # deletes CustomUser which cascades to Trainer
        messages.success(request, "Trainer deleted successfully!")
        return redirect('admin_trainer_list')
    return render(request, 'admin_panel/trainers/trainer_delete.html', {'trainer': trainer})


# 5) SCHEDULE MANAGEMENT VIEWS
# a) SCHEDULE LIST
@admin_required
def schedule_list(request):
    schedules = Schedule.objects.select_related('trainer__user').all().order_by('trainer__user__first_name', 'shift_name')
    schedules_page = paginate(schedules, request, 10)
    return render(request, 'admin_panel/schedules/schedule_list.html', {
        'schedules': schedules_page,
    })


# b) SCHEDULE ADD
@admin_required
def schedule_add(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Schedule added successfully!")
            return redirect('schedule_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ScheduleForm()
    return render(request, 'admin_panel/schedules/schedule_add.html', {'form': form})


# c) SCHEDULE UPDATE
@admin_required
def schedule_update(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "Schedule updated successfully!")
            return redirect('schedule_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ScheduleForm(instance=schedule)
    return render(request, 'admin_panel/schedules/schedule_update.html', {'form': form, 'schedule': schedule})


# d) SCHEDULE DELETE
@admin_required
def schedule_delete(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, "Schedule deleted successfully!")
        return redirect('schedule_list')
    return render(request, 'admin_panel/schedules/schedule_delete.html', {'schedule': schedule})


# 6) BOOKING MANAGEMENT VIEWS
# a) BOOKING LIST
@admin_required
def booking_list(request):
    bookings = Booking.objects.select_related('user', 'schedule__trainer__user').all().order_by('-booking_date')
    bookings_page = paginate(bookings, request, 10)
    return render(request, 'admin_panel/bookings/booking_list.html', {
        'bookings': bookings_page,
    })


# b) BOOKING ADD
@admin_required
def booking_add(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Booking added successfully!")
            return redirect('booking_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BookingForm()
    return render(request, 'admin_panel/bookings/booking_add.html', {
        'form': form,
        'today': date.today().isoformat()   # for min date in template
    })


# c) BOOKING UPDATE
@admin_required
def booking_update(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            # After form.save() in booking_update:
            new_status = form.cleaned_data.get('booking_status')
            if new_status in ['Confirmed', 'Cancelled', 'Completed']:
                notify_booking_status_changed(booking.user, booking, new_status) 
            messages.success(request, "Booking updated successfully!")
            return redirect('booking_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = BookingForm(instance=booking)
    return render(request, 'admin_panel/bookings/booking_update.html', {
        'form': form,
        'booking': booking,
        'today': date.today().isoformat()   # for min date in template
    })


# d) BOOKING DELETE 
@admin_required
def booking_delete(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        booking.delete()
        messages.success(request, "Booking deleted successfully!")
        return redirect('booking_list')
    return render(request, 'admin_panel/bookings/booking_delete.html', {'booking': booking})


# 7) SUBSCRIPTIONS (Admin CRUD)
# a) SUBSCRIPTION LIST 
@admin_required
def subscription_list(request):
    """
    Shows all client subscriptions with their status.
    """
    try:
        subscriptions = Subscription.objects.select_related(
            'user', 'plan'
        ).all().order_by('-start_date')
    except Exception:
        subscriptions = []
        messages.error(request, "Failed to load subscriptions.")

    subscriptions_page = paginate(subscriptions, request, 10)
    return render(request, 'admin_panel/subscriptions/subscription_list.html', {
        'subscriptions': subscriptions_page,
    })


# b) SUBSCRIPTION ADD 
@admin_required
def subscription_add(request):
    """
    Admin manually creates a subscription for a client.
    Useful for walk-in clients paying at the front desk.
    """
    if request.method == 'POST':
        form = AdminSubscriptionForm(request.POST)
        if form.is_valid():
            try:
                subscription = form.save(commit=False)

                # Auto-calculate end_date from start_date + plan duration
                subscription.end_date = (
                    subscription.start_date +
                    relativedelta(months=subscription.plan.duration)
                )
                subscription.save()

                # Notify client about new subscription
                notify_membership_purchased(
                    subscription.user,
                    subscription.plan,
                    'Cash'
                )
                messages.success(request, "Subscription created successfully!")
                return redirect('subscription_list')
            except Exception as e:
                messages.error(request, "Failed to create subscription. Please try again.")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = AdminSubscriptionForm()

    return render(request, 'admin_panel/subscriptions/subscription_add.html', {
        'form': form,
    })


# c) SUBSCRIPTION UPDATE 
@admin_required
def subscription_update(request, pk):
    """
    Admin updates subscription details.
    Status changes trigger notifications to the client.
    """
    try:
        subscription = get_object_or_404(Subscription, pk=pk)
        old_status = subscription.subs_status
    except Exception:
        messages.error(request, "Subscription not found.")
        return redirect('subscription_list')

    if request.method == 'POST':
        form = AdminSubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            try:
                updated = form.save(commit=False)
                new_status = updated.subs_status

                # Recalculate end_date if plan or start_date changed
                updated.end_date = (
                    updated.start_date +
                    relativedelta(months=updated.plan.duration)
                )

                # Handle hold logic — save hold_date when putting on hold
                if new_status == 'On Hold' and old_status != 'On Hold':
                    updated.hold_date = date.today()
                    notify_membership_hold(subscription.user, subscription)

                # Handle unhold — recalculate end_date from remaining days
                elif new_status == 'Active' and old_status == 'On Hold':
                    if subscription.hold_date:
                        remaining = (subscription.end_date - subscription.hold_date).days
                        remaining = max(0, remaining)
                    else:
                        remaining = (subscription.end_date - date.today()).days
                        remaining = max(0, remaining)
                    new_end = date.today() + timedelta(days=remaining)
                    updated.end_date = new_end
                    updated.hold_date = None
                    notify_membership_unhold(subscription.user, subscription, new_end)

                # Handle cancellation
                elif new_status == 'Cancelled' and old_status != 'Cancelled':
                    updated.hold_date = None
                    notify_membership_cancelled(subscription.user, subscription)

                updated.save()
                messages.success(request, "Subscription updated successfully!")
                return redirect('subscription_list')
            except Exception:
                messages.error(request, "Failed to update subscription. Please try again.")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = AdminSubscriptionForm(instance=subscription)

    return render(request, 'admin_panel/subscriptions/subscription_update.html', {
        'form': form,
        'subscription': subscription,
    })


# d) SUBSCRIPTION DELETE
@admin_required
def subscription_delete(request, pk):
    """
    Admin permanently deletes a subscription record.
    """
    try:
        subscription = get_object_or_404(Subscription, pk=pk)
    except Exception:
        messages.error(request, "Subscription not found.")
        return redirect('subscription_list')

    if request.method == 'POST':
        try:
            subscription.delete()
            messages.success(request, "Subscription deleted successfully!")
            return redirect('subscription_list')
        except Exception:
            messages.error(request, "Failed to delete subscription. Please try again.")

    return render(request, 'admin_panel/subscriptions/subscription_delete.html', {
        'subscription': subscription,
    })


# 8) PAYMENTS
# a) PAYMENT LIST 
@admin_required
def payment_list(request):
    """
    Shows all payments with filter options.
    """
    try:
        payments = Payment.objects.select_related('user').all().order_by('-payment_date')
    except Exception:
        payments = []
        messages.error(request, "Failed to load payments.")

    payments_page = paginate(payments, request, 10)
    return render(request, 'admin_panel/payments/payment_list.html', {
        'payments': payments_page,
    })


# b) PAYMENT VERIFY
@admin_required
def payment_verify(request, pk):
    """
    Admin verifies or rejects a pending payment.
    On verify → marks payment Completed + updates related subscription/booking to Active/Confirmed.
    On reject → marks payment Failed + updates related subscription/booking to Cancelled.
    """
    try:
        payment = get_object_or_404(Payment, pk=pk)
    except Exception:
        messages.error(request, "Payment not found.")
        return redirect('payment_list')

    if request.method == 'POST':
        action = request.POST.get('action')  # 'verify' or 'reject'

        try:
            if payment.payment_status != 'Pending':
                messages.error(request, "This payment has already been processed.")
                return redirect('payment_list')

            if action == 'verify':
                # ─── Mark payment as Completed ───────────────
                payment.payment_status = 'Completed'
                payment.save()

                # ─── Find and update related subscription ─────
                # Match by user + payment_date (same day) + Cash method
                try:
                    subscription = Subscription.objects.get(
                        user=payment.user,
                        subs_status='Active',
                        start_date=payment.payment_date.date(),
                    )
                    # Subscription is already Active for cash — just notify
                    notify_membership_purchased(
                        payment.user,
                        subscription.plan,
                        'Cash (Verified)'
                    )
                except Subscription.DoesNotExist:
                    pass
                except Exception:
                    pass

                # ─── Find and update related booking ──────────
                try:
                    booking = Booking.objects.filter(
                        user=payment.user,
                        booking_status='Pending',
                    ).order_by('-booking_date').first()

                    if booking:
                        booking.booking_status = 'Confirmed'
                        booking.save()
                        # Notify client about booking confirmation
                        notify_booking_status_changed(
                            payment.user, booking, 'Confirmed'
                        )
                except Exception:
                    pass

                messages.success(
                    request,
                    f"Payment of Rs. {payment.amount} verified. "
                    f"Related booking/subscription updated to Confirmed/Active."
                )

            elif action == 'reject':
                # ─── Mark payment as Failed ───────────────────
                payment.payment_status = 'Failed'
                payment.save()

                # ─── Cancel related pending booking ───────────
                try:
                    booking = Booking.objects.filter(
                        user=payment.user,
                        booking_status='Pending',
                    ).order_by('-booking_date').first()

                    if booking:
                        booking.booking_status = 'Cancelled'
                        booking.save()
                        notify_booking_status_changed(
                            payment.user, booking, 'Cancelled'
                        )
                except Exception:
                    pass

                # ─── Cancel related pending subscription ──────
                try:
                    subscription = Subscription.objects.get(
                        user=payment.user,
                        subs_status='Active',
                        start_date=payment.payment_date.date(),
                    )
                    subscription.subs_status = 'Cancelled'
                    subscription.save()
                    notify_membership_cancelled(payment.user, subscription)
                except Subscription.DoesNotExist:
                    pass
                except Exception:
                    pass

                messages.success(
                    request,
                    f"Payment rejected. Related booking/subscription has been cancelled."
                )

            return redirect('payment_list')

        except Exception as e:
            messages.error(request, "Failed to process payment action. Please try again.")
            return redirect('payment_list')

    return render(request, 'admin_panel/payments/payment_verify.html', {
        'payment': payment,
    })

# 9) FEEDBACK MANAGEMENT
# a) FEEDBACK LIST
@admin_required
def feedback_list(request):
    """
    Admin view of all client feedback/reviews for trainers.
    """
    try:
        feedbacks = Feedback.objects.select_related(
            'user', 'trainer__user'
        ).all().order_by('-date_given')
    except Exception:
        feedbacks = []
        messages.error(request, "Failed to load feedback.")

    feedbacks_page = paginate(feedbacks, request, 15)
    return render(request, 'admin_panel/feedback_list.html', {
        'feedbacks': feedbacks_page,
    })

# b) FEEDBACK DELETE
@admin_required
def feedback_delete(request, pk):
    """
    Admin can delete inappropriate feedback.
    """
    try:
        feedback = get_object_or_404(Feedback, pk=pk)
    except Exception:
        messages.error(request, "Feedback not found.")
        return redirect('feedback_list')

    if request.method == 'POST':
        try:
            feedback.delete()
            messages.success(request, "Feedback deleted successfully.")
        except Exception:
            messages.error(request, "Failed to delete feedback.")
        return redirect('feedback_list')

    return render(request, 'admin_panel/feedback_delete.html', {
        'feedback': feedback,
    })


# 10) REPORTS
@admin_required
def reports(request):
    try:
        report_type = request.GET.get('type', 'membership')
        period = request.GET.get('period', 'all')

        today = date.today()
        if period == 'week':
            start_filter = today - timedelta(weeks=1)
        elif period == 'month':
            start_filter = today - relativedelta(months=1)
        elif period == '3months':
            start_filter = today - relativedelta(months=3)
        else:
            start_filter = None

        # ─── Membership ───────────────────────────
        subscriptions = Subscription.objects.select_related('user', 'plan').all()
        if start_filter:
            subscriptions = subscriptions.filter(start_date__gte=start_filter)
        subscriptions = subscriptions.order_by('-start_date')

        subs_by_status = list(
            Subscription.objects.values('subs_status').annotate(count=Count('id'))
        )
        # Plain Python lists
        subs_status_labels = [item['subs_status'] for item in subs_by_status]
        subs_status_counts = [item['count'] for item in subs_by_status]

        plans_popularity = list(
            MembershipPlan.objects.annotate(
                sub_count=Count('subscription')
            ).values('plan_name', 'sub_count').order_by('-sub_count')
        )
        plans_labels = [item['plan_name'] for item in plans_popularity]
        plans_counts = [item['sub_count'] for item in plans_popularity]

        # ─── Bookings ─────────────────────────────
        bookings = Booking.objects.select_related(
            'user', 'schedule__trainer__user'
        ).all()
        if start_filter:
            bookings = bookings.filter(booking_date__gte=start_filter)
        bookings = bookings.order_by('-booking_date')

        bookings_by_status = list(
            Booking.objects.values('booking_status').annotate(count=Count('id'))
        )
        booking_status_labels = [item['booking_status'] for item in bookings_by_status]
        booking_status_counts = [item['count'] for item in bookings_by_status]

        monthly_bookings = list(
            Booking.objects.annotate(
                month=TruncMonth('booking_date')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')[:6]
        )
        monthly_booking_labels = [
            item['month'].strftime('%b %Y') for item in monthly_bookings
        ]
        monthly_booking_counts = [item['count'] for item in monthly_bookings]

        # ─── Trainer Performance ──────────────────
        trainer_performance = Trainer.objects.select_related('user').annotate(
            total_bookings=Count('schedules__bookings'),
            confirmed_bookings=Count(
                'schedules__bookings',
                filter=Q(schedules__bookings__booking_status='Confirmed')
            ),
            avg_rating=Avg('feedbacks__rating'),
        ).order_by('-total_bookings')

        trainer_names = [t.user.get_full_name() for t in trainer_performance]
        trainer_booking_counts_list = [t.total_bookings for t in trainer_performance]
        trainer_ratings = [
            round(float(t.avg_rating), 1) if t.avg_rating else 0
            for t in trainer_performance
        ]

        # ─── Revenue ──────────────────────────────
        total_revenue = Payment.objects.filter(
            payment_status='Completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        if start_filter:
            period_revenue = Payment.objects.filter(
                payment_status='Completed',
                payment_date__gte=start_filter
            ).aggregate(total=Sum('amount'))['total'] or 0
        else:
            period_revenue = total_revenue

    except Exception as e:
        import traceback
        print(f"[Report Error] {e}")
        print(traceback.format_exc())
        subscriptions = bookings = trainer_performance = []
        total_revenue = period_revenue = 0
        subs_status_labels = subs_status_counts = []
        plans_labels = plans_counts = []
        booking_status_labels = booking_status_counts = []
        monthly_booking_labels = monthly_booking_counts = []
        trainer_names = trainer_booking_counts_list = trainer_ratings = []
        messages.error(request, "Failed to generate reports.")

    if report_type == 'membership':
        data = paginate(subscriptions, request, 15)
    elif report_type == 'booking':
        data = paginate(bookings, request, 15)
    else:
        data = paginate(trainer_performance, request, 15)

    return render(request, 'admin_panel/reports.html', {
        'report_type': report_type,
        'period': period,
        'data': data,
        'total_revenue': total_revenue,
        'period_revenue': period_revenue,
        'subs_status_labels': subs_status_labels,
        'subs_status_counts': subs_status_counts,
        'plans_labels': plans_labels,
        'plans_counts': plans_counts,
        'booking_status_labels': booking_status_labels,
        'booking_status_counts': booking_status_counts,
        'monthly_booking_labels': monthly_booking_labels,
        'monthly_booking_counts': monthly_booking_counts,
        'trainer_names': trainer_names,
        'trainer_booking_counts': trainer_booking_counts_list,
        'trainer_ratings': trainer_ratings,
    })