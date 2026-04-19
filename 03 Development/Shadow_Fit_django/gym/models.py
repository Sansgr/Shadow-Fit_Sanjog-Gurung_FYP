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
    
    
# 5) Subscription model to store information about user subscriptions to membership plans
class Subscription(models.Model):
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('On Hold', 'On Hold'),
        ('Expired', 'Expired'),
        ('Cancelled', 'Cancelled'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'Member'}
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.SET_NULL,
        null=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    subs_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    hold_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.plan.plan_name} ({self.subs_status})"
    

# 6) Payment model to store information about user payments for subscriptions and bookings
class Payment(models.Model):
    METHOD_CHOICES = (
        ('Cash', 'Cash'),
        ('Online', 'Online'),       
    )
    PLATFORM_CHOICES = (
        ('Khalti', 'Khalti'), 
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.user.get_full_name()} — Rs.{self.amount} ({self.payment_status})"
    

# 7) Notification model to store notifications for users about their membership and bookings
class Notification(models.Model):
    TYPE_CHOICES = (
        # Membership related
        ('membership_purchased', 'Membership Purchased'),
        ('membership_hold', 'Membership On Hold'),
        ('membership_unhold', 'Membership Resumed'),
        ('membership_cancelled', 'Membership Cancelled'),
        # Booking related
        ('booking_created', 'Booking Created'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_completed', 'Booking Completed'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']  # newest first

    def __str__(self):
        return f"{self.user.username} — {self.title}"
    
    
# 8) Inquiry model to store contact inquiries from clients
class Inquiry(models.Model):
    """
    Stores contact inquiries from clients.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True  # Allow anonymous inquiries
    )
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=500)
    date_sent = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} — {self.date_sent.strftime('%Y-%m-%d')}"
    
# 9) Feedback model to store client reviews/ratings for trainers after completed bookings
class Feedback(models.Model):
    """
    Client review/rating for a trainer.
    Only allowed after booking is Completed.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'Member'}
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    booking = models.OneToOneField(
        'Booking',
        on_delete=models.CASCADE,
        related_name='feedback',
        null=True, blank=True
    )
    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)]  # 1-5 stars
    )
    comment = models.TextField(max_length=500, blank=True)
    date_given = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} → {self.trainer.user.get_full_name()} ({self.rating}★)"