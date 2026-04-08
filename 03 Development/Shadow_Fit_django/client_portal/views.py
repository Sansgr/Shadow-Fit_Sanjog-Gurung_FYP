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
from gym.models import MembershipPlan, Trainer, Subscription, Payment



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
