from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from admin_panel.decorators import admin_required
from accounts.models import CustomUser
from client_portal.notifications import notify_membership_cancelled, notify_membership_hold, notify_membership_purchased, notify_membership_unhold
from gym.models import Booking, MembershipPlan, Payment, Schedule, Subscription, Trainer
from admin_panel.forms import ClientForm, MembershipPlanForm, ScheduleForm, TrainerUserForm, TrainerProfileForm, BookingForm, AdminSubscriptionForm 


# 1) ADMIN DASHBOARD 
@admin_required
def admin_dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


# 2) CLIENT MANAGEMENT VIEWS
# a) CLIENT LIST
@admin_required
def client_list(request):
    clients = CustomUser.objects.filter(role='Member').order_by('-date_joined')
    return render(request, 'admin_panel/clients/client_list.html', {'clients': clients})


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
    return render(request, 'admin_panel/plans/plan_list.html', {'plans': plans})


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
    return render(request, 'admin_panel/trainers/trainer_list.html', {'trainers': trainers})


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
            user.set_password(f"{user_form.cleaned_data.get('username')}@123")
            user.save()
            # Save trainer profile
            trainer = profile_form.save(commit=False)
            trainer.user = user
            trainer.save()
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
    # TO THIS:
    schedules = Schedule.objects.select_related('trainer__user').all().order_by('trainer__user__first_name', 'shift_name')
    return render(request, 'admin_panel/schedules/schedule_list.html', {'schedules': schedules})


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
    bookings = Booking.objects.select_related(
        'user', 'schedule__trainer__user'
    ).all().order_by('-booking_date')
    return render(request, 'admin_panel/bookings/booking_list.html', {'bookings': bookings})


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

    return render(request, 'admin_panel/subscriptions/subscription_list.html', {
        'subscriptions': subscriptions,
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

    return render(request, 'admin_panel/payments/payment_list.html', {
        'payments': payments,
    })


# b) PAYMENT VERIFY
@admin_required
def payment_verify(request, pk):
    """
    Admin verifies a pending cash payment —
    marks it as Completed.
    """
    try:
        payment = get_object_or_404(Payment, pk=pk)
    except Exception:
        messages.error(request, "Payment not found.")
        return redirect('payment_list')

    if request.method == 'POST':
        try:
            if payment.payment_status == 'Pending':
                payment.payment_status = 'Completed'
                payment.save()
                messages.success(
                    request,
                    f"Payment of Rs. {payment.amount} verified successfully."
                )
            else:
                messages.error(request, "This payment cannot be verified.")
        except Exception:
            messages.error(request, "Failed to verify payment. Please try again.")
        return redirect('payment_list')

    return render(request, 'admin_panel/payments/payment_verify.html', {
        'payment': payment,
    })