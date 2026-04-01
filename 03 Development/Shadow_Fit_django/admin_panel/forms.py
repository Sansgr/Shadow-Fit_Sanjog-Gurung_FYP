from django import forms
from accounts.models import CustomUser

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