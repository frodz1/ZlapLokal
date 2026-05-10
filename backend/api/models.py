from django.db import models

class Users(models.Model):
    user_id = models.AutoField(db_column='User_ID', primary_key=True)
    email = models.CharField(db_column='Email', unique=True, max_length=255)
    password_hash = models.CharField(db_column='Password_Hash', max_length=255)
    role = models.CharField(db_column='Role', max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(db_column='Created_At', blank=True, null=True)
    is_active = models.BooleanField(db_column='Is_Active', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Users'

class Provinces(models.Model):
    province_id = models.AutoField(db_column='Province_ID', primary_key=True)
    name = models.CharField(db_column='Name', unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'Provinces'

class Cities(models.Model):
    city_id = models.AutoField(db_column='City_ID', primary_key=True)
    province = models.ForeignKey(Provinces, models.DO_NOTHING, db_column='Province_ID', blank=True, null=True)
    name = models.CharField(db_column='Name', max_length=100)

    class Meta:
        managed = False
        db_table = 'Cities'

class Categories(models.Model):
    category_id = models.AutoField(db_column='Category_ID', primary_key=True)
    category_name = models.CharField(db_column='Category_Name', unique=True, max_length=100)

    class Meta:
        managed = False
        db_table = 'Categories'

class Venues(models.Model):
    venue_id = models.AutoField(db_column='Venue_ID', primary_key=True)
    owner = models.ForeignKey(Users, models.DO_NOTHING, db_column='Owner_ID', blank=True, null=True)
    city = models.ForeignKey(Cities, models.DO_NOTHING, db_column='City_ID', blank=True, null=True)
    name = models.CharField(db_column='Name', max_length=255)
    description = models.TextField(db_column='Description', blank=True, null=True)
    capacity = models.IntegerField(db_column='Capacity', blank=True, null=True)
    price_per_day = models.DecimalField(db_column='Price_Per_Day', max_digits=19, decimal_places=4)
    deposit = models.DecimalField(db_column='Deposit', max_digits=19, decimal_places=4, blank=True, null=True)
    is_deleted = models.BooleanField(db_column='Is_Deleted', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Venues'

class Bookings(models.Model):
    booking_id = models.AutoField(db_column='Booking_ID', primary_key=True)
    venue = models.ForeignKey(Venues, models.DO_NOTHING, db_column='Venue_ID', blank=True, null=True)
    renter = models.ForeignKey(Users, models.DO_NOTHING, db_column='Renter_ID', blank=True, null=True)
    start_date = models.DateTimeField(db_column='Start_Date')
    end_date = models.DateTimeField(db_column='End_Date')
    total_cost = models.DecimalField(db_column='Total_Cost', max_digits=19, decimal_places=4, blank=True, null=True)
    system_commission = models.DecimalField(db_column='System_Commission', max_digits=19, decimal_places=4, blank=True, null=True)
    status = models.CharField(db_column='Status', max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Bookings'

class VenueCategory(models.Model):
    id = models.AutoField(primary_key=True)
    venue = models.ForeignKey(Venues, models.DO_NOTHING, db_column='Venue_ID')
    category = models.ForeignKey(Categories, models.DO_NOTHING, db_column='Category_ID')

    class Meta:
        managed = False
        db_table = 'Venue_Category'
        unique_together = (('venue', 'category'),)

class SystemConfig(models.Model):
    config_id = models.AutoField(db_column='Config_ID', primary_key=True)
    commission_rate = models.DecimalField(db_column='Commission_Rate', max_digits=5, decimal_places=2)
    updated_at = models.DateTimeField(db_column='Updated_At', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'System_Config'