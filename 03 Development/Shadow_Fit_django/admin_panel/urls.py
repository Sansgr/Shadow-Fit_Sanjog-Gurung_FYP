from django.urls import path
from . import views

urlpatterns = [
    # Admin Dashboard
    path('', views.admin_dashboard, name='admin_dashboard'),

    # Client URLs
    path('clients/', views.client_list, name='client_list'),
    path('clients/add/', views.client_add, name='client_add'),
    path('clients/<int:pk>/update/', views.client_update, name='client_update'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),

    # Plan URLs
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/add/', views.plan_add, name='plan_add'),
    path('plans/<int:pk>/update/', views.plan_update, name='plan_update'),
    path('plans/<int:pk>/delete/', views.plan_delete, name='plan_delete'),

    # Trainer URLs
    path('trainers/', views.trainer_list, name='trainer_list'),
    path('trainers/add/', views.trainer_add, name='trainer_add'),
    path('trainers/<int:pk>/update/', views.trainer_update, name='trainer_update'),
    path('trainers/<int:pk>/delete/', views.trainer_delete, name='trainer_delete'),

    # Schedule URLs
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/add/', views.schedule_add, name='schedule_add'),
    path('schedules/<int:pk>/update/', views.schedule_update, name='schedule_update'),
    path('schedules/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),

    # Booking URLs
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/add/', views.booking_add, name='booking_add'),
    path('bookings/<int:pk>/update/', views.booking_update, name='booking_update'),
    path('bookings/<int:pk>/delete/', views.booking_delete, name='booking_delete'),
]