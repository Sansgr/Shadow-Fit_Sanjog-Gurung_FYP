import requests
from datetime import date
from dateutil.relativedelta import relativedelta

from django.conf import settings as django_settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

from client_portal.decorators import member_required
from client_portal.forms import CustomPasswordChangeForm, ProfileUpdateForm
from gym.models import Booking, MembershipPlan, Schedule, Trainer, Subscription, Payment



# Create your views here.
# 1) Client Dashboard
def client_dashboard(request):
    plans = MembershipPlan.objects.all().order_by('price')
    trainers = Trainer.objects.select_related('user').all()
    return render(request, 'client_portal/dashboard.html', {
        'plans': plans,
        'trainers': trainers,
    })

# 2) Profile Management
# a) VIEW PROFILE
@member_required
def view_profile(request):
    # Password change form
    if request.method == 'POST':
        password_form = CustomPasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully!")
            return redirect('view_profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        password_form = CustomPasswordChangeForm(request.user)

    return render(request, 'client_portal/profile/view_profile.html', {
        'password_form': password_form,
    })


# b) UPDATE PROFILE
@member_required
def update_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('view_profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'client_portal/profile/update_profile.html', {'form': form})


# 3) Membership Management
# a) MEMBERSHIP LIST 
def membership_list(request):
    plans = MembershipPlan.objects.all().order_by('price')
    active_subscription = None
    if request.user.is_authenticated:
        try:
            active_subscription = Subscription.objects.get(
                user=request.user,
                subs_status='Active'
            )
        except Subscription.DoesNotExist:
            pass
    return render(request, 'client_portal/membership/membership_list.html', {
        'plans': plans,
        'active_subscription': active_subscription,
    })


# b) MEMBERSHIP CHECKOUT
@member_required
def membership_checkout(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)

    # Check if already has active subscription
    if Subscription.objects.filter(user=request.user, subs_status='Active').exists():
        messages.error(request, "You already have an active membership plan.")
        return redirect('membership_list')

    return render(request, 'client_portal/membership/membership_checkout.html', {
        'plan': plan,
        'khalti_public_key': django_settings.KHALTI_PUBLIC_KEY,
    })


# c) MEMBERSHIP CASH PAYMENT
@member_required
def membership_cash_payment(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=plan.price,
            payment_method='Cash',
            platform=None,
            payment_status='Pending',
        )
        # Create subscription
        start = date.today()
        end = start + relativedelta(months=plan.duration)
        Subscription.objects.create(
            user=request.user,
            plan=plan,
            start_date=start,
            end_date=end,
            subs_status='Active',
        )
        messages.success(request, f"Membership purchased! Please pay Rs. {plan.price} at the front desk.")
        return redirect('my_membership')
    return redirect('membership_checkout', pk=pk)


# d) MEMBERSHIP KHALTI INITIATE
@member_required
def membership_khalti_initiate(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        amount_in_paisa = int(plan.price * 100)  # Khalti uses paisa
        payload = {
            "return_url": request.build_absolute_uri(f"/portal/membership/khalti-verify/{pk}/"),
            "website_url": request.build_absolute_uri("/"),
            "amount": amount_in_paisa,
            "purchase_order_id": f"PLAN-{pk}-{request.user.id}",
            "purchase_order_name": plan.plan_name,
            "customer_info": {
                "name": request.user.get_full_name(),
                "email": request.user.email,
                "phone": request.user.phone or "9800000000",
            }
        }
        headers = {
            "Authorization": f"Key {django_settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            "https://a.khalti.com/api/v2/epayment/initiate/",
            json=payload,
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            return redirect(data['payment_url'])
        else:
            messages.error(request, "Failed to initiate Khalti payment. Please try again.")
            return redirect('membership_checkout', pk=pk)
    return redirect('membership_checkout', pk=pk)


# e) MEMBERSHIP KHALTI VERIFY
@member_required
def membership_khalti_verify(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    pidx = request.GET.get('pidx')
    status = request.GET.get('status')

    if status == 'Completed' and pidx:
        # Verify with Khalti
        headers = {
            "Authorization": f"Key {django_settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            "https://a.khalti.com/api/v2/epayment/lookup/",
            json={"pidx": pidx},
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'Completed':
                # Create Payment record
                Payment.objects.create(
                    user=request.user,
                    amount=plan.price,
                    payment_method='Online',
                    platform='Khalti',
                    payment_status='Completed',
                )
                # Create Subscription
                start = date.today()
                end = start + relativedelta(months=plan.duration)
                Subscription.objects.create(
                    user=request.user,
                    plan=plan,
                    start_date=start,
                    end_date=end,
                    subs_status='Active',
                )
                messages.success(request, "Payment successful! Your membership is now active.")
                return redirect('my_membership')

    messages.error(request, "Payment failed or was cancelled. Please try again.")
    return redirect('membership_checkout', pk=pk)


# f) MY MEMBERSHIP
@member_required
def my_membership(request):
    subscription = None
    try:
        subscription = Subscription.objects.select_related('plan').get(
            user=request.user,
            subs_status='Active'
        )
    except Subscription.DoesNotExist:
        pass
    return render(request, 'client_portal/membership/my_membership.html', {
        'subscription': subscription,
    })


# 4) Trainer Booking
# a) TRAINER LIST 
def trainer_list(request):
    trainers = Trainer.objects.select_related('user').prefetch_related('schedules').all()
    return render(request, 'client_portal/trainers/trainer_list.html', {
        'trainers': trainers,
    })


# b) TRAINER DETAIL
def trainer_detail(request, pk):
    trainer = get_object_or_404(Trainer, pk=pk)
    schedules = Schedule.objects.filter(trainer=trainer)
    return render(request, 'client_portal/trainers/trainer_detail.html', {
        'trainer': trainer,
        'schedules': schedules,
    })


# c) BOOK TRAINER CHECKOUT
@member_required
def booking_checkout(request, schedule_pk):
    schedule = get_object_or_404(Schedule, pk=schedule_pk)

    # Check if client has active membership
    if not Subscription.objects.filter(user=request.user, subs_status='Active').exists():
        messages.error(request, "You need an active membership to book a trainer.")
        return redirect('membership_list')

    # Check if already has active booking for this schedule
    if Booking.objects.filter(
        user=request.user,
        booking_status__in=['Pending', 'Confirmed']
    ).exists():
        messages.error(request, "You already have an active trainer booking. Please cancel it before booking a new one.")
        return redirect('my_bookings')

    return render(request, 'client_portal/trainers/booking_checkout.html', {
        'schedule': schedule,
        'khalti_public_key': django_settings.KHALTI_PUBLIC_KEY,
        'duration_choices': Booking.DURATION_CHOICES,
        'today': date.today().isoformat(),
    })


# d) BOOKING CASH PAYMENT 
@member_required
def booking_cash_payment(request, schedule_pk):
    schedule = get_object_or_404(Schedule, pk=schedule_pk)
    if request.method == 'POST':
        duration = request.POST.get('duration')
        start_date = request.POST.get('start_date')

        if not duration or not start_date:
            messages.error(request, "Please select duration and start date.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)

        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d').date()

        # Calculate end date
        if duration == '1 Week':
            from datetime import timedelta
            end = start + timedelta(weeks=1)
        elif duration == '1 Month':
            end = start + relativedelta(months=1)
        elif duration == '3 Months':
            end = start + relativedelta(months=3)
        else:
            end = start + relativedelta(months=1)

        # Create Payment
        Payment.objects.create(
            user=request.user,
            amount=schedule.trainer.session_price,
            payment_method='Cash',
            platform=None,
            payment_status='Pending',
        )

        # Create Booking
        Booking.objects.create(
            user=request.user,
            schedule=schedule,
            duration=duration,
            start_date=start,
            end_date=end,
            booking_status='Pending',
        )

        messages.success(request, f"Booking confirmed! Please pay Rs. {schedule.trainer.session_price} at the front desk.")
        return redirect('my_bookings')
    return redirect('booking_checkout', schedule_pk=schedule_pk)


# e) BOOKING KHALTI INITIATE
@member_required
def booking_khalti_initiate(request, schedule_pk):
    schedule = get_object_or_404(Schedule, pk=schedule_pk)
    if request.method == 'POST':
        duration = request.POST.get('duration')
        start_date = request.POST.get('start_date')

        if not duration or not start_date:
            messages.error(request, "Please select duration and start date.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)

        # Store in session for verification step
        request.session['booking_duration'] = duration
        request.session['booking_start_date'] = start_date

        amount_in_paisa = int(schedule.trainer.session_price * 100)
        payload = {
            "return_url": request.build_absolute_uri(f"/portal/trainers/booking/{schedule_pk}/khalti-verify/"),
            "website_url": request.build_absolute_uri("/"),
            "amount": amount_in_paisa,
            "purchase_order_id": f"BOOKING-{schedule_pk}-{request.user.id}",
            "purchase_order_name": f"{schedule.trainer.user.get_full_name()} — {schedule.shift_name} Shift",
            "customer_info": {
                "name": request.user.get_full_name(),
                "email": request.user.email,
                "phone": request.user.phone or "9800000000",
            }
        }
        headers = {
            "Authorization": f"Key {django_settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            "https://a.khalti.com/api/v2/epayment/initiate/",
            json=payload,
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            return redirect(data['payment_url'])
        else:
            messages.error(request, "Failed to initiate Khalti payment. Please try again.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)
    return redirect('booking_checkout', schedule_pk=schedule_pk)


# f) BOOKING KHALTI VERIFY 
@member_required
def booking_khalti_verify(request, schedule_pk):
    schedule = get_object_or_404(Schedule, pk=schedule_pk)
    pidx = request.GET.get('pidx')
    status = request.GET.get('status')

    if status == 'Completed' and pidx:
        headers = {
            "Authorization": f"Key {django_settings.KHALTI_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            "https://a.khalti.com/api/v2/epayment/lookup/",
            json={"pidx": pidx},
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'Completed':
                duration = request.session.get('booking_duration', '1 Month')
                start_date_str = request.session.get('booking_start_date')

                from datetime import datetime, timedelta
                start = datetime.strptime(start_date_str, '%Y-%m-%d').date()

                if duration == '1 Week':
                    end = start + timedelta(weeks=1)
                elif duration == '1 Month':
                    end = start + relativedelta(months=1)
                elif duration == '3 Months':
                    end = start + relativedelta(months=3)
                else:
                    end = start + relativedelta(months=1)

                # Create Payment
                Payment.objects.create(
                    user=request.user,
                    amount=schedule.trainer.session_price,
                    payment_method='Online',
                    platform='Khalti',
                    payment_status='Completed',
                )

                # Create Booking
                Booking.objects.create(
                    user=request.user,
                    schedule=schedule,
                    duration=duration,
                    start_date=start,
                    end_date=end,
                    booking_status='Confirmed',
                )

                # Clear session
                del request.session['booking_duration']
                del request.session['booking_start_date']

                messages.success(request, "Payment successful! Your trainer has been booked.")
                return redirect('my_bookings')

    messages.error(request, "Payment failed or was cancelled. Please try again.")
    return redirect('booking_checkout', schedule_pk=schedule_pk)


# g) MY BOOKINGS 
@member_required
def my_bookings(request):
    bookings = Booking.objects.select_related(
        'schedule__trainer__user'
    ).filter(user=request.user).order_by('-booking_date')
    return render(request, 'client_portal/trainers/my_bookings.html', {
        'bookings': bookings,
    })


# h) CANCEL BOOKING 
@member_required
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if request.method == 'POST':
        if booking.booking_status in ['Pending', 'Confirmed']:
            booking.booking_status = 'Cancelled'
            booking.save()
            messages.success(request, "Booking cancelled successfully.")
        else:
            messages.error(request, "This booking cannot be cancelled.")
        return redirect('my_bookings')
    return render(request, 'client_portal/trainers/cancel_booking.html', {
        'booking': booking,
    })