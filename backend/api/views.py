import os
from decimal import Decimal
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.utils.dateparse import parse_datetime
from .models import Cities, Venues, Bookings
from .serializers import CitySerializer, VenueSerializer, BookingSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user_id': user.id, 'username': user.username})
    return Response({'error': 'Błędne dane'}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Użytkownik istnieje'}, status=400)
    user = User.objects.create_user(username=username, password=password, email=email)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user_id': user.id, 'username': user.username}, status=201)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def get_venues(request):
    if request.method == 'GET':
        venues = Venues.objects.all().order_by('-venue_id')
        serializer = VenueSerializer(venues, many=True, context={'request': request})
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = VenueSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def booking_list_or_create(request):
    if request.method == 'GET':
        bookings = Bookings.objects.all().order_by('-booking_id')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        data = request.data
        try:
            venue = Venues.objects.get(venue_id=data.get('venue'))
        except Venues.DoesNotExist:
            return Response({'error': 'Brak lokalu'}, status=404)
        start = parse_datetime(data.get('start_date'))
        end = parse_datetime(data.get('end_date'))
        if not start or not end or start >= end:
            return Response({'error': 'Złe daty'}, status=400)
        days = (end - start).days or 1
        rate = Decimal(os.environ.get('COMMISSION_RATE', '0.10'))
        base = days * venue.price_per_day
        comm = (base * rate).quantize(Decimal('0.01'))
        booking_data = data.copy()
        booking_data['total_cost'] = base + comm
        booking_data['system_commission'] = comm
        booking_data['status'] = 'Confirmed'
        serializer = BookingSerializer(data=booking_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities(request):
    cities = Cities.objects.all()
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_venue_detail(request, pk):
    try:
        venue = Venues.objects.get(venue_id=pk)
        serializer = VenueSerializer(venue, context={'request': request})
        return Response(serializer.data)
    except Venues.DoesNotExist:
        return Response({'error': 'Brak lokalu'}, status=404)
