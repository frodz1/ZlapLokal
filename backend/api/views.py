import os
from decimal import Decimal
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.utils.dateparse import parse_datetime
from .models import Cities, Venues, Bookings, Users
from .serializers import CitySerializer, VenueSerializer, BookingSerializer
from django.views.decorators.csrf import csrf_exempt
 
# --- AUTH ---
 
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
    email = request.data.get('email')
    password = request.data.get('password')
 
    if not username or not password or not email:
        return Response({'error': 'Wszystkie pola są wymagane'}, status=status.HTTP_400_BAD_REQUEST)
 
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Użytkownik o takim loginie już istnieje'}, status=status.HTTP_400_BAD_REQUEST)
 
    try:
        user = User.objects.create_user(username=username, email=email, password=password)
        Users.objects.get_or_create(username=username, email=email)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'username': user.username,
            'message': 'Konto utworzone pomyślnie'
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': f'Błąd podczas rejestracji: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
# --- VENUES & CITIES ---
 
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def get_venues(request):
    if request.method == 'GET':
        venues = Venues.objects.all().order_by('-venue_id')
        serializer = VenueSerializer(venues, many=True, context={'request': request})
        return Response(serializer.data)
 
    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({'error': 'Wymagane logowanie'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            custom_user = Users.objects.get(username=request.user.username)
        except Users.DoesNotExist:
            return Response({'error': 'Nie znaleziono profilu użytkownika'}, status=status.HTTP_400_BAD_REQUEST)
 
        serializer = VenueSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(owner=custom_user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities(request):
    cities = Cities.objects.all()
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)
 
@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def get_venue_detail(request, pk):
    try:
        venue = Venues.objects.get(venue_id=pk)
    except Venues.DoesNotExist:
        return Response({'error': 'Brak lokalu'}, status=404)
 
    if request.method == 'GET':
        serializer = VenueSerializer(venue, context={'request': request})
        return Response(serializer.data)
 
    elif request.method == 'DELETE':
        if not request.user.is_authenticated:
            return Response({'error': 'Wymagane logowanie'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            custom_user = Users.objects.get(username=request.user.username)
        except Users.DoesNotExist:
            return Response({'error': 'Nie znaleziono profilu użytkownika'}, status=status.HTTP_400_BAD_REQUEST)
 
        if venue.owner != custom_user:
            return Response({'error': 'Brak uprawnień – nie jesteś właścicielem tego lokalu'}, status=status.HTTP_403_FORBIDDEN)
 
        venue.delete()
        return Response({'message': 'Lokal usunięty'}, status=status.HTTP_204_NO_CONTENT)
 
# --- REZERWACJE ---
 
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def booking_list_or_create(request):
    try:
        custom_user = Users.objects.get(username=request.user.username)
    except Users.DoesNotExist:
        return Response({'error': 'Nie znaleziono profilu użytkownika.'}, status=status.HTTP_400_BAD_REQUEST)
 
    if request.method == 'GET':
        bookings = Bookings.objects.filter(renter=custom_user).order_by('-booking_id')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)
 
    if request.method == 'POST':
        venue_id = request.data.get('venue')
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
 
        if not venue_id or not start_date_str or not end_date_str:
            return Response({'error': 'Wszystkie pola są wymagane.'}, status=status.HTTP_400_BAD_REQUEST)
 
        try:
            venue = Venues.objects.get(venue_id=venue_id)
            start_date = parse_datetime(start_date_str)
            end_date = parse_datetime(end_date_str)
 
            if not start_date or not end_date or start_date.date() > end_date.date():
                return Response({'error': 'Nieprawidłowy zakres dat.'}, status=status.HTTP_400_BAD_REQUEST)
 
            delta = end_date.date() - start_date.date()
            days = delta.days + 1
 
            overlapping_bookings = Bookings.objects.filter(
                venue=venue,
                start_date__date__lte=end_date.date(),
                end_date__date__gte=start_date.date()
            ).exclude(status='ANULOWANO')
 
            if overlapping_bookings.exists():
                return Response({'error': 'Ten lokal jest już zajęty.'}, status=status.HTTP_400_BAD_REQUEST)
 
            commission_val = os.environ.get('COMMISSION_RATE', '10')
            commission_multiplier = Decimal('1') + (Decimal(commission_val) / Decimal('100'))
            calculated_total = Decimal(days) * venue.price_per_day * commission_multiplier
 
            booking = Bookings.objects.create(
                renter=custom_user,
                venue=venue,
                start_date=start_date,
                end_date=end_date,
                total_cost=calculated_total,
                status='ZAREZERWOWANO'
            )
 
            serializer = BookingSerializer(booking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
 
        except Venues.DoesNotExist:
            return Response({'error': 'Lokal nie istnieje.'}, status=404)
        except Exception as e:
            return Response({'error': f'Błąd: {str(e)}'}, status=500)
 
@csrf_exempt
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    try:
        booking = Bookings.objects.get(booking_id=pk, renter__username=request.user.username)
    except Bookings.DoesNotExist:
        return Response({'error': 'Nie znaleziono rezerwacji'}, status=status.HTTP_404_NOT_FOUND)
 
    serializer = BookingSerializer(booking, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
# --- CONFIG ---
 
@api_view(['GET'])
@permission_classes([AllowAny])
def get_config(request):
    commission = os.environ.get('COMMISSION_RATE', '10')
    return Response({'commission_rate': float(commission)})
 
