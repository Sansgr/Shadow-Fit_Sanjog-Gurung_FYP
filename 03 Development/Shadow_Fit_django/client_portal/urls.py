from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_dashboard, name='client_dashboard'),

    # Profile URLs
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),

    # Membership
    path('membership/', views.membership_list, name='membership_list'),
    path('membership/my/', views.my_membership, name='my_membership'),          
    path('membership/hold/', views.hold_membership, name='hold_membership'),    
    path('membership/unhold/', views.unhold_membership, name='unhold_membership'),
    path('membership/cancel/', views.cancel_membership, name='cancel_membership'),
    path('membership/<int:pk>/checkout/', views.membership_checkout, name='membership_checkout'),
    path('membership/<int:pk>/cash/', views.membership_cash_payment, name='membership_cash_payment'),
    path('membership/<int:pk>/khalti/', views.membership_khalti_initiate, name='membership_khalti_initiate'),
    path('membership/<int:pk>/khalti-verify/', views.membership_khalti_verify, name='membership_khalti_verify'),
    path('membership/<int:pk>/khalti-verify', views.membership_khalti_verify, name='membership_khalti_verify_noslash'),

    # Trainers & Booking
    path('trainers/', views.trainer_list, name='trainer_list'),
    path('trainers/<int:pk>/', views.trainer_detail, name='trainer_detail'),
    path('trainers/booking/<int:schedule_pk>/checkout/', views.booking_checkout, name='booking_checkout'),
    path('trainers/booking/<int:schedule_pk>/cash/', views.booking_cash_payment, name='booking_cash_payment'),
    path('trainers/booking/<int:schedule_pk>/khalti/', views.booking_khalti_initiate, name='booking_khalti_initiate'),
    path('trainers/booking/<int:schedule_pk>/khalti-verify/', views.booking_khalti_verify, name='booking_khalti_verify'),
    path('trainers/booking/<int:schedule_pk>/khalti-verify', views.booking_khalti_verify, name='booking_khalti_verify_noslash'),
    path('bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'), 
]