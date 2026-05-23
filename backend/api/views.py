import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Provinces, Cities, Venues, Bookings, Users, SystemConfig, Reviews
from .serializers import (
    ProvinceSerializer,
    CitySerializer,
    VenueSerializer,
    BookingSerializer,
    UserSerializer,
    ReviewSerializer,
)


PUBLIC_ROLES = {Users.ROLE_RENTER, Users.ROLE_OWNER}
ADMIN_ROLES = {Users.ROLE_ADMIN}
BOOKING_STATUSES = {
    Bookings.STATUS_PENDING,
    Bookings.STATUS_CONFIRMED,
    Bookings.STATUS_PAID,
    Bookings.STATUS_DONE,
    Bookings.STATUS_CANCELLED,
}
PAYMENT_METHODS = {Bookings.PAYMENT_ONLINE, Bookings.PAYMENT_CASH}


def error_response(message, http_status=status.HTTP_400_BAD_REQUEST, field=None):
    payload = {'error': message}
    if field:
        payload['field'] = field
    return Response(payload, status=http_status)


def get_app_user(django_user):
    """Zwraca profil aplikacji przypięty do zalogowanego użytkownika Django.

    Poprzednio szukaliśmy profilu tylko po idealnie takim samym loginie.
    Przy starych wolumenach bazy albo ręcznie tworzonych kontach mogło dojść do
    rozjazdu wielkości liter w loginie. Wtedy backend widział użytkownika, ale
    nie potrafił konsekwentnie przypisać do niego lokali. Teraz używamy
    dopasowania case-insensitive i normalizujemy login w profilu aplikacji.
    """
    username = (django_user.username or '').strip()
    try:
        app_user = Users.objects.select_related('province', 'city').get(username=username)
    except Users.DoesNotExist:
        app_user = Users.objects.select_related('province', 'city').get(username__iexact=username)
        if app_user.username != username:
            app_user.username = username
            app_user.save(update_fields=['username'])
    return app_user


def require_admin(request):
    if not request.user.is_authenticated:
        return None, error_response('Musisz się zalogować.', status.HTTP_401_UNAUTHORIZED)
    try:
        app_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return None, error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)
    if app_user.role not in ADMIN_ROLES:
        return None, error_response('Brak uprawnień administratora.', status.HTTP_403_FORBIDDEN)
    return app_user, None


def current_commission_rate():
    config = SystemConfig.objects.order_by('config_id').first()
    if config:
        return Decimal(config.commission_rate)
    return Decimal(os.environ.get('COMMISSION_RATE', '10'))


def money_decimal(value):
    return Decimal(value or 0).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def split_booking_amount(days, price_per_day, commission_rate):
    owner_payout = money_decimal(Decimal(days) * Decimal(price_per_day))
    platform_commission = money_decimal(owner_payout * Decimal(commission_rate) / Decimal('100'))
    total_cost = money_decimal(owner_payout + platform_commission)
    return owner_payout, platform_commission, total_cost


def validate_city_and_province(city_id, province_id=None):
    if not city_id:
        return None, error_response('Wybierz miasto.', field='city')
    try:
        city = Cities.objects.select_related('province').get(city_id=city_id)
    except (Cities.DoesNotExist, ValueError, TypeError):
        return None, error_response('Wybrane miasto nie istnieje.', field='city')

    if province_id:
        try:
            province_id_int = int(province_id)
        except (ValueError, TypeError):
            return None, error_response('Wybrane województwo jest nieprawidłowe.', field='province')
        if city.province_id != province_id_int:
            return None, error_response('Miasto nie pasuje do wybranego województwa.', field='city')
    return city, None


def parse_required_date(raw, field, label):
    value = parse_date(raw) if raw else None
    if not value:
        return None, error_response(f'Podaj poprawną datę: {label}.', field=field)
    return value, None


def booking_within_availability(venue, start_date, end_date):
    start_day = start_date.date()
    end_day = end_date.date()
    if venue.available_from and start_day < venue.available_from:
        return False
    if venue.available_to and end_day > venue.available_to:
        return False
    return True



