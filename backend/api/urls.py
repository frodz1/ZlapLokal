from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view),
    path('venues/', views.get_venues),
    path('venues/<int:pk>/', views.get_venue_detail),
    path('bookings/', views.booking_list_or_create),
    path('cities/', views.get_cities),
]