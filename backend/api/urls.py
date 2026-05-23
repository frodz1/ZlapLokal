from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('me/', views.me_view, name='me'),
    path('venues/', views.get_venues, name='venues'),
    path('my-venues/', views.my_venues, name='my-venues'),
    path('venues/<int:pk>/', views.get_venue_detail, name='venue-detail'),
    path('venues/<int:pk>/reviews/', views.venue_reviews, name='venue-reviews'),
    path('bookings/', views.booking_list_or_create, name='bookings'),
    path('bookings/<int:pk>/', views.booking_detail, name='booking-detail'),
    path('provinces/', views.get_provinces, name='provinces'),
    path('cities/', views.get_cities, name='cities'),
    path('config/', views.get_config, name='get-config'),
    path('admin/dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('admin/users/<int:pk>/', views.admin_update_user, name='admin-update-user'),
    path('admin/config/', views.admin_update_config, name='admin-update-config'),
    path('owner/dashboard/', views.owner_dashboard, name='owner-dashboard'),
]
