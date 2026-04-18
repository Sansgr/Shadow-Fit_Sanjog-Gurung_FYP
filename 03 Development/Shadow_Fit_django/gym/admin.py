from django.contrib import admin
from .models import Booking, MembershipPlan, Notification, Payment, Schedule, Subscription, Trainer

# Register your models here.
admin.site.register(MembershipPlan)
admin.site.register(Trainer) 
admin.site.register(Schedule)
admin.site.register(Booking)
admin.site.register(Subscription)
admin.site.register(Payment)
admin.site.register(Notification)