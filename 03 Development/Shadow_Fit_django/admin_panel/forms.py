from django import forms
from accounts.models import CustomUser
from gym.models import MembershipPlan, Schedule, Trainer

# Form for Client Management in Admin Panel
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
    
# Form for Membership Plan Management in Admin Panel
class MembershipPlanForm(forms.ModelForm):
    class Meta:
        model = MembershipPlan
        fields = [
            'plan_name',
            'duration',
            'price',
            'description',
        ]

# Form for Trainer Management in Admin Panel
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

# Form for Trainer Profile Management in Admin Panel
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

# Form for Schedule Management in Admin Panel
class ScheduleForm(forms.ModelForm):                
    class Meta:
        model = Schedule
        fields = [
            'trainer',
            'day_of_week',
            'start_time',
            'end_time',
        ]

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        trainer = cleaned_data.get('trainer')
        day_of_week = cleaned_data.get('day_of_week')

        # end time must be after start time
        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError("End time must be after start time.")

        # Check for duplicate schedule for same trainer on same day and overlapping time
        if trainer and day_of_week and start_time and end_time:
            overlapping = Schedule.objects.filter(
                trainer=trainer,
                day_of_week=day_of_week,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise forms.ValidationError("This trainer already has a schedule that overlaps with this time slot.")

        return cleaned_data