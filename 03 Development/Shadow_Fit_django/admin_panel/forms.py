from django import forms
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from accounts.models import CustomUser
from gym.models import Booking, MembershipPlan, Schedule, Subscription, Trainer

# 1) Form for Client Management in Admin Panel
class ClientForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phone',
            'photo',
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Exclude current instance when updating
        qs = CustomUser.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Email is already registered.")
        return email
    
# 2) Form for Membership Plan Management in Admin Panel
class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = [
            'plan_name',
            'duration',
            'price',
            'description',
        ]

# 3) Form for Trainer Management in Admin Panel
class TrainerUserForm(forms.ModelForm):
    """Handles CustomUser fields for trainer"""
    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phone',
            'photo',
        ]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = CustomUser.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Email is already registered.")
        return email

# 4) Form for Trainer Profile Management in Admin Panel
class TrainerProfileForm(forms.ModelForm):
    """Handles Trainer profile fields"""
    class Meta:
        model = Trainer
        fields = [
            'specialty',
            'experience',
            'session_price',
            'bio',
        ]

# 5) Form for Schedule Management in Admin Panel
class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = [
            'trainer',
            'shift_name',
            'start_time',
            'end_time',
        ]

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError("End time must be after start time.")

        return cleaned_data
    
# 6) Form for Booking Management in Admin Panel
class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'user',
            'schedule',
            'duration',
            'start_date',
            'booking_status',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = CustomUser.objects.filter(role='Member').order_by('first_name')
        self.fields['schedule'].queryset = Schedule.objects.select_related('trainer__user').all()

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        schedule = cleaned_data.get('schedule')
        duration = cleaned_data.get('duration')
        start_date = cleaned_data.get('start_date')

        # Duplicate booking check
        if user and schedule:
            duplicate = Booking.objects.filter(
                user=user,
                schedule=schedule,
                booking_status__in=['Pending', 'Confirmed']
            )
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise forms.ValidationError("This client already has an active booking for this schedule.")

        # Calculate end_date based on duration
        if start_date and duration:
            if duration == '1 Week':
                cleaned_data['end_date'] = start_date + timedelta(weeks=1)
            elif duration == '1 Month':
                cleaned_data['end_date'] = start_date + relativedelta(months=1)
            elif duration == '3 Months':
                cleaned_data['end_date'] = start_date + relativedelta(months=3)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Assign calculated end_date from clean()
        instance.end_date = self.cleaned_data.get('end_date')
        if commit:
            instance.save()
        return instance
    
# 7) Form for Subscription Management in Admin Panel
class AdminSubscriptionForm(forms.ModelForm):
    """
    Form for admin to manually create or update client subscriptions.
    end_date is auto-calculated in the view — not shown in form.
    """
    class Meta:
        model = Subscription
        fields = [
            'user',
            'plan',
            'start_date',
            'subs_status',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show Members in user dropdown
        self.fields['user'].queryset = CustomUser.objects.filter(
            role='Member'
        ).order_by('first_name')
        # Format user display nicely
        self.fields['user'].label_from_instance = lambda obj: (
            f"{obj.get_full_name()} (@{obj.username})"
        )