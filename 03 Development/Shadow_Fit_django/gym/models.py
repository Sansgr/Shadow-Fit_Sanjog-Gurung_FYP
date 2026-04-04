from django.db import models
from django.conf import settings

# Create your models here.
# MembershipPlan model to store different gym membership plans
class MembershipPlan(models.Model):
    plan_name = models.CharField(max_length=50)
    duration = models.IntegerField(help_text="Duration in months")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.plan_name
    

# Trainer model to store information about gym trainers
class Trainer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'Trainer'}
    )
    specialty = models.CharField(max_length=100)
    experience = models.IntegerField(help_text="Years of experience")
    session_price = models.DecimalField(max_digits=8, decimal_places=2)
    bio = models.CharField(max_length=250, blank=True)

    def __str__(self):
        return self.user.get_full_name()
    

# Schedule model to store trainer availability
class Schedule(models.Model):
    DAY_CHOICES = (
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    )

    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    day_of_week = models.CharField(max_length=20, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.trainer.user.get_full_name()} — {self.day_of_week} ({self.start_time} - {self.end_time})"