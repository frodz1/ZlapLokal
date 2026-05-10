from django.contrib import admin
from .models import Cities, Venues, Bookings

@admin.register(Venues)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'price_per_day')
    search_fields = ('name',)

@admin.register(Cities)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Bookings)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'venue', 'start_date', 'status')