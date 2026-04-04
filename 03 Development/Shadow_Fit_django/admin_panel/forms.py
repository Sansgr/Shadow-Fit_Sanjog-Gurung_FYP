from django import forms
from accounts.models import CustomUser
from gym.models import MembershipPlan, Trainer

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