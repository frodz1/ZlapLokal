from django.contrib import admin
from .models import Provinces, Cities, Users, Venues, Bookings, SystemConfig, Reviews


@admin.register(Provinces)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('province_id', 'name')
    search_fields = ('name',)


@admin.register(Cities)
class CityAdmin(admin.ModelAdmin):
    list_display = ('city_id', 'name', 'province')
    list_filter = ('province',)
    search_fields = ('name', 'province__name')


@admin.register(Users)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'username', 'email', 'role', 'province', 'city', 'is_active', 'registration_date')
    list_filter = ('role', 'is_active', 'province')
    search_fields = ('username', 'email')
    readonly_fields = ('registration_date',)


@admin.register(Venues)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('venue_id', 'name', 'street_address', 'city', 'capacity', 'area_m2', 'price_per_day', 'deposit', 'available_from', 'available_to', 'owner', 'is_active')
    list_filter = ('city__province', 'city', 'is_active')
    search_fields = ('name', 'description', 'street_address', 'owner__email')


@admin.register(Bookings)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'venue', 'renter', 'start_date', 'end_date', 'total_cost', 'payment_method', 'payment_status', 'platform_commission', 'owner_payout', 'commission_rate_applied', 'status')
    list_filter = ('status', 'payment_method', 'payment_status', 'start_date')
    search_fields = ('venue__name', 'renter__email')


@admin.register(Reviews)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('review_id', 'venue', 'reviewer', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('venue__name', 'reviewer__username', 'comment')
    readonly_fields = ('created_at',)


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('config_id', 'commission_rate')
