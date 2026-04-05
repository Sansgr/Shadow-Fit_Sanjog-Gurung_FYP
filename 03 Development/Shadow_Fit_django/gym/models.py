from django.db import models
from django.conf import settings
from datetime import date

# Create your models here.
# 1) MembershipPlan model to store different gym membership plans
class MembershipPlan(models.Model):
    plan_name = models.CharField(max_length=50)
    duration = models.IntegerField(help_text="Duration in months")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.plan_name
    

# 2) Trainer model to store information about gym trainers
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
    

# 3) Schedule model to store trainer availability
class Schedule(models.Model):
    SHIFT_CHOICES = (
        ('Morning', 'Morning'),
        ('Day', 'Day'),
        ('Evening', 'Evening'),
    )

    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    # FROM THIS:
    shift_name = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='Morning')
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ('trainer', 'shift_name')  # one shift per trainer

    def __str__(self):
        return f"{self.trainer.user.get_full_name()} — {self.shift_name} ({self.start_time} - {self.end_time})"
    

# 4) Booking model to store information about user bookings with trainers
class Booking(models.Model):
    DURATION_CHOICES = (
        ('1 Week', '1 Week'),
        ('1 Month', '1 Month'),
        ('3 Months', '3 Months'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'Member'}
    )
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default='1 Month')
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(blank=True, null=True)  
    booking_date = models.DateTimeField(auto_now_add=True)  
    booking_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.schedule.trainer.user.get_full_name()} ({self.duration})"