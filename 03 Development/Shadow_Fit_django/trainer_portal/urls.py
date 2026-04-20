from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.trainer_dashboard, name='trainer_dashboard'),

    # Profile
    path('profile/', views.trainer_profile, name='trainer_profile'),

    # Bookings
    path('bookings/', views.trainer_bookings, name='trainer_bookings'),
    path('bookings/<int:pk>/accept/', views.accept_booking, name='accept_booking'),
    path('bookings/<int:pk>/reject/', views.reject_booking, name='reject_booking'),

    # Reviews
    path('reviews/', views.trainer_reviews, name='trainer_reviews'),

    # Schedule
    path('schedule/', views.trainer_schedule, name='trainer_schedule'),
]