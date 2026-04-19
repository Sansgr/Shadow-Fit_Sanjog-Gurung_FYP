import requests
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from django.db import models
from django.conf import settings as django_settings
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from client_portal import models
from client_portal.decorators import member_required
from client_portal.forms import CustomPasswordChangeForm, ProfileUpdateForm
from gym.models import Booking, Feedback, MembershipPlan, Notification, Schedule, Trainer, Subscription, Payment
from client_portal.notifications import (
    notify_membership_purchased,
    notify_membership_hold,
    notify_membership_unhold,
    notify_membership_cancelled,
    notify_booking_created,
    notify_booking_status_changed,
)


# HELPER FUNCTIONS
# a) Calculate booking price based on duration
# Session price is per week, so multiply accordingly
def get_booking_price(session_price, duration):
    try:
        if duration == '1 Week':
            return session_price * 1
        elif duration == '1 Month':
            return session_price * 4
        elif duration == '3 Months':
            return session_price * 12
        return session_price
    except Exception as e:
        # Fallback to base price if calculation fails
        return session_price


# b) Calculate end date from start date + duration
def calculate_end_date(start, duration):
    try:
        if duration == '1 Week':
            return start + timedelta(weeks=1)
        elif duration == '1 Month':
            return start + relativedelta(months=1)
        elif duration == '3 Months':
            return start + relativedelta(months=3)
        return start + relativedelta(months=1)
    except Exception as e:
        # Fallback to 1 month if calculation fails
        return start + relativedelta(months=1)



# 1) CLIENT DASHBOARD
# Public page — shows plans and trainers overview
def client_dashboard(request):
    try:
        plans = MembershipPlan.objects.all().order_by('price')
        trainers = Trainer.objects.select_related('user').all()
    except Exception as e:
        plans = []
        trainers = []
        messages.error(request, "Failed to load dashboard data. Please try again.")

    return render(request, 'client_portal/dashboard.html', {
        'plans': plans,
        'trainers': trainers,
    })



# 2) PROFILE MANAGEMENT
# a) VIEW PROFILE + CHANGE PASSWORD
# Handles both viewing profile info and password update form
@member_required
def view_profile(request):
    if request.method == 'POST':
        # Handle password change form submission
        password_form = CustomPasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            try:
                user = password_form.save()
                # Keep user logged in after password change
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully!")
                return redirect('view_profile')
            except Exception as e:
                messages.error(request, "Failed to update password. Please try again.")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        # Empty password form for GET request
        password_form = CustomPasswordChangeForm(request.user)

    return render(request, 'client_portal/profile/view_profile.html', {
        'password_form': password_form,
    })


# b) UPDATE PROFILE
# Allows client to update personal info and photo
@member_required
def update_profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Profile updated successfully!")
                return redirect('view_profile')
            except Exception as e:
                messages.error(request, "Failed to update profile. Please try again.")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        # Pre-fill form with current user data
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'client_portal/profile/update_profile.html', {
        'form': form,
    })



