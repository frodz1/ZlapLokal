from rest_framework import serializers
from .models import Cities, Venues, Users, Bookings

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Cities
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ['user_id', 'email', 'role']

class VenueSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    photo_url = serializers.SerializerMethodField()

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    class Meta:
        model = Venues
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Bookings
        fields = ['booking_id', 'venue', 'venue_name', 'renter', 'start_date', 'end_date', 'total_cost', 'system_commission', 'status']