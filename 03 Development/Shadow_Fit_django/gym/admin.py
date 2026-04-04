from django.contrib import admin
from .models import MembershipPlan, Trainer

# Register your models here.
admin.site.register(MembershipPlan)
admin.site.register(Trainer)  