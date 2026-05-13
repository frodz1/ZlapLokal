from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view),
    path('venues/', views.get_venues),
    path('venues/<int:pk>/', views.get_venue_detail),
    path('bookings/', views.booking_list_or_create),
    path('cities/', views.get_cities),
    path('config/', views.get_config, name='get_config'),
    path('bookings/<int:pk>/', views.booking_detail),
    

]