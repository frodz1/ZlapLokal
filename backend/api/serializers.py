from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Avg
from rest_framework import serializers
from .models import Provinces, Cities, Venues, Users, Bookings, SystemConfig, Reviews


def _money_decimal(value):
    return Decimal(value or 0).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _current_commission_rate():
    config = SystemConfig.objects.order_by('config_id').first()
    return Decimal(config.commission_rate) if config else Decimal('10')


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provinces
        fields = ['province_id', 'name']


class CitySerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source='province.name', read_only=True)

    class Meta:
        model = Cities
        fields = ['city_id', 'name', 'province', 'province_name']


class UserSerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source='province.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = Users
        fields = [
            'user_id', 'username', 'email', 'role',
            'province', 'province_name', 'city', 'city_name',
            'is_active', 'registration_date'
        ]


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Reviews
        fields = ['review_id', 'venue', 'venue_name', 'reviewer', 'reviewer_username', 'rating', 'comment', 'created_at']
        read_only_fields = ['venue', 'reviewer', 'created_at']


class VenueSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    province_name = serializers.CharField(source='city.province.name', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    photo_url = serializers.SerializerMethodField()
    client_price_per_day = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    booked_ranges = serializers.SerializerMethodField()

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    def get_client_price_per_day(self, obj):
        base = _money_decimal(obj.price_per_day)
        commission = _money_decimal(base * _current_commission_rate() / Decimal('100'))
        return float(_money_decimal(base + commission))

    def get_average_rating(self, obj):
        avg = obj.reviews.aggregate(avg=Avg('rating')).get('avg')
        return round(float(avg), 1) if avg else 0

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_reviews(self, obj):
        reviews = obj.reviews.select_related('reviewer').all()[:20]
        return ReviewSerializer(reviews, many=True).data

    def get_booked_ranges(self, obj):
        bookings = obj.bookings_set.exclude(status=Bookings.STATUS_CANCELLED).values('start_date', 'end_date', 'payment_status')
        return [
            {
                'start': b['start_date'].date().isoformat(),
                'end': b['end_date'].date().isoformat(),
                'payment_status': b['payment_status'],
            }
            for b in bookings
        ]

    def to_representation(self, obj):
        data = super().to_representation(obj)
        request = self.context.get('request')
        can_see_internal_price = False
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            username = request.user.username
            is_admin = request.user.is_staff or Users.objects.filter(username=username, role=Users.ROLE_ADMIN).exists()
            is_owner = obj.owner and obj.owner.username == username
            can_see_internal_price = bool(is_admin or is_owner)
        if not can_see_internal_price:
            data.pop('price_per_day', None)
            data.pop('owner_email', None)
            data.pop('owner_username', None)
            data.pop('is_active', None)
        return data

    class Meta:
        model = Venues
        fields = [
            'venue_id', 'owner', 'owner_email', 'owner_username',
            'city', 'city_name', 'province_name', 'name', 'street_address', 'description',
            'capacity', 'area_m2', 'price_per_day', 'client_price_per_day',
            'deposit', 'available_from', 'available_to', 'is_active', 'photo', 'photo_url',
            'average_rating', 'reviews_count', 'reviews', 'booked_ranges'
        ]
        read_only_fields = ['owner']


class BookingSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_address = serializers.CharField(source='venue.street_address', read_only=True)
    venue_city = serializers.CharField(source='venue.city.name', read_only=True)
    renter_username = serializers.CharField(source='renter.username', read_only=True)

    class Meta:
        model = Bookings
        fields = [
            'booking_id', 'venue', 'venue_name', 'venue_address', 'venue_city', 'renter', 'renter_username',
            'start_date', 'end_date', 'total_cost', 'owner_payout',
            'platform_commission', 'commission_rate_applied', 'payment_method', 'payment_status', 'status'
        ]
        read_only_fields = ['renter', 'total_cost', 'owner_payout', 'platform_commission', 'commission_rate_applied']


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = ['config_id', 'commission_rate']
