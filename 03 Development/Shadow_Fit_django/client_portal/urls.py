from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_dashboard, name='client_dashboard'),

    # Profile URLs
    path('profile/', views.view_profile, name='view_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),

    # Membership
    path('membership/', views.membership_list, name='membership_list'),
    path('membership/<int:pk>/checkout/', views.membership_checkout, name='membership_checkout'),
    path('membership/<int:pk>/cash/', views.membership_cash_payment, name='membership_cash_payment'),
    path('membership/<int:pk>/khalti/', views.membership_khalti_initiate, name='membership_khalti_initiate'),
    path('membership/<int:pk>/khalti-verify/', views.membership_khalti_verify, name='membership_khalti_verify'),
    path('membership/my/', views.my_membership, name='my_membership'),
]