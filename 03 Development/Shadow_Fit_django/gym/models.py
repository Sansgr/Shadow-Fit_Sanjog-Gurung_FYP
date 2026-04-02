from django.db import models
from django.conf import settings

# Create your models here.
class MembershipPlan(models.Model):
    plan_name = models.CharField(max_length=50)
    duration = models.IntegerField(help_text="Duration in months")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.plan_name