# 3) MEMBERSHIP MANAGEMENT
# a) MEMBERSHIP LIST
# Public — shows all plans, highlights active subscription if any
def membership_list(request):
    """
    Public — shows all plans with search and pagination.
    """
    try:
        plans = MembershipPlan.objects.all().order_by('price')
    except Exception:
        plans = []
        messages.error(request, "Failed to load membership plans.")

    # ─── Search/Filter ────────────────────────────────
    search = request.GET.get('search', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    duration = request.GET.get('duration', '')

    if search:
        plans = plans.filter(plan_name__icontains=search)
    if min_price:
        try:
            plans = plans.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            plans = plans.filter(price__lte=float(max_price))
        except ValueError:
            pass
    if duration:
        try:
            plans = plans.filter(duration=int(duration))
        except ValueError:
            pass

    # ─── Pagination ───────────────────────────────────
    paginator = Paginator(plans, 6)  # 6 plans per page
    page = request.GET.get('page', 1)
    try:
        plans_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        plans_page = paginator.page(1)

    # Check subscription status
    active_subscription = None
    if request.user.is_authenticated:
        try:
            active_subscription = Subscription.objects.get(
                user=request.user,
                subs_status__in=['Active', 'On Hold']
            )
        except Subscription.DoesNotExist:
            pass
        except Exception:
            messages.error(request, "Failed to load subscription status.")

    return render(request, 'client_portal/membership/membership_list.html', {
        'plans': plans_page,
        'active_subscription': active_subscription,
        'search': search,
        'min_price': min_price,
        'max_price': max_price,
        'duration': duration,
    })


# b) MEMBERSHIP CHECKOUT
# Gate before payment — blocks if already subscribed
@member_required
def membership_checkout(request, pk):
    try:
        plan = get_object_or_404(MembershipPlan, pk=pk)
    except Exception as e:
        messages.error(request, "Plan not found.")
        return redirect('membership_list')

    # Block if already has active or on hold subscription
    if Subscription.objects.filter(
        user=request.user,
        subs_status__in=['Active', 'On Hold']
    ).exists():
        messages.error(request, "You already have an active or on hold membership plan.")
        return redirect('membership_list')

    return render(request, 'client_portal/membership/membership_checkout.html', {
        'plan': plan,
        'khalti_public_key': django_settings.KHALTI_PUBLIC_KEY,
    })


# c) MEMBERSHIP CASH PAYMENT
# Creates subscription immediately, payment marked Pending (pay at desk)
@member_required
def membership_cash_payment(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)

    if request.method == 'POST':
        # Re-check subscription status — user may have subscribed in another tab
        if Subscription.objects.filter(
            user=request.user,
            subs_status__in=['Active', 'On Hold']
        ).exists():
            messages.error(request, "You already have an active or on hold membership plan.")
            return redirect('membership_list')

        try:
            # Record cash payment as Pending until confirmed at front desk
            Payment.objects.create(
                user=request.user,
                amount=plan.price,
                payment_method='Cash',
                platform=None,
                payment_status='Pending',
            )

            # Calculate subscription dates
            start = date.today()
            end = start + relativedelta(months=plan.duration)

            # update_or_create handles case where cancelled/expired subscription exists
            # (OneToOneField prevents create if record already exists for this user)
            Subscription.objects.update_or_create(
                user=request.user,
                defaults={
                    'plan': plan,
                    'start_date': start,
                    'end_date': end,
                    'subs_status': 'Active',
                    'hold_date': None,  # clear any previous hold date
                }
            )

            # Send notification and email to client and admin
            notify_membership_purchased(request.user, plan, 'Cash')

            messages.success(
                request,
                f"Membership purchased! Please pay Rs. {plan.price} at the front desk."
            )

            return redirect('my_membership')

        except Exception as e:
            messages.error(request, "Failed to process membership. Please try again.")
            return redirect('membership_checkout', pk=pk)

    return redirect('membership_checkout', pk=pk)


# d) MEMBERSHIP KHALTI INITIATE
# Initiates Khalti payment — redirects to Khalti payment page
@member_required
def membership_khalti_initiate(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)

    if request.method == 'POST':
        try:
            # Khalti requires amount in paisa (1 Rs = 100 paisa)
            amount_in_paisa = int(plan.price * 100)

            payload = {
                # Return URL must NOT have trailing slash — Khalti strips it
                "return_url": request.build_absolute_uri(f"/portal/membership/{pk}/khalti-verify"),
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

            # Call Khalti API to initiate payment
            response = requests.post(
                "https://a.khalti.com/api/v2/epayment/initiate/",
                json=payload,
                headers=headers,
                timeout=10  # prevent hanging requests
            )

            if response.status_code == 200:
                data = response.json()
                # Redirect user to Khalti payment page
                return redirect(data['payment_url'])
            else:
                messages.error(request, "Failed to initiate Khalti payment. Please try again.")
                return redirect('membership_checkout', pk=pk)

        except requests.exceptions.Timeout:
            messages.error(request, "Payment gateway timed out. Please try again.")
            return redirect('membership_checkout', pk=pk)
        except Exception as e:
            messages.error(request, "An error occurred. Please try again.")
            return redirect('membership_checkout', pk=pk)

    return redirect('membership_checkout', pk=pk)


# e) MEMBERSHIP KHALTI VERIFY
# Called by Khalti after payment — verifies and creates subscription
@member_required
def membership_khalti_verify(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)

    # Get payment status and token from Khalti callback
    pidx = request.GET.get('pidx')
    status = request.GET.get('status')

    if status == 'Completed' and pidx:
        try:
            headers = {
                "Authorization": f"Key {django_settings.KHALTI_SECRET_KEY}",
                "Content-Type": "application/json",
            }

            # Verify payment with Khalti lookup API
            response = requests.post(
                "https://a.khalti.com/api/v2/epayment/lookup/",
                json={"pidx": pidx},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 'Completed':
                    # Re-check before creating — prevent duplicate subscriptions
                    if Subscription.objects.filter(
                        user=request.user,
                        subs_status__in=['Active', 'On Hold']
                    ).exists():
                        messages.error(request, "You already have an active membership.")
                        return redirect('my_membership')

                    # Record successful online payment
                    Payment.objects.create(
                        user=request.user,
                        amount=plan.price,
                        payment_method='Online',
                        platform='Khalti',
                        payment_status='Completed',
                    )

                    # Calculate subscription dates
                    start = date.today()
                    end = start + relativedelta(months=plan.duration)

                    # update_or_create handles existing cancelled/expired records
                    Subscription.objects.update_or_create(
                        user=request.user,
                        defaults={
                            'plan': plan,
                            'start_date': start,
                            'end_date': end,
                            'subs_status': 'Active',
                            'hold_date': None,
                        }
                    )
                    # Send notification and email to client and admin
                    notify_membership_purchased(request.user, plan, 'Online (Khalti)')

                    messages.success(request, "Payment successful! Your membership is now active.")

                    return redirect('my_membership')

        except requests.exceptions.Timeout:
            messages.error(request, "Payment verification timed out. Contact support.")
            return redirect('my_membership')
        except Exception as e:
            messages.error(request, "Verification failed. Please contact support.")
            return redirect('my_membership')

    # Payment was cancelled or failed
    messages.error(request, "Payment failed or was cancelled. Please try again.")
    return redirect('membership_checkout', pk=pk)


# f) MY MEMBERSHIP
# Shows client's current subscription details
@member_required
def my_membership(request):
    """
    Shows current subscription and history of past subscriptions.
    """
    subscription = None
    try:
        subscription = Subscription.objects.select_related('plan').get(
            user=request.user,
            subs_status__in=['Active', 'On Hold']
        )
    except Subscription.DoesNotExist:
        pass
    except Exception:
        messages.error(request, "Failed to load membership details.")

    # ─── History: past cancelled/expired subscriptions ─
    try:
        history = Subscription.objects.select_related('plan').filter(
            user=request.user,
            subs_status__in=['Cancelled', 'Expired']
        ).order_by('-end_date')
    except Exception:
        history = []

    # Paginate history
    paginator = Paginator(history, 5)
    page = request.GET.get('history_page', 1)
    try:
        history_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        history_page = paginator.page(1)

    return render(request, 'client_portal/membership/my_membership.html', {
        'subscription': subscription,
        'history': history_page,
    })


# g) HOLD MEMBERSHIP
# Pauses membership — saves hold_date to calculate remaining days on unhold
@member_required
def hold_membership(request):
    try:
        subscription = get_object_or_404(Subscription, user=request.user, subs_status='Active')
    except Exception as e:
        messages.error(request, "No active membership found.")
        return redirect('my_membership')

    if request.method == 'POST':
        try:
            # Save today as hold_date — needed to calculate remaining days on unhold
            subscription.hold_date = date.today()
            subscription.subs_status = 'On Hold'
            subscription.save()

            # Notify client
            notify_membership_hold(request.user, subscription)
            messages.success(request, "Your membership has been put on hold.")
            return redirect('my_membership')
        except Exception as e:
            messages.error(request, "Failed to hold membership. Please try again.")

    return render(request, 'client_portal/membership/hold_membership.html', {
        'subscription': subscription,
    })


# h) UNHOLD MEMBERSHIP
# Resumes membership — recalculates end_date based on remaining days
@member_required
def unhold_membership(request):
    try:
        subscription = get_object_or_404(Subscription, user=request.user, subs_status='On Hold')
    except Exception as e:
        messages.error(request, "No on-hold membership found.")
        return redirect('my_membership')

    if request.method == 'POST':
        try:
            today = date.today()

            # Calculate remaining days at the time of hold
            # remaining = original end_date - hold_date
            if subscription.hold_date:
                remaining_days = (subscription.end_date - subscription.hold_date).days
            else:
                # Fallback: if hold_date wasn't saved, keep original end_date
                remaining_days = (subscription.end_date - today).days

            # New end_date = today + remaining days
            new_end_date = today + timedelta(days=remaining_days)

            # Update subscription
            subscription.subs_status = 'Active'
            subscription.end_date = new_end_date
            subscription.hold_date = None  # clear hold date
            subscription.save()

            # Notify client with new end date
            notify_membership_unhold(request.user, subscription, new_end_date)
            messages.success(
                request,
                f"Membership resumed! New expiry date: {new_end_date.strftime('%B %d, %Y')}"
            )
            return redirect('my_membership')

        except Exception as e:
            messages.error(request, "Failed to unhold membership. Please try again.")

    # Calculate remaining days to show on confirmation page
    remaining_days = 0
    try:
        if subscription.hold_date:
            remaining_days = (subscription.end_date - subscription.hold_date).days
        else:
            remaining_days = (subscription.end_date - date.today()).days
    except Exception:
        pass

    return render(request, 'client_portal/membership/unhold_membership.html', {
        'subscription': subscription,
        'remaining_days': remaining_days,
        'new_end_date': date.today() + timedelta(days=remaining_days),
    })


# i) CANCEL MEMBERSHIP
# Permanently cancels active or on-hold membership
@member_required
def cancel_membership(request):
    try:
        subscription = get_object_or_404(
            Subscription,
            user=request.user,
            subs_status__in=['Active', 'On Hold']
        )
    except Exception as e:
        messages.error(request, "No active membership found.")
        return redirect('my_membership')

    if request.method == 'POST':
        try:
            subscription.subs_status = 'Cancelled'
            subscription.hold_date = None
            subscription.save()
            # Notify client and admin
            notify_membership_cancelled(request.user, subscription)
            messages.success(request, "Your membership has been cancelled.")
            return redirect('my_membership')
        except Exception as e:
            messages.error(request, "Failed to cancel membership. Please try again.")

    return render(request, 'client_portal/membership/cancel_membership.html', {
        'subscription': subscription,
    })



# 4) TRAINER & BOOKING
# a) TRAINER LIST
# Public — shows all trainers with their shifts
def trainer_list(request):
    """
    Public — shows all trainers with search, filter and pagination.
    """
    try:
        trainers = Trainer.objects.select_related('user').prefetch_related('schedules').all()
    except Exception:
        trainers = []
        messages.error(request, "Failed to load trainers.")

    # ─── Search/Filter ────────────────────────────────
    search = request.GET.get('search', '')
    specialty = request.GET.get('specialty', '')
    shift = request.GET.get('shift', '')

    if search:
        trainers = trainers.filter(
            user__first_name__icontains=search
        ) | trainers.filter(
            user__last_name__icontains=search
        ) | trainers.filter(
            specialty__icontains=search
        )
    if specialty:
        trainers = trainers.filter(specialty__icontains=specialty)
    if shift:
        trainers = trainers.filter(schedules__shift_name=shift).distinct()

    # Get unique specialties for filter dropdown
    try:
        all_specialties = Trainer.objects.values_list(
            'specialty', flat=True
        ).distinct().order_by('specialty')
    except Exception:
        all_specialties = []

    # ─── Pagination ───────────────────────────────────
    paginator = Paginator(trainers, 6)  # 6 trainers per page
    page = request.GET.get('page', 1)
    try:
        trainers_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        trainers_page = paginator.page(1)

    return render(request, 'client_portal/trainers/trainer_list.html', {
        'trainers': trainers_page,
        'search': search,
        'specialty': specialty,
        'shift': shift,
        'all_specialties': all_specialties,
        'shift_choices': ['Morning', 'Day', 'Evening'],
    })


# b) TRAINER DETAIL
# Public — shows trainer profile and available shifts for booking
def trainer_detail(request, pk):
    try:
        trainer = get_object_or_404(Trainer, pk=pk)
        schedules = Schedule.objects.filter(trainer=trainer)
    except Exception as e:
        messages.error(request, "Trainer not found.")
        return redirect('trainer_list')

    return render(request, 'client_portal/trainers/trainer_detail.html', {
        'trainer': trainer,
        'schedules': schedules,
    })


# c) BOOKING CHECKOUT
# Gate before payment — checks membership and existing bookings
@member_required
def booking_checkout(request, schedule_pk):
    try:
        schedule = get_object_or_404(Schedule, pk=schedule_pk)
    except Exception as e:
        messages.error(request, "Schedule not found.")
        return redirect('trainer_list')

    # Must have active membership to book a trainer
    if not Subscription.objects.filter(
        user=request.user,
        subs_status='Active'
    ).exists():
        messages.error(request, "You need an active membership to book a trainer.")
        return redirect('membership_list')

    # Can only have one active booking at a time
    if Booking.objects.filter(
        user=request.user,
        booking_status__in=['Pending', 'Confirmed']
    ).exists():
        messages.error(
            request,
            "You already have an active trainer booking. Please cancel it before booking a new one."
        )
        return redirect('my_bookings')

    # Pre-calculate prices for each duration option
    # Session price is per week — multiply accordingly
    base_price = schedule.trainer.session_price
    duration_prices = {
        '1 Week': base_price * 1,
        '1 Month': base_price * 4,
        '3 Months': base_price * 12,
    }

    return render(request, 'client_portal/trainers/booking_checkout.html', {
        'schedule': schedule,
        'khalti_public_key': django_settings.KHALTI_PUBLIC_KEY,
        'duration_choices': Booking.DURATION_CHOICES,
        'duration_prices': duration_prices,
        'today': date.today().isoformat(),
    })


# d) BOOKING CASH PAYMENT
# Creates booking immediately, payment marked Pending (pay at desk)
@member_required
def booking_cash_payment(request, schedule_pk):
    schedule = get_object_or_404(Schedule, pk=schedule_pk)

    if request.method == 'POST':
        duration = request.POST.get('duration')
        start_date = request.POST.get('start_date')

        # Validate required fields
        if not duration or not start_date:
            messages.error(request, "Please select duration and start date.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)

        booking = None
        try:
            # Parse date string to date object
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = calculate_end_date(start, duration)
            amount = get_booking_price(schedule.trainer.session_price, duration)

            # Record cash payment as Pending until paid at desk
            Payment.objects.create(
                user=request.user,
                amount=amount,
                payment_method='Cash',
                platform=None,
                payment_status='Pending',
            )

            # Create booking as Pending until admin/trainer confirms
            booking = Booking.objects.create(
                user=request.user,
                schedule=schedule,
                duration=duration,
                start_date=start,
                end_date=end,
                booking_status='Pending',
            )

            # Notify client and admin about new booking
            if booking:
                notify_booking_created(request.user, booking)

            messages.success(
                request,
                f"Booking submitted! Please pay Rs. {amount} at the front desk."
            )
            return redirect('my_bookings')

        except ValueError:
            messages.error(request, "Invalid date format. Please try again.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)
        except Exception as e:
            messages.error(request, "Failed to create booking. Please try again.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)

    return redirect('booking_checkout', schedule_pk=schedule_pk)


# e) BOOKING KHALTI INITIATE
# Initiates Khalti payment for trainer booking
@member_required
def booking_khalti_initiate(request, schedule_pk):
    schedule = get_object_or_404(Schedule, pk=schedule_pk)

    if request.method == 'POST':
        duration = request.POST.get('duration')
        start_date = request.POST.get('start_date')

        # Validate required fields
        if not duration or not start_date:
            messages.error(request, "Please select duration and start date.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)

        try:
            # Store booking details in session — needed after Khalti redirects back
            request.session['booking_duration'] = duration
            request.session['booking_start_date'] = start_date

            amount = get_booking_price(schedule.trainer.session_price, duration)
            amount_in_paisa = int(amount * 100)  # Khalti requires paisa

            payload = {
                # No trailing slash — Khalti strips it on return
                "return_url": request.build_absolute_uri(
                    f"/portal/trainers/booking/{schedule_pk}/khalti-verify"
                ),
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

            # Call Khalti API
            response = requests.post(
                "https://a.khalti.com/api/v2/epayment/initiate/",
                json=payload,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return redirect(data['payment_url'])
            else:
                messages.error(request, "Failed to initiate Khalti payment. Please try again.")
                return redirect('booking_checkout', schedule_pk=schedule_pk)

        except requests.exceptions.Timeout:
            messages.error(request, "Payment gateway timed out. Please try again.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)
        except Exception as e:
            messages.error(request, "An error occurred. Please try again.")
            return redirect('booking_checkout', schedule_pk=schedule_pk)

    return redirect('booking_checkout', schedule_pk=schedule_pk)


# f) BOOKING KHALTI VERIFY
# Called by Khalti after payment — verifies and creates booking
@member_required
def booking_khalti_verify(request, schedule_pk):
    schedule = get_object_or_404(Schedule, pk=schedule_pk)

    # Get payment result from Khalti callback params
    pidx = request.GET.get('pidx')
    status = request.GET.get('status')

    if status == 'Completed' and pidx:
        try:
            headers = {
                "Authorization": f"Key {django_settings.KHALTI_SECRET_KEY}",
                "Content-Type": "application/json",
            }

            # Verify payment with Khalti lookup API
            response = requests.post(
                "https://a.khalti.com/api/v2/epayment/lookup/",
                json={"pidx": pidx},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 'Completed':
                    # Retrieve booking details stored in session before Khalti redirect
                    duration = request.session.get('booking_duration', '1 Month')
                    start_date_str = request.session.get('booking_start_date')

                    if not start_date_str:
                        messages.error(request, "Session expired. Please try booking again.")
                        return redirect('booking_checkout', schedule_pk=schedule_pk)

                    # Parse and calculate dates
                    start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    end = calculate_end_date(start, duration)
                    amount = get_booking_price(schedule.trainer.session_price, duration)

                    # Record successful online payment
                    Payment.objects.create(
                        user=request.user,
                        amount=amount,
                        payment_method='Online',
                        platform='Khalti',
                        payment_status='Completed',
                    )

                    booking = None
                    # Create booking — online payment = auto Confirmed
                    booking = Booking.objects.create(
                        user=request.user,
                        schedule=schedule,
                        duration=duration,
                        start_date=start,
                        end_date=end,
                        booking_status='Confirmed',
                    )
                    
                    # Notify client and admin
                    if booking:
                        notify_booking_created(request.user, booking)

                    # Clear session data safely
                    request.session.pop('booking_duration', None)
                    request.session.pop('booking_start_date', None)

                    messages.success(request, "Payment successful! Your trainer has been booked.")
                    return redirect('my_bookings')

        except requests.exceptions.Timeout:
            messages.error(request, "Payment verification timed out. Contact support.")
            return redirect('my_bookings')
        except Exception as e:
            messages.error(request, "Verification failed. Please contact support.")
            return redirect('my_bookings')

    # Payment was cancelled or failed on Khalti side
    messages.error(request, "Payment failed or was cancelled. Please try again.")
    return redirect('booking_checkout', schedule_pk=schedule_pk)


# g) MY BOOKINGS
# Shows all bookings for the logged-in client
@member_required
def my_bookings(request):
    """
    Shows active bookings and booking history with pagination.
    """
    try:
        # Active bookings — Pending or Confirmed
        active_bookings = Booking.objects.select_related(
            'schedule__trainer__user'
        ).filter(
            user=request.user,
            booking_status__in=['Pending', 'Confirmed']
        ).order_by('-booking_date')
    except Exception:
        active_bookings = []
        messages.error(request, "Failed to load bookings.")

    try:
        # History — Cancelled or Completed
        history = Booking.objects.select_related(
            'schedule__trainer__user'
        ).filter(
            user=request.user,
            booking_status__in=['Cancelled', 'Completed']
        ).order_by('-booking_date')
    except Exception:
        history = []

    # Paginate history
    paginator = Paginator(history, 5)
    page = request.GET.get('history_page', 1)
    try:
        history_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        history_page = paginator.page(1)

    return render(request, 'client_portal/trainers/my_bookings.html', {
        'bookings': active_bookings,
        'history': history_page,
    })


# h) CANCEL BOOKING
# Allows client to cancel a Pending or Confirmed booking
@member_required
def cancel_booking(request, pk):
    try:
        # Ensure booking belongs to this user
        booking = get_object_or_404(Booking, pk=pk, user=request.user)
    except Exception as e:
        messages.error(request, "Booking not found.")
        return redirect('my_bookings')

    if request.method == 'POST':
        try:
            if booking.booking_status in ['Pending', 'Confirmed']:
                booking.booking_status = 'Cancelled'
                booking.save()
                # Notify client about cancellation
                notify_booking_status_changed(request.user, booking, 'Cancelled')
                messages.success(request, "Booking cancelled successfully.")
            else:
                messages.error(request, "This booking cannot be cancelled.")
        except Exception as e:
            messages.error(request, "Failed to cancel booking. Please try again.")
        return redirect('my_bookings')

    return render(request, 'client_portal/trainers/cancel_booking.html', {
        'booking': booking,
    })




# 5) NOTIFICATIONS 
# a) NOTIFICATIONS LIST 
"""
Shows all notifications for the logged-in client.
Marks all unread notifications as read on page open.
"""
@member_required
def notifications_list(request):
    try:
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')

        # Mark all unread as read
        notifications.filter(is_read=False).update(is_read=True)

    except Exception:
        notifications = []
        messages.error(request, "Failed to load notifications.")

    # Paginate — 5 per page
    paginator = Paginator(notifications, 5)
    page = request.GET.get('page', 1)
    try:
        notifications_page = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        notifications_page = paginator.page(1)

    return render(request, 'client_portal/notifications/notifications_list.html', {
        'notifications': notifications_page,
    })

    return render(request, 'client_portal/notifications/notifications_list.html', {
        'notifications': notifications,
    })


# b) UNREAD NOTIFICATION COUNT
"""
Returns unread notification count.
Used internally — context processor handles template injection.
"""
def get_unread_count(request):
    if request.user.is_authenticated and hasattr(request.user, 'role'):
        if request.user.role == 'Member':
            try:
                return Notification.objects.filter(
                    user=request.user,
                    is_read=False
                ).count()
            except Exception:
                return 0
    return 0


# 6) STATIC PAGES
# a) ABOUT US
def about_us(request):
    """Static about us page."""
    return render(request, 'client_portal/about.html')

# b) CONTACT US
def contact_us(request):
    """
    Contact us page — handles inquiry form submission.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not all([name, email, subject, message]):
            messages.error(request, "Please fill in all fields.")
            return render(request, 'client_portal/contact.html')

        try:
            # Send inquiry email to admin
            from client_portal.notifications import send_email, get_admin_emails
            inquiry_message = (
                f"New Contact Inquiry\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Subject: {subject}\n\n"
                f"Message:\n{message}"
            )
            for admin_email in get_admin_emails():
                send_email(
                    subject=f"Shadow Fit — Contact Inquiry: {subject}",
                    message=inquiry_message,
                    recipient_email=admin_email,
                )

            # Save to Inquiry model if user is logged in
            if request.user.is_authenticated:
                from gym.models import Inquiry
                Inquiry.objects.create(
                    user=request.user,
                    subject=subject,
                    message=message,
                )

            messages.success(
                request,
                "Your message has been sent! We'll get back to you soon."
            )
            return redirect('contact_us')

        except Exception as e:
            messages.error(request, "Failed to send message. Please try again.")

    return render(request, 'client_portal/contact.html')


# 7) TRAINER REVIEWS
# a) REVIEW TRAINER 
@member_required
def review_trainer(request, booking_pk):
    """
    Client can review a trainer only after booking is Completed.
    One review per completed booking.
    """
    try:
        # Booking must belong to this user and be Completed
        booking = get_object_or_404(
            Booking,
            pk=booking_pk,
            user=request.user,
            booking_status='Completed'
        )
    except Exception:
        messages.error(request, "You can only review a trainer after completing a session.")
        return redirect('my_bookings')

    # Check if already reviewed this booking
    if hasattr(booking, 'feedback') and booking.feedback:
        messages.error(request, "You have already reviewed this booking.")
        return redirect('my_bookings')

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Please select a valid rating (1-5).")
            return render(request, 'client_portal/trainers/review_trainer.html', {
                'booking': booking,
            })

        try:
            Feedback.objects.create(
                user=request.user,
                trainer=booking.schedule.trainer,
                booking=booking,
                rating=rating,
                comment=comment,
            )
            messages.success(
                request,
                f"Thank you for reviewing {booking.schedule.trainer.user.get_full_name()}!"
            )
            return redirect('my_bookings')
        except Exception as e:
            messages.error(request, "Failed to submit review. Please try again.")

    return render(request, 'client_portal/trainers/review_trainer.html', {
        'booking': booking,
    })


# b) TRAINER REVIEWS (public)
def trainer_reviews(request, trainer_pk):
    """
    Shows all reviews for a specific trainer.
    """
    try:
        trainer = get_object_or_404(Trainer, pk=trainer_pk)
        feedbacks = Feedback.objects.select_related('user').filter(
            trainer=trainer
        ).order_by('-date_given')

        # Calculate average rating
        avg_rating = feedbacks.aggregate(
            avg=models.Avg('rating')
        )['avg'] or 0
        avg_rating = round(avg_rating, 1)

    except Exception:
        messages.error(request, "Failed to load reviews.")
        return redirect('trainer_list')

    return render(request, 'client_portal/trainers/trainer_reviews.html', {
        'trainer': trainer,
        'feedbacks': feedbacks,
        'avg_rating': avg_rating,
    })