def sum_booking_money(queryset):
    totals = queryset.aggregate(
        gross_revenue=Sum('total_cost'),
        platform_commission=Sum('platform_commission'),
        owner_payout=Sum('owner_payout'),
    )
    return {
        'gross_revenue': totals['gross_revenue'] or Decimal('0'),
        'platform_commission': totals['platform_commission'] or Decimal('0'),
        'owner_payout': totals['owner_payout'] or Decimal('0'),
    }


def payment_split_stats(active_booking_qs):
    # Zapłacone = Payment_Status = OPLACONA.
    # Oczekujące = aktywne rezerwacje, które jeszcze nie są opłacone.
    total = sum_booking_money(active_booking_qs)
    paid = sum_booking_money(active_booking_qs.filter(payment_status=Bookings.PAYMENT_PAID))
    pending = sum_booking_money(active_booking_qs.filter(payment_status=Bookings.PAYMENT_PENDING))
    return {
        **total,
        'paid_gross_revenue': paid['gross_revenue'],
        'paid_platform_commission': paid['platform_commission'],
        'paid_owner_payout': paid['owner_payout'],
        'pending_gross_revenue': pending['gross_revenue'],
        'pending_platform_commission': pending['platform_commission'],
        'pending_owner_payout': pending['owner_payout'],
    }


def build_monthly_payment_report(active_booking_qs):
    month_totals = defaultdict(lambda: {
        'bookings': 0,
        'gross_revenue': Decimal('0'),
        'platform_commission': Decimal('0'),
        'owner_payout': Decimal('0'),
        'paid_gross_revenue': Decimal('0'),
        'paid_platform_commission': Decimal('0'),
        'paid_owner_payout': Decimal('0'),
        'pending_gross_revenue': Decimal('0'),
        'pending_platform_commission': Decimal('0'),
        'pending_owner_payout': Decimal('0'),
    })
    for booking in active_booking_qs:
        key = timezone.localtime(booking.start_date).strftime('%Y-%m') if timezone.is_aware(booking.start_date) else booking.start_date.strftime('%Y-%m')
        gross = booking.total_cost or Decimal('0')
        commission = booking.platform_commission or Decimal('0')
        payout = booking.owner_payout or Decimal('0')
        month_totals[key]['bookings'] += 1
        month_totals[key]['gross_revenue'] += gross
        month_totals[key]['platform_commission'] += commission
        month_totals[key]['owner_payout'] += payout
        if booking.payment_status == Bookings.PAYMENT_PAID:
            month_totals[key]['paid_gross_revenue'] += gross
            month_totals[key]['paid_platform_commission'] += commission
            month_totals[key]['paid_owner_payout'] += payout
        else:
            month_totals[key]['pending_gross_revenue'] += gross
            month_totals[key]['pending_platform_commission'] += commission
            month_totals[key]['pending_owner_payout'] += payout

    return [
        {
            'month': month,
            'bookings': value['bookings'],
            'gross_revenue': float(value['gross_revenue']),
            'platform_commission': float(value['platform_commission']),
            'owner_payout': float(value['owner_payout']),
            'paid_gross_revenue': float(value['paid_gross_revenue']),
            'paid_platform_commission': float(value['paid_platform_commission']),
            'paid_owner_payout': float(value['paid_owner_payout']),
            'pending_gross_revenue': float(value['pending_gross_revenue']),
            'pending_platform_commission': float(value['pending_platform_commission']),
            'pending_owner_payout': float(value['pending_owner_payout']),
            'revenue': float(value['gross_revenue']),
        }
        for month, value in sorted(month_totals.items())[-6:]
    ]


