from django.contrib import admin
from .models import MembershipPlan, Schedule, Trainer

# Register your models here.
admin.site.register(MembershipPlan)
admin.site.register(Trainer) 
admin.site.register(Schedule) 