from django.db import models

class Provinces(models.Model):
    province_id = models.AutoField(primary_key=True, db_column='Province_ID')
    name = models.CharField(max_length=100, unique=True, db_column='Name')

    class Meta:
        db_table = 'Provinces'
        managed = True

    def __str__(self):
        return self.name

class Cities(models.Model):
    city_id = models.AutoField(primary_key=True, db_column='City_ID')
    province = models.ForeignKey(Provinces, on_delete=models.CASCADE, db_column='Province_ID')
    name = models.CharField(max_length=100, db_column='Name')

    class Meta:
        db_table = 'Cities'
        managed = True

    def __str__(self):
        return self.name

# DODAJEMY TĘ KLASĘ - TO JEJ BRAKOWAŁO:
class Users(models.Model):
    user_id = models.AutoField(primary_key=True, db_column='User_ID')
    username = models.CharField(max_length=255, unique=True, db_column='Username')
    email = models.EmailField(unique=True, db_column='Email')
    password_hash = models.CharField(max_length=255, db_column='Password_Hash')
    role = models.CharField(max_length=50, db_column='Role')

    class Meta:
        db_table = 'Users'
        managed = True

    def __str__(self):
        return self.email

class Venues(models.Model):
    venue_id = models.AutoField(primary_key=True, db_column='Venue_ID')
    owner = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='Owner_ID', null=True)
    city = models.ForeignKey(Cities, on_delete=models.CASCADE, db_column='City_ID')
    name = models.CharField(max_length=255, db_column='Name')
    description = models.TextField(null=True, blank=True, db_column='Description')
    capacity = models.IntegerField(null=True, blank=True, db_column='Capacity')
    price_per_day = models.DecimalField(max_digits=19, decimal_places=4, db_column='Price_Per_Day')
    photo = models.ImageField(upload_to='venues_photos/', null=True, blank=True)

    class Meta:
        db_table = 'Venues'
        managed = True

    def __str__(self):
        return self.name

class Bookings(models.Model):
    booking_id = models.AutoField(primary_key=True, db_column='Booking_ID')
    venue = models.ForeignKey(Venues, on_delete=models.CASCADE, db_column='Venue_ID')
    renter = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='Renter_ID', null=True)
    start_date = models.DateTimeField(db_column='Start_Date')
    end_date = models.DateTimeField(db_column='End_Date')
    total_cost = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True, db_column='Total_Price')
    status = models.CharField(max_length=50, default='Pending', db_column='Status')

    class Meta:
        db_table = 'Bookings'
        managed = True