# --- AUTH ---

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''

    if not username or not password:
        return error_response('Podaj login i hasło.', status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        return error_response('Nieprawidłowy login lub hasło.', status.HTTP_400_BAD_REQUEST)

    try:
        app_user = get_app_user(user)
    except Users.DoesNotExist:
        app_user = Users.objects.create(
            username=user.username,
            email=user.email or f'{user.username}@example.local',
            password_hash='HASHED_IN_DJANGO_AUTH_USER',
            role=Users.ROLE_RENTER,
        )

    if not app_user.is_active or not user.is_active:
        return error_response('To konto jest zablokowane. Skontaktuj się z administratorem.', status.HTTP_403_FORBIDDEN)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        'token': token.key,
        'user_id': app_user.user_id,
        'username': user.username,
        'email': app_user.email,
        'role': app_user.role,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    username = (request.data.get('username') or '').strip()
    email = (request.data.get('email') or '').strip().lower()
    password = request.data.get('password') or ''
    role = request.data.get('role') or Users.ROLE_RENTER
    province_id = request.data.get('province')
    city_id = request.data.get('city')

    if not username or not email or not password:
        return error_response('Wypełnij login, e-mail i hasło.', status.HTTP_400_BAD_REQUEST)

    if role not in PUBLIC_ROLES:
        return error_response('Wybierz poprawny typ konta: najemca albo właściciel.', field='role')

    if User.objects.filter(username__iexact=username).exists() or Users.objects.filter(username__iexact=username).exists():
        return error_response('Ten login jest już zajęty. Wybierz inny login.', status.HTTP_409_CONFLICT, field='username')

    if User.objects.filter(email__iexact=email).exists() or Users.objects.filter(email__iexact=email).exists():
        return error_response('Podany adres e-mail jest już zajęty. Użyj innego adresu albo zaloguj się.', status.HTTP_409_CONFLICT, field='email')

    province = None
    if province_id:
        try:
            province = Provinces.objects.get(province_id=province_id)
        except (Provinces.DoesNotExist, ValueError, TypeError):
            return error_response('Wybrane województwo nie istnieje.', field='province')

    city = None
    if city_id:
        city, city_error = validate_city_and_province(city_id, province_id)
        if city_error:
            return city_error
        province = city.province

    try:
        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            app_user = Users.objects.create(
                username=username,
                email=email,
                password_hash='HASHED_IN_DJANGO_AUTH_USER',
                role=role,
                province=province,
                city=city,
                is_active=True,
            )
            token, _ = Token.objects.get_or_create(user=user)
    except Exception:
        return error_response('Nie udało się utworzyć konta. Sprawdź dane i spróbuj ponownie.', status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'token': token.key,
        'user_id': app_user.user_id,
        'username': user.username,
        'email': app_user.email,
        'role': app_user.role,
        'message': 'Konto utworzone pomyślnie.',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_view(request):
    try:
        app_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        return Response(UserSerializer(app_user).data)

    new_role = request.data.get('role')
    if new_role:
        if app_user.role == Users.ROLE_ADMIN:
            return error_response('Administrator nie zmienia swojej roli w ustawieniach konta. Użyj panelu admina, żeby nie zablokować sobie dostępu.', status.HTTP_403_FORBIDDEN)
        if new_role not in PUBLIC_ROLES:
            return error_response('Możesz wybrać tylko: najemca albo właściciel lokalu.', status.HTTP_400_BAD_REQUEST, field='role')
        app_user.role = new_role
        app_user.save()
        User.objects.filter(username=app_user.username).update(is_staff=False, is_superuser=False)

    return Response({
        **UserSerializer(app_user).data,
        'message': 'Ustawienia konta zapisane.',
    })


# --- VENUES, PROVINCES & CITIES ---

@api_view(['GET'])
@permission_classes([AllowAny])
def get_provinces(request):
    provinces = Provinces.objects.all().order_by('name')
    serializer = ProvinceSerializer(provinces, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_cities(request):
    province_id = request.query_params.get('province')
    cities = Cities.objects.select_related('province').all().order_by('province__name', 'name')
    if province_id:
        cities = cities.filter(province_id=province_id)
    serializer = CitySerializer(cities, many=True)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def get_venues(request):
    if request.method == 'GET':
        venues = Venues.objects.select_related('city__province', 'owner').filter(is_active=True).order_by('-venue_id')
        serializer = VenueSerializer(venues, many=True, context={'request': request})
        return Response(serializer.data)

    if not request.user.is_authenticated:
        return error_response('Musisz się zalogować, aby dodać lokal.', status.HTTP_401_UNAUTHORIZED)

    try:
        custom_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    if custom_user.role not in {Users.ROLE_OWNER, Users.ROLE_ADMIN}:
        return error_response('Tylko właściciel albo administrator może dodawać lokale.', status.HTTP_403_FORBIDDEN)

    name = (request.data.get('name') or '').strip()
    street_address = (request.data.get('street_address') or '').strip()
    price = request.data.get('price_per_day')
    capacity = request.data.get('capacity')
    area_m2 = request.data.get('area_m2')
    deposit = request.data.get('deposit') or 0
    city_id = request.data.get('city')
    province_id = request.data.get('province')
    available_from_raw = request.data.get('available_from')
    available_to_raw = request.data.get('available_to')

    if not name:
        return error_response('Podaj nazwę lokalu.', field='name')
    if not street_address:
        return error_response('Podaj dokładny adres ulicy.', field='street_address')

    city, city_error = validate_city_and_province(city_id, province_id)
    if city_error:
        return city_error

    available_from, date_error = parse_required_date(available_from_raw, 'available_from', 'dostępny od')
    if date_error:
        return date_error
    available_to, date_error = parse_required_date(available_to_raw, 'available_to', 'dostępny do')
    if date_error:
        return date_error
    if available_from > available_to:
        return error_response('Data „dostępny do” musi być późniejsza niż „dostępny od”.', field='available_to')

    try:
        price_decimal = Decimal(str(price))
        deposit_decimal = Decimal(str(deposit))
        area_decimal = Decimal(str(area_m2))
        capacity_int = int(capacity)
    except (InvalidOperation, ValueError, TypeError):
        return error_response('Cena, kaucja, powierzchnia i pojemność muszą być liczbami.', field='numbers')

    if price_decimal <= 0:
        return error_response('Cena za dobę musi być większa od 0.', field='price_per_day')
    if deposit_decimal < 0:
        return error_response('Kaucja nie może być ujemna.', field='deposit')
    if capacity_int <= 0:
        return error_response('Pojemność musi być większa od 0.', field='capacity')
    if area_decimal <= 0:
        return error_response('Powierzchnia musi być większa od 0.', field='area_m2')

    # Tworzymy lokal ręcznie, zamiast polegać na ModelSerializerze przy zapisie.
    # Dzięki temu Owner_ID i Is_Active są ustawiane wprost i nie ma sytuacji,
    # w której frontend dostaje zielony komunikat, ale /api/my-venues/ zwraca [].
    try:
        with transaction.atomic():
            venue = Venues.objects.create(
                owner=custom_user,
                city=city,
                name=name,
                street_address=street_address,
                description=(request.data.get('description') or '').strip(),
                capacity=capacity_int,
                area_m2=area_decimal,
                price_per_day=price_decimal,
                deposit=deposit_decimal,
                available_from=available_from,
                available_to=available_to,
                is_active=True,
                photo=request.FILES.get('photo') if 'photo' in request.FILES else None,
            )
            # Twarda kontrola po zapisie: jeżeli lokal nie jest przypięty do
            # aktualnego właściciela, zwracamy błąd zamiast fałszywego sukcesu.
            saved_ok = Venues.objects.filter(
                venue_id=venue.venue_id,
                owner_id=custom_user.user_id,
                is_active=True,
            ).exists()
            if not saved_ok:
                raise RuntimeError('Venue was saved without the current owner')
    except Exception as exc:
        return error_response(
            'Nie udało się zapisać lokalu i przypisać go do Twojego konta. Spróbuj ponownie albo zrestartuj bazę: docker-compose down -v.',
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            field='venue_save',
        )

    venue = Venues.objects.select_related('city__province', 'owner').get(venue_id=venue.venue_id)
    serializer = VenueSerializer(venue, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_venues(request):
    """Zwraca lokale zalogowanego właściciela bez zgadywania po froncie.

    Wcześniej frontend pobierał publiczną listę lokali i próbował wybrać swoje
    lokale po nazwie użytkownika. To było kruche, bo publiczny serializer ukrywa
    dane właściciela dla obcych użytkowników. Ten endpoint zwraca dokładnie
    lokale zalogowanego właściciela, więc nowo dodana oferta od razu pojawia się
    w zakładce „Rezerwacje” -> „Twoje lokale” i w panelu właściciela.
    """
    try:
        custom_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    if custom_user.role == Users.ROLE_ADMIN:
        venues = Venues.objects.select_related('city__province', 'owner').filter(is_active=True).order_by('-venue_id')
    elif custom_user.role == Users.ROLE_OWNER:
        # Filtrujemy po owner_id oraz awaryjnie po loginie właściciela. To zabezpiecza
        # stare wolumeny, gdzie relacja mogła być zapisana poprawnie w bazie, ale
        # obiekt użytkownika został odtworzony po zmianach ZIP-a.
        venues = Venues.objects.select_related('city__province', 'owner').filter(
            is_active=True,
            owner__username__iexact=request.user.username,
        ).order_by('-venue_id')
    else:
        venues = Venues.objects.none()

    serializer = VenueSerializer(venues, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def get_venue_detail(request, pk):
    try:
        venue = Venues.objects.select_related('owner', 'city__province').get(venue_id=pk, is_active=True)
    except Venues.DoesNotExist:
        return error_response('Taki lokal nie istnieje.', status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = VenueSerializer(venue, context={'request': request})
        return Response(serializer.data)

    if not request.user.is_authenticated:
        return error_response('Musisz się zalogować, aby usunąć lokal.', status.HTTP_401_UNAUTHORIZED)
    try:
        custom_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    is_owner = venue.owner == custom_user
    is_admin = custom_user.role == Users.ROLE_ADMIN
    if not (is_owner or is_admin):
        return error_response('Brak uprawnień – nie jesteś właścicielem tego lokalu ani administratorem.', status.HTTP_403_FORBIDDEN)

    venue.is_active = False
    venue.save(update_fields=['is_active'])
    return Response({'message': 'Lokal ukryty z widoku publicznego.'}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def venue_reviews(request, pk):
    try:
        venue = Venues.objects.get(venue_id=pk, is_active=True)
    except Venues.DoesNotExist:
        return error_response('Taki lokal nie istnieje.', status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        reviews = Reviews.objects.select_related('reviewer', 'venue').filter(venue=venue).order_by('-created_at')
        return Response(ReviewSerializer(reviews, many=True).data)

    if not request.user.is_authenticated:
        return error_response('Musisz się zalogować, aby dodać opinię.', status.HTTP_401_UNAUTHORIZED)

    try:
        reviewer = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    try:
        rating = int(request.data.get('rating'))
    except (ValueError, TypeError):
        return error_response('Ocena musi być liczbą od 1 do 5.', field='rating')

    if rating < 1 or rating > 5:
        return error_response('Ocena musi być w zakresie od 1 do 5.', field='rating')

    comment = (request.data.get('comment') or '').strip()
    if len(comment) > 2000:
        return error_response('Opinia jest za długa. Maksymalnie 2000 znaków.', field='comment')

    review = Reviews.objects.create(venue=venue, reviewer=reviewer, rating=rating, comment=comment)
    return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


# --- BOOKINGS ---

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def booking_list_or_create(request):
    try:
        custom_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        if custom_user.role == Users.ROLE_ADMIN:
            bookings = Bookings.objects.select_related('venue', 'venue__city', 'renter').all().order_by('-booking_id')[:200]
        else:
            bookings = Bookings.objects.select_related('venue', 'venue__city', 'renter').filter(renter=custom_user).order_by('-booking_id')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

    venue_id = request.data.get('venue')
    start_date_str = request.data.get('start_date')
    end_date_str = request.data.get('end_date')
    payment_method = request.data.get('payment_method') or Bookings.PAYMENT_ONLINE

    if payment_method not in PAYMENT_METHODS:
        return error_response('Wybierz poprawną formę płatności: online albo gotówka.', field='payment_method')

    if not venue_id or not start_date_str or not end_date_str:
        return error_response('Wybierz lokal oraz datę rozpoczęcia i zakończenia.', status.HTTP_400_BAD_REQUEST)

    try:
        venue = Venues.objects.get(venue_id=venue_id, is_active=True)
    except (Venues.DoesNotExist, ValueError, TypeError):
        return error_response('Wybrany lokal nie istnieje.', status.HTTP_404_NOT_FOUND)

    start_date = parse_datetime(start_date_str)
    end_date = parse_datetime(end_date_str)

    if not start_date or not end_date:
        return error_response('Daty mają nieprawidłowy format.', status.HTTP_400_BAD_REQUEST)
    if start_date >= end_date:
        return error_response('Data końcowa musi być późniejsza niż data początkowa.', status.HTTP_400_BAD_REQUEST)

    if not booking_within_availability(venue, start_date, end_date):
        return error_response('Ten lokal nie jest udostępniony przez właściciela w wybranym terminie.', status.HTTP_409_CONFLICT)

    delta = end_date.date() - start_date.date()
    days = max(delta.days, 1)

    try:
        with transaction.atomic():
            overlapping_bookings = Bookings.objects.select_for_update().filter(
                venue=venue,
                start_date__date__lt=end_date.date(),
                end_date__date__gt=start_date.date(),
            ).exclude(status=Bookings.STATUS_CANCELLED)

            if overlapping_bookings.exists():
                return error_response('Ten lokal jest już zajęty w wybranym terminie. Wybierz inne daty.', status.HTTP_409_CONFLICT)

            commission_rate = current_commission_rate()
            owner_payout, platform_commission, calculated_total = split_booking_amount(
                days, venue.price_per_day, commission_rate
            )

            booking = Bookings.objects.create(
                renter=custom_user,
                venue=venue,
                start_date=start_date,
                end_date=end_date,
                owner_payout=owner_payout,
                platform_commission=platform_commission,
                commission_rate_applied=commission_rate,
                total_cost=calculated_total,
                payment_method=payment_method,
                payment_status=Bookings.PAYMENT_PENDING,
                status=Bookings.STATUS_PENDING,
            )
    except Exception:
        return error_response('Nie udało się zapisać rezerwacji. Spróbuj ponownie.', status.HTTP_500_INTERNAL_SERVER_ERROR)

    serializer = BookingSerializer(booking)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def booking_detail(request, pk):
    try:
        custom_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    try:
        if custom_user.role == Users.ROLE_ADMIN:
            booking = Bookings.objects.get(booking_id=pk)
        else:
            booking = Bookings.objects.get(booking_id=pk, renter=custom_user)
    except Bookings.DoesNotExist:
        return error_response('Nie znaleziono rezerwacji.', status.HTTP_404_NOT_FOUND)

    if custom_user.role == Users.ROLE_ADMIN and (request.data.get('payment_method') or request.data.get('status') == Bookings.STATUS_PAID):
        return error_response('Administrator widzi rezerwacje w systemie, ale nie może opłacać cudzych rezerwacji ani zmieniać ich formy płatności.', status.HTTP_403_FORBIDDEN)

    changed = []
    new_payment_method = request.data.get('payment_method')
    if new_payment_method:
        if new_payment_method not in PAYMENT_METHODS:
            return error_response('Nieprawidłowa forma płatności.', status.HTTP_400_BAD_REQUEST, field='payment_method')
        if booking.payment_status != Bookings.PAYMENT_PENDING or booking.status in {Bookings.STATUS_PAID, Bookings.STATUS_DONE, Bookings.STATUS_CANCELLED}:
            return error_response('Formę płatności można zmienić tylko wtedy, gdy płatność nadal oczekuje.', status.HTTP_409_CONFLICT)
        booking.payment_method = new_payment_method
        changed.append('payment_method')

    new_status = request.data.get('status')
    if new_status:
        if new_status not in BOOKING_STATUSES:
            return error_response('Nieprawidłowy status rezerwacji.', status.HTTP_400_BAD_REQUEST)
        if new_status == Bookings.STATUS_PAID:
            if booking.status == Bookings.STATUS_CANCELLED:
                return error_response('Nie można opłacić anulowanej rezerwacji.', status.HTTP_409_CONFLICT)
            booking.payment_method = Bookings.PAYMENT_ONLINE
            booking.payment_status = Bookings.PAYMENT_PAID
            booking.status = Bookings.STATUS_PAID
            changed.extend(['payment_method', 'payment_status', 'status'])
        elif new_status == Bookings.STATUS_CANCELLED:
            booking.status = Bookings.STATUS_CANCELLED
            changed.append('status')
        else:
            booking.status = new_status
            changed.append('status')

    if not changed:
        return error_response('Nie podano żadnej zmiany rezerwacji.', status.HTTP_400_BAD_REQUEST)

    booking.save(update_fields=list(set(changed)))
    return Response(BookingSerializer(booking).data)


# --- CONFIG + ADMIN ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_config(request):
    _, admin_error = require_admin(request)
    if admin_error:
        return admin_error
    commission = current_commission_rate()
    return Response({'commission_rate': float(commission)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard(request):
    _, admin_error = require_admin(request)
    if admin_error:
        return admin_error

    users = Users.objects.select_related('province', 'city').all().order_by('user_id')
    venues = Venues.objects.select_related('city__province', 'owner').all().order_by('-venue_id')
    bookings = Bookings.objects.select_related('venue', 'venue__city', 'renter').all().order_by('-booking_id')[:100]

    active_booking_qs = Bookings.objects.exclude(status=Bookings.STATUS_CANCELLED)
    totals = payment_split_stats(active_booking_qs)
    active_bookings = active_booking_qs.count()
    monthly = build_monthly_payment_report(active_booking_qs)

    return Response({
        'stats': {
            'users': users.count(),
            'venues': venues.count(),
            'bookings': active_bookings,
            'gross_revenue': float(totals['gross_revenue']),
            'platform_commission': float(totals['platform_commission']),
            'owner_payout': float(totals['owner_payout']),
            'paid_gross_revenue': float(totals['paid_gross_revenue']),
            'paid_platform_commission': float(totals['paid_platform_commission']),
            'paid_owner_payout': float(totals['paid_owner_payout']),
            'pending_gross_revenue': float(totals['pending_gross_revenue']),
            'pending_platform_commission': float(totals['pending_platform_commission']),
            'pending_owner_payout': float(totals['pending_owner_payout']),
            'revenue': float(totals['gross_revenue']),
            'commission_rate': float(current_commission_rate()),
        },
        'users': UserSerializer(users, many=True).data,
        'venues': VenueSerializer(venues, many=True, context={'request': request}).data,
        'bookings': BookingSerializer(bookings, many=True).data,
        'monthly': monthly,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def owner_dashboard(request):
    try:
        app_user = get_app_user(request.user)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono profilu użytkownika.', status.HTTP_400_BAD_REQUEST)

    if app_user.role not in {Users.ROLE_OWNER, Users.ROLE_ADMIN}:
        return error_response('Panel zarządzania jest dostępny tylko dla właściciela lokali.', status.HTTP_403_FORBIDDEN)

    if app_user.role == Users.ROLE_ADMIN:
        venues = Venues.objects.select_related('city__province', 'owner').all().order_by('-venue_id')
        booking_qs = Bookings.objects.select_related('venue', 'venue__city', 'renter').all()
    else:
        venues = Venues.objects.select_related('city__province', 'owner').filter(owner=app_user, is_active=True).order_by('-venue_id')
        booking_qs = Bookings.objects.select_related('venue', 'venue__city', 'renter').filter(venue__owner=app_user)

    active_booking_qs = booking_qs.exclude(status=Bookings.STATUS_CANCELLED)
    totals = payment_split_stats(active_booking_qs)
    monthly = build_monthly_payment_report(active_booking_qs)

    venue_summary = []
    for venue in venues:
        venue_bookings = active_booking_qs.filter(venue=venue)
        venue_totals = payment_split_stats(venue_bookings)
        venue_summary.append({
            'venue_id': venue.venue_id,
            'name': venue.name,
            'street_address': venue.street_address,
            'city_name': venue.city.name,
            'province_name': venue.city.province.name,
            'capacity': venue.capacity,
            'area_m2': float(venue.area_m2),
            'price_per_day': float(venue.price_per_day),
            'bookings': venue_bookings.count(),
            'gross_revenue': float(venue_totals['gross_revenue']),
            'platform_commission': float(venue_totals['platform_commission']),
            'owner_payout': float(venue_totals['owner_payout']),
            'paid_gross_revenue': float(venue_totals['paid_gross_revenue']),
            'paid_platform_commission': float(venue_totals['paid_platform_commission']),
            'paid_owner_payout': float(venue_totals['paid_owner_payout']),
            'pending_gross_revenue': float(venue_totals['pending_gross_revenue']),
            'pending_platform_commission': float(venue_totals['pending_platform_commission']),
            'pending_owner_payout': float(venue_totals['pending_owner_payout']),
        })

    return Response({
        'stats': {
            'venues': venues.count(),
            'bookings': active_booking_qs.count(),
            'gross_revenue': float(totals['gross_revenue']),
            'platform_commission': float(totals['platform_commission']),
            'owner_payout': float(totals['owner_payout']),
            'paid_gross_revenue': float(totals['paid_gross_revenue']),
            'paid_platform_commission': float(totals['paid_platform_commission']),
            'paid_owner_payout': float(totals['paid_owner_payout']),
            'pending_gross_revenue': float(totals['pending_gross_revenue']),
            'pending_platform_commission': float(totals['pending_platform_commission']),
            'pending_owner_payout': float(totals['pending_owner_payout']),
        },
        'venues': VenueSerializer(venues, many=True, context={'request': request}).data,
        'venue_summary': venue_summary,
        'bookings': BookingSerializer(booking_qs.order_by('-booking_id')[:100], many=True).data,
        'monthly': monthly,
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_update_user(request, pk):
    _, admin_error = require_admin(request)
    if admin_error:
        return admin_error

    try:
        app_user = Users.objects.get(user_id=pk)
    except Users.DoesNotExist:
        return error_response('Nie znaleziono użytkownika.', status.HTTP_404_NOT_FOUND)

    if 'is_active' in request.data:
        app_user.is_active = bool(request.data.get('is_active'))
        User.objects.filter(username=app_user.username).update(is_active=app_user.is_active)

    if 'role' in request.data:
        role = request.data.get('role')
        if role not in {Users.ROLE_RENTER, Users.ROLE_OWNER, Users.ROLE_ADMIN}:
            return error_response('Nieprawidłowa rola użytkownika.', status.HTTP_400_BAD_REQUEST)
        app_user.role = role
        User.objects.filter(username=app_user.username).update(
            is_staff=(role == Users.ROLE_ADMIN),
            is_superuser=(role == Users.ROLE_ADMIN),
        )

    app_user.save()
    return Response(UserSerializer(app_user).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_update_config(request):
    _, admin_error = require_admin(request)
    if admin_error:
        return admin_error

    raw_rate = request.data.get('commission_rate')
    try:
        rate = Decimal(str(raw_rate))
    except (InvalidOperation, TypeError):
        return error_response('Prowizja musi być liczbą.', status.HTTP_400_BAD_REQUEST)

    if rate < 0 or rate > 100:
        return error_response('Prowizja musi być w zakresie od 0 do 100%.', status.HTTP_400_BAD_REQUEST)

    config = SystemConfig.objects.order_by('config_id').first()
    if not config:
        config = SystemConfig.objects.create(commission_rate=rate)
    else:
        config.commission_rate = rate
        config.save()

    return Response({'commission_rate': float(config.commission_rate), 'message': 'Prowizja zapisana.'})
