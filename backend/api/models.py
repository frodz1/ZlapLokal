from django.db import models


class Provinces(models.Model):
    province_id = models.AutoField(primary_key=True, db_column='Province_ID')
    name = models.CharField(max_length=100, unique=True, db_column='Name')

    class Meta:
        db_table = 'Provinces'
        managed = True
        verbose_name = 'Województwo'
        verbose_name_plural = 'Województwa'

    def __str__(self):
        return self.name


class Cities(models.Model):
    city_id = models.AutoField(primary_key=True, db_column='City_ID')
    province = models.ForeignKey(Provinces, on_delete=models.CASCADE, db_column='Province_ID')
    name = models.CharField(max_length=100, db_column='Name')

    class Meta:
        db_table = 'Cities'
        managed = True
        unique_together = ('province', 'name')
        verbose_name = 'Miasto'
        verbose_name_plural = 'Miasta'

    def __str__(self):
        return f'{self.name} ({self.province.name})'


class Users(models.Model):
    ROLE_RENTER = 'Role_Renter'
    ROLE_OWNER = 'Role_Owner'
    ROLE_ADMIN = 'Role_Admin'

    ROLE_CHOICES = [
        (ROLE_RENTER, 'Najemca'),
        (ROLE_OWNER, 'Właściciel'),
        (ROLE_ADMIN, 'Administrator'),
    ]

    user_id = models.AutoField(primary_key=True, db_column='User_ID')
    username = models.CharField(max_length=255, unique=True, db_column='Username')
    email = models.EmailField(unique=True, db_column='Email')
    password_hash = models.CharField(max_length=255, blank=True, default='', db_column='Password_Hash')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=ROLE_RENTER, db_column='Role')
    province = models.ForeignKey(Provinces, on_delete=models.SET_NULL, null=True, blank=True, db_column='Province_ID')
    city = models.ForeignKey(Cities, on_delete=models.SET_NULL, null=True, blank=True, db_column='City_ID')
    is_active = models.BooleanField(default=True, db_column='Is_Active')
    registration_date = models.DateTimeField(auto_now_add=True, db_column='Registration_Date')

    class Meta:
        db_table = 'Users'
        managed = True
        verbose_name = 'Użytkownik aplikacji'
        verbose_name_plural = 'Użytkownicy aplikacji'

    def __str__(self):
        return f'{self.username} ({self.email})'


class SystemConfig(models.Model):
    config_id = models.AutoField(primary_key=True, db_column='Config_ID')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, db_column='Commission_Rate')

    class Meta:
        db_table = 'System_Config'
        managed = True
        verbose_name = 'Konfiguracja systemu'
        verbose_name_plural = 'Konfiguracja systemu'

    def __str__(self):
        return f'Prowizja: {self.commission_rate}%'


class Venues(models.Model):
    venue_id = models.AutoField(primary_key=True, db_column='Venue_ID')
    owner = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='Owner_ID', null=True, blank=True)
    city = models.ForeignKey(Cities, on_delete=models.CASCADE, db_column='City_ID')
    name = models.CharField(max_length=255, db_column='Name')
    street_address = models.CharField(max_length=255, default='Adres do uzupełnienia', db_column='Street_Address')
    description = models.TextField(null=True, blank=True, db_column='Description')
    capacity = models.IntegerField(db_column='Capacity')
    area_m2 = models.DecimalField(max_digits=8, decimal_places=2, default=100, db_column='Area_M2')
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, db_column='Price_Per_Day')
    deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='Deposit')
    available_from = models.DateField(null=True, blank=True, db_column='Available_From')
    available_to = models.DateField(null=True, blank=True, db_column='Available_To')
    is_active = models.BooleanField(default=True, db_column='Is_Active')
    photo = models.ImageField(upload_to='venues_photos/', null=True, blank=True, db_column='photo')

    class Meta:
        db_table = 'Venues'
        managed = True
        verbose_name = 'Lokal'
        verbose_name_plural = 'Lokale'

    def __str__(self):
        return self.name


class Bookings(models.Model):
    STATUS_PENDING = 'OCZEKUJACA'
    STATUS_CONFIRMED = 'POTWIERDZONA'
    STATUS_PAID = 'OPLACONA'
    STATUS_DONE = 'ZREALIZOWANA'
    STATUS_CANCELLED = 'ANULOWANA'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Oczekująca'),
        (STATUS_CONFIRMED, 'Potwierdzona'),
        (STATUS_PAID, 'Opłacona'),
        (STATUS_DONE, 'Zrealizowana'),
        (STATUS_CANCELLED, 'Anulowana'),
    ]

    PAYMENT_ONLINE = 'ONLINE'
    PAYMENT_CASH = 'GOTOWKA'

    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_ONLINE, 'Płatność online'),
        (PAYMENT_CASH, 'Gotówka'),
    ]

    PAYMENT_PENDING = 'OCZEKUJACA'
    PAYMENT_PAID = 'OPLACONA'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Oczekująca'),
        (PAYMENT_PAID, 'Opłacona'),
    ]

    booking_id = models.AutoField(primary_key=True, db_column='Booking_ID')
    venue = models.ForeignKey(Venues, on_delete=models.CASCADE, db_column='Venue_ID')
    renter = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='Renter_ID', null=True, blank=True)
    start_date = models.DateTimeField(db_column='Start_Date')
    end_date = models.DateTimeField(db_column='End_Date')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, db_column='Total_Price')
    owner_payout = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, db_column='Owner_Payout')
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, db_column='Platform_Commission')
    commission_rate_applied = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, db_column='Commission_Rate_Applied')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_ONLINE, db_column='Payment_Method')
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING, db_column='Payment_Status')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_PENDING, db_column='Status')

    class Meta:
        db_table = 'Bookings'
        managed = True
        verbose_name = 'Rezerwacja'
        verbose_name_plural = 'Rezerwacje'

    def __str__(self):
        return f'{self.venue.name} {self.start_date:%Y-%m-%d} - {self.end_date:%Y-%m-%d}'


class Reviews(models.Model):
    review_id = models.AutoField(primary_key=True, db_column='Review_ID')
    venue = models.ForeignKey(Venues, on_delete=models.CASCADE, related_name='reviews', db_column='Venue_ID')
    reviewer = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='reviews', db_column='Reviewer_ID')
    rating = models.IntegerField(db_column='Rating')
    comment = models.TextField(blank=True, default='', db_column='Comment')
    created_at = models.DateTimeField(auto_now_add=True, db_column='Created_At')

    class Meta:
        db_table = 'Reviews'
        managed = True
        verbose_name = 'Opinia'
        verbose_name_plural = 'Opinie'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.venue.name}: {self.rating}/5'
