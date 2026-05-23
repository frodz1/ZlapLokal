USE master;
GO

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'ZlapLokalDB')
BEGIN
    CREATE DATABASE ZlapLokalDB;
END
GO

USE ZlapLokalDB;
GO

-- =========================================================
--  TWORZENIE TABEL ZGODNIE Z PROJEKTEM
-- =========================================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[System_Config]') AND type in (N'U'))
CREATE TABLE System_Config (
    Config_ID INT PRIMARY KEY IDENTITY(1,1),
    Commission_Rate DECIMAL(5,2) NOT NULL CONSTRAINT CK_System_Config_Commission CHECK (Commission_Rate >= 0 AND Commission_Rate <= 100)
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Provinces]') AND type in (N'U'))
CREATE TABLE Provinces (
    Province_ID INT PRIMARY KEY IDENTITY(1,1),
    Name NVARCHAR(100) NOT NULL UNIQUE
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Cities]') AND type in (N'U'))
CREATE TABLE Cities (
    City_ID INT PRIMARY KEY IDENTITY(1,1),
    Province_ID INT NOT NULL FOREIGN KEY REFERENCES Provinces(Province_ID),
    Name NVARCHAR(100) NOT NULL,
    CONSTRAINT UQ_Cities_Province_Name UNIQUE (Province_ID, Name)
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Categories]') AND type in (N'U'))
CREATE TABLE Categories (
    Category_ID INT PRIMARY KEY IDENTITY(1,1),
    Category_Name NVARCHAR(100) NOT NULL UNIQUE
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Users]') AND type in (N'U'))
CREATE TABLE Users (
    User_ID INT PRIMARY KEY IDENTITY(1,1),
    Username NVARCHAR(255) NOT NULL UNIQUE,
    Email NVARCHAR(255) NOT NULL UNIQUE,
    Password_Hash NVARCHAR(255) NULL,
    Role NVARCHAR(50) NOT NULL CONSTRAINT CK_Users_Role CHECK (Role IN ('Role_Renter', 'Role_Owner', 'Role_Admin')),
    Province_ID INT NULL FOREIGN KEY REFERENCES Provinces(Province_ID),
    City_ID INT NULL FOREIGN KEY REFERENCES Cities(City_ID),
    Is_Active BIT NOT NULL CONSTRAINT DF_Users_Is_Active DEFAULT 1,
    Registration_Date DATETIME2 NOT NULL CONSTRAINT DF_Users_Registration_Date DEFAULT SYSDATETIME()
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Venues]') AND type in (N'U'))
CREATE TABLE Venues (
    Venue_ID INT PRIMARY KEY IDENTITY(1,1),
    Owner_ID INT NULL FOREIGN KEY REFERENCES Users(User_ID),
    City_ID INT NOT NULL FOREIGN KEY REFERENCES Cities(City_ID),
    Name NVARCHAR(255) NOT NULL,
    Street_Address NVARCHAR(255) NOT NULL CONSTRAINT DF_Venues_Street_Address DEFAULT N'Adres do uzupełnienia',
    Description NVARCHAR(MAX) NULL,
    Capacity INT NOT NULL CONSTRAINT CK_Venues_Capacity CHECK (Capacity > 0),
    Area_M2 DECIMAL(8,2) NOT NULL CONSTRAINT DF_Venues_Area DEFAULT 100 CONSTRAINT CK_Venues_Area CHECK (Area_M2 > 0),
    Price_Per_Day DECIMAL(10,2) NOT NULL CONSTRAINT CK_Venues_Price CHECK (Price_Per_Day > 0),
    Deposit DECIMAL(10,2) NOT NULL CONSTRAINT DF_Venues_Deposit DEFAULT 0 CONSTRAINT CK_Venues_Deposit CHECK (Deposit >= 0),
    Available_From DATE NULL,
    Available_To DATE NULL,
    Is_Active BIT NOT NULL CONSTRAINT DF_Venues_Is_Active DEFAULT 1,
    photo NVARCHAR(255) NULL,
    CONSTRAINT CK_Venues_Availability CHECK (Available_From IS NULL OR Available_To IS NULL OR Available_From <= Available_To)
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Venue_Category]') AND type in (N'U'))
CREATE TABLE Venue_Category (
    Venue_ID INT NOT NULL FOREIGN KEY REFERENCES Venues(Venue_ID),
    Category_ID INT NOT NULL FOREIGN KEY REFERENCES Categories(Category_ID),
    PRIMARY KEY (Venue_ID, Category_ID)
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Bookings]') AND type in (N'U'))
CREATE TABLE Bookings (
    Booking_ID INT PRIMARY KEY IDENTITY(1,1),
    Venue_ID INT NOT NULL FOREIGN KEY REFERENCES Venues(Venue_ID),
    Renter_ID INT NULL FOREIGN KEY REFERENCES Users(User_ID),
    Start_Date DATETIME2 NOT NULL,
    End_Date DATETIME2 NOT NULL,
    Total_Price DECIMAL(10,2) NULL,
    Owner_Payout DECIMAL(10,2) NULL,
    Platform_Commission DECIMAL(10,2) NULL,
    Commission_Rate_Applied DECIMAL(5,2) NULL,
    Payment_Method NVARCHAR(20) NOT NULL CONSTRAINT DF_Bookings_Payment_Method DEFAULT 'ONLINE',
    Payment_Status NVARCHAR(50) NOT NULL CONSTRAINT DF_Bookings_Payment_Status DEFAULT 'OCZEKUJACA',
    Status NVARCHAR(50) NOT NULL CONSTRAINT DF_Bookings_Status DEFAULT 'OCZEKUJACA',
    CONSTRAINT CK_Bookings_Date CHECK (Start_Date < End_Date),
    CONSTRAINT CK_Bookings_Payment_Method CHECK (Payment_Method IN ('ONLINE', 'GOTOWKA')),
    CONSTRAINT CK_Bookings_Payment_Status CHECK (Payment_Status IN ('OCZEKUJACA', 'OPLACONA')),
    CONSTRAINT CK_Bookings_Status CHECK (Status IN ('OCZEKUJACA', 'POTWIERDZONA', 'OPLACONA', 'ZREALIZOWANA', 'ANULOWANA'))
);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Reviews]') AND type in (N'U'))
CREATE TABLE Reviews (
    Review_ID INT PRIMARY KEY IDENTITY(1,1),
    Venue_ID INT NOT NULL FOREIGN KEY REFERENCES Venues(Venue_ID),
    Reviewer_ID INT NOT NULL FOREIGN KEY REFERENCES Users(User_ID),
    Rating INT NOT NULL CONSTRAINT CK_Reviews_Rating CHECK (Rating BETWEEN 1 AND 5),
    Comment NVARCHAR(MAX) NULL,
    Created_At DATETIME2 NOT NULL CONSTRAINT DF_Reviews_Created DEFAULT SYSDATETIME()
);
GO

-- =========================================================
--  MIGRACJE DLA STARYCH WOLUMENÓW, GDY TABELA JUŻ ISTNIAŁA
-- =========================================================
IF COL_LENGTH('dbo.Users', 'Province_ID') IS NULL ALTER TABLE Users ADD Province_ID INT NULL FOREIGN KEY REFERENCES Provinces(Province_ID);
IF COL_LENGTH('dbo.Users', 'City_ID') IS NULL ALTER TABLE Users ADD City_ID INT NULL FOREIGN KEY REFERENCES Cities(City_ID);
IF COL_LENGTH('dbo.Users', 'Is_Active') IS NULL ALTER TABLE Users ADD Is_Active BIT NOT NULL CONSTRAINT DF_Users_Is_Active_2 DEFAULT 1;
IF COL_LENGTH('dbo.Users', 'Registration_Date') IS NULL ALTER TABLE Users ADD Registration_Date DATETIME2 NOT NULL CONSTRAINT DF_Users_Registration_Date_2 DEFAULT SYSDATETIME();
IF COL_LENGTH('dbo.Venues', 'Street_Address') IS NULL ALTER TABLE Venues ADD Street_Address NVARCHAR(255) NOT NULL CONSTRAINT DF_Venues_Street_Address_2 DEFAULT N'Adres do uzupełnienia';
IF COL_LENGTH('dbo.Venues', 'Area_M2') IS NULL ALTER TABLE Venues ADD Area_M2 DECIMAL(8,2) NOT NULL CONSTRAINT DF_Venues_Area_2 DEFAULT 100;
IF COL_LENGTH('dbo.Venues', 'Deposit') IS NULL ALTER TABLE Venues ADD Deposit DECIMAL(10,2) NOT NULL CONSTRAINT DF_Venues_Deposit_2 DEFAULT 0;
IF COL_LENGTH('dbo.Venues', 'Available_From') IS NULL ALTER TABLE Venues ADD Available_From DATE NULL;
IF COL_LENGTH('dbo.Venues', 'Available_To') IS NULL ALTER TABLE Venues ADD Available_To DATE NULL;
IF COL_LENGTH('dbo.Venues', 'Is_Active') IS NULL ALTER TABLE Venues ADD Is_Active BIT NOT NULL CONSTRAINT DF_Venues_Is_Active_2 DEFAULT 1;
IF COL_LENGTH('dbo.Bookings', 'Owner_Payout') IS NULL ALTER TABLE Bookings ADD Owner_Payout DECIMAL(10,2) NULL;
IF COL_LENGTH('dbo.Bookings', 'Platform_Commission') IS NULL ALTER TABLE Bookings ADD Platform_Commission DECIMAL(10,2) NULL;
IF COL_LENGTH('dbo.Bookings', 'Commission_Rate_Applied') IS NULL ALTER TABLE Bookings ADD Commission_Rate_Applied DECIMAL(5,2) NULL;
IF COL_LENGTH('dbo.Bookings', 'Payment_Method') IS NULL ALTER TABLE Bookings ADD Payment_Method NVARCHAR(20) NOT NULL CONSTRAINT DF_Bookings_Payment_Method_2 DEFAULT 'ONLINE';
IF COL_LENGTH('dbo.Bookings', 'Payment_Status') IS NULL ALTER TABLE Bookings ADD Payment_Status NVARCHAR(50) NOT NULL CONSTRAINT DF_Bookings_Payment_Status_2 DEFAULT 'OCZEKUJACA';

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Reviews]') AND type in (N'U'))
CREATE TABLE Reviews (
    Review_ID INT PRIMARY KEY IDENTITY(1,1),
    Venue_ID INT NOT NULL FOREIGN KEY REFERENCES Venues(Venue_ID),
    Reviewer_ID INT NOT NULL FOREIGN KEY REFERENCES Users(User_ID),
    Rating INT NOT NULL CONSTRAINT CK_Reviews_Rating_2 CHECK (Rating BETWEEN 1 AND 5),
    Comment NVARCHAR(MAX) NULL,
    Created_At DATETIME2 NOT NULL CONSTRAINT DF_Reviews_Created_2 DEFAULT SYSDATETIME()
);
GO


-- Uzupełnienie adresów i powierzchni w starych wolumenach.
-- Dzięki temu lokale dodane w poprzedniej wersji projektu nie wiszą jako „Adres do uzupełnienia”.
UPDATE v
   SET Street_Address = CASE c.Name
        WHEN N'Wrocław' THEN N'ul. Kazimierza Wielkiego ' + CAST(10 + v.Venue_ID AS NVARCHAR(10)) + N', Wrocław'
        WHEN N'Warszawa' THEN N'ul. Marszałkowska ' + CAST(20 + v.Venue_ID AS NVARCHAR(10)) + N', Warszawa'
        WHEN N'Kraków' THEN N'ul. Floriańska ' + CAST(30 + v.Venue_ID AS NVARCHAR(10)) + N', Kraków'
        WHEN N'Gdańsk' THEN N'ul. Długa ' + CAST(40 + v.Venue_ID AS NVARCHAR(10)) + N', Gdańsk'
        WHEN N'Sopot' THEN N'ul. Bohaterów Monte Cassino ' + CAST(50 + v.Venue_ID AS NVARCHAR(10)) + N', Sopot'
        WHEN N'Poznań' THEN N'ul. Święty Marcin ' + CAST(60 + v.Venue_ID AS NVARCHAR(10)) + N', Poznań'
        ELSE N'ul. Główna ' + CAST(100 + v.Venue_ID AS NVARCHAR(10))
       END
FROM dbo.Venues v
JOIN dbo.Cities c ON c.City_ID = v.City_ID
WHERE v.Street_Address IS NULL
   OR LTRIM(RTRIM(v.Street_Address)) = N''
   OR v.Street_Address = N'Adres do uzupełnienia';

UPDATE dbo.Venues
   SET Area_M2 = CASE
        WHEN Capacity >= 250 THEN 900.00
        WHEN Capacity >= 100 THEN 420.00
        WHEN Capacity >= 50 THEN 180.00
        ELSE 120.00
       END
WHERE Area_M2 IS NULL OR Area_M2 <= 0;

UPDATE dbo.Venues SET Available_From = '2026-04-01' WHERE Available_From IS NULL;
UPDATE dbo.Venues SET Available_To = '2026-12-31' WHERE Available_To IS NULL;
GO

-- Poprawka starego CHECK statusów, żeby był zgodny z projektem bazy.
DECLARE @DropStatusConstraint NVARCHAR(MAX) = N'';
SELECT @DropStatusConstraint = @DropStatusConstraint + N'ALTER TABLE dbo.Bookings DROP CONSTRAINT [' + name + N'];'
FROM sys.check_constraints
WHERE parent_object_id = OBJECT_ID(N'dbo.Bookings')
  AND name LIKE N'CK_Bookings_Status%';
IF @DropStatusConstraint <> N'' EXEC sp_executesql @DropStatusConstraint;

UPDATE dbo.Bookings SET Status = 'OCZEKUJACA' WHERE Status IN (N'ZAREZERWOWANO', N'REZERWACJA');
UPDATE dbo.Bookings SET Status = 'OPLACONA' WHERE Status IN (N'OPLACONO', N'OPŁACONO');
UPDATE dbo.Bookings SET Status = 'ANULOWANA' WHERE Status IN (N'ANULOWANO');
UPDATE dbo.Bookings
   SET Status = 'OCZEKUJACA'
 WHERE Status NOT IN ('OCZEKUJACA', 'POTWIERDZONA', 'OPLACONA', 'ZREALIZOWANA', 'ANULOWANA');

UPDATE dbo.Bookings SET Payment_Method = 'ONLINE' WHERE Payment_Method NOT IN ('ONLINE', 'GOTOWKA') OR Payment_Method IS NULL;
UPDATE dbo.Bookings SET Payment_Status = CASE WHEN Status = 'OPLACONA' THEN 'OPLACONA' ELSE 'OCZEKUJACA' END WHERE Payment_Status NOT IN ('OCZEKUJACA', 'OPLACONA') OR Payment_Status IS NULL;

ALTER TABLE dbo.Bookings WITH CHECK ADD CONSTRAINT CK_Bookings_Status CHECK (Status IN ('OCZEKUJACA', 'POTWIERDZONA', 'OPLACONA', 'ZREALIZOWANA', 'ANULOWANA'));
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Bookings_Payment_Method') ALTER TABLE dbo.Bookings WITH CHECK ADD CONSTRAINT CK_Bookings_Payment_Method CHECK (Payment_Method IN ('ONLINE', 'GOTOWKA'));
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Bookings_Payment_Status') ALTER TABLE dbo.Bookings WITH CHECK ADD CONSTRAINT CK_Bookings_Payment_Status CHECK (Payment_Status IN ('OCZEKUJACA', 'OPLACONA'));
GO

DECLARE @Rate DECIMAL(5,2);
SELECT TOP 1 @Rate = Commission_Rate FROM System_Config ORDER BY Config_ID;
IF @Rate IS NULL SET @Rate = 12.50;

UPDATE Bookings
SET
    Commission_Rate_Applied = ISNULL(Commission_Rate_Applied, @Rate),
    Owner_Payout = ISNULL(Owner_Payout, ROUND(Total_Price / (1 + (@Rate / 100.0)), 2)),
    Platform_Commission = ISNULL(Platform_Commission, ROUND(Total_Price - ROUND(Total_Price / (1 + (@Rate / 100.0)), 2), 2))
WHERE Total_Price IS NOT NULL
  AND (Owner_Payout IS NULL OR Platform_Commission IS NULL OR Commission_Rate_Applied IS NULL);
GO

-- =========================================================
--  TRIGGERY ZGODNE Z PROJEKTEM BAZY
-- =========================================================
CREATE OR ALTER TRIGGER dbo.TRG_CheckOverbooking
ON dbo.Bookings
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Bookings b
          ON b.Venue_ID = i.Venue_ID
         AND b.Booking_ID <> i.Booking_ID
         AND b.Status <> 'ANULOWANA'
         AND i.Status <> 'ANULOWANA'
         AND b.Start_Date < i.End_Date
         AND b.End_Date > i.Start_Date
    )
    OR EXISTS (
        SELECT 1
        FROM inserted i1
        JOIN inserted i2
          ON i1.Booking_ID <> i2.Booking_ID
         AND i1.Venue_ID = i2.Venue_ID
         AND i1.Status <> 'ANULOWANA'
         AND i2.Status <> 'ANULOWANA'
         AND i1.Start_Date < i2.End_Date
         AND i1.End_Date > i2.Start_Date
    )
    BEGIN
        RAISERROR(N'Ten lokal jest już zajęty w wybranym terminie.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END
END;
GO

CREATE OR ALTER TRIGGER dbo.TRG_CheckVenueAvailability
ON dbo.Bookings
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Venues v ON v.Venue_ID = i.Venue_ID
        WHERE i.Status <> 'ANULOWANA'
          AND (
              (v.Available_From IS NOT NULL AND CAST(i.Start_Date AS DATE) < v.Available_From)
              OR (v.Available_To IS NOT NULL AND CAST(i.End_Date AS DATE) > v.Available_To)
          )
    )
    BEGIN
        RAISERROR(N'Ten lokal nie jest udostępniony przez właściciela w wybranym terminie.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END
END;
GO

CREATE OR ALTER TRIGGER dbo.TRG_CalculateCost
ON dbo.Bookings
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF TRIGGER_NESTLEVEL(OBJECT_ID(N'dbo.TRG_CalculateCost')) > 1 RETURN;

    IF NOT (
        UPDATE(Venue_ID) OR UPDATE(Start_Date) OR UPDATE(End_Date)
        OR UPDATE(Total_Price) OR UPDATE(Owner_Payout)
        OR UPDATE(Platform_Commission) OR UPDATE(Commission_Rate_Applied)
    ) RETURN;

    UPDATE b
       SET Commission_Rate_Applied = r.Rate_Applied,
           Owner_Payout = ROUND(d.Days_Count * v.Price_Per_Day, 2),
           Platform_Commission = ROUND(ROUND(d.Days_Count * v.Price_Per_Day, 2) * r.Rate_Applied / 100.0, 2),
           Total_Price = ROUND(
               ROUND(d.Days_Count * v.Price_Per_Day, 2)
               + ROUND(ROUND(d.Days_Count * v.Price_Per_Day, 2) * r.Rate_Applied / 100.0, 2),
               2
           )
    FROM dbo.Bookings b
    JOIN inserted i ON i.Booking_ID = b.Booking_ID
    JOIN dbo.Venues v ON v.Venue_ID = i.Venue_ID
    OUTER APPLY (SELECT TOP 1 Commission_Rate FROM dbo.System_Config ORDER BY Config_ID) cfg
    CROSS APPLY (
        SELECT CASE WHEN DATEDIFF(DAY, i.Start_Date, i.End_Date) < 1 THEN 1 ELSE DATEDIFF(DAY, i.Start_Date, i.End_Date) END AS Days_Count
    ) d
    CROSS APPLY (
        SELECT COALESCE(i.Commission_Rate_Applied, cfg.Commission_Rate, CAST(12.50 AS DECIMAL(5,2))) AS Rate_Applied
    ) r
    WHERE i.Status <> 'ANULOWANA';
END;
GO

-- Procedura uruchamiana cyklicznie jako odpowiednik Job_SoftCleanReservations.
CREATE OR ALTER PROCEDURE dbo.Job_SoftCleanReservations
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE dbo.Bookings
       SET Status = 'ANULOWANA'
     WHERE Status = 'OCZEKUJACA'
       AND Start_Date < DATEADD(DAY, -1, SYSDATETIME());
END;
GO

-- =========================================================
--  ROLE I UPRAWNIENIA BAZODANOWE
-- =========================================================
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'Role_Renter' AND type = 'R') CREATE ROLE Role_Renter;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'Role_Owner' AND type = 'R') CREATE ROLE Role_Owner;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'Role_Admin' AND type = 'R') CREATE ROLE Role_Admin;
GO

GRANT SELECT ON dbo.Provinces TO Role_Renter;
GRANT SELECT ON dbo.Cities TO Role_Renter;
GRANT SELECT ON dbo.Categories TO Role_Renter;
GRANT SELECT ON dbo.Venue_Category TO Role_Renter;
GRANT SELECT ON dbo.Venues TO Role_Renter;
GRANT INSERT, UPDATE ON dbo.Bookings TO Role_Renter;
DENY DELETE ON SCHEMA::dbo TO Role_Renter;

GRANT SELECT ON SCHEMA::dbo TO Role_Owner;
GRANT INSERT, UPDATE ON dbo.Venues TO Role_Owner;
GRANT INSERT, UPDATE ON dbo.Bookings TO Role_Owner;
DENY DELETE ON SCHEMA::dbo TO Role_Owner;

GRANT CONTROL ON DATABASE::ZlapLokalDB TO Role_Admin;
GO

-- =========================================================
--  INDEKSY POD FILTRY I PANELE
-- =========================================================
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Cities_Province' AND object_id = OBJECT_ID('Cities')) CREATE INDEX IX_Cities_Province ON Cities(Province_ID);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Venues_City' AND object_id = OBJECT_ID('Venues')) CREATE INDEX IX_Venues_City ON Venues(City_ID);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Venues_Price' AND object_id = OBJECT_ID('Venues')) CREATE INDEX IX_Venues_Price ON Venues(Price_Per_Day);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Venues_Active' AND object_id = OBJECT_ID('Venues')) CREATE INDEX IX_Venues_Active ON Venues(Is_Active);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Bookings_Venue_Dates' AND object_id = OBJECT_ID('Bookings')) CREATE INDEX IX_Bookings_Venue_Dates ON Bookings(Venue_ID, Start_Date, End_Date);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_Reviews_Venue' AND object_id = OBJECT_ID('Reviews')) CREATE INDEX IX_Reviews_Venue ON Reviews(Venue_ID, Created_At DESC);
GO

-- =========================================================
--  DANE TESTOWE
-- =========================================================
IF NOT EXISTS (SELECT 1 FROM System_Config) INSERT INTO System_Config (Commission_Rate) VALUES (12.50);

IF NOT EXISTS (SELECT 1 FROM Provinces) INSERT INTO Provinces (Name) VALUES
(N'Dolnośląskie'), (N'Mazowieckie'), (N'Małopolskie'), (N'Pomorskie'), (N'Wielkopolskie');

IF NOT EXISTS (SELECT 1 FROM Cities) INSERT INTO Cities (Province_ID, Name) VALUES
(1, N'Wrocław'), (2, N'Warszawa'), (3, N'Kraków'), (4, N'Gdańsk'), (4, N'Sopot'), (5, N'Poznań');

IF NOT EXISTS (SELECT 1 FROM Categories) INSERT INTO Categories (Category_Name) VALUES
(N'Sala bankietowa'), (N'Loft industrialny'), (N'Klub nocny'), (N'Plener i ogród'), (N'Willa z basenem');

IF NOT EXISTS (SELECT 1 FROM Users) INSERT INTO Users (Username, Email, Password_Hash, Role, Province_ID, City_ID, Is_Active) VALUES
(N'admin', N'admin@zlaplokal.pl', N'HASHED_IN_DJANGO_AUTH_USER', N'Role_Admin', 1, 1, 1),
(N'event_master', N'kontakt@event-space.pl', N'HASHED_IN_DJANGO_AUTH_USER', N'Role_Owner', 1, 1, 1),
(N'janusz_biznesu', N'janusz.wlasciciel@gmail.com', N'HASHED_IN_DJANGO_AUTH_USER', N'Role_Owner', 2, 2, 1),
(N'tomek_impreza', N'tomasz.imprezowicz@wp.pl', N'HASHED_IN_DJANGO_AUTH_USER', N'Role_Renter', 3, 3, 1),
(N'kasia_studentka', N'kasia.studentka@stud.pwr.edu.pl', N'HASHED_IN_DJANGO_AUTH_USER', N'Role_Renter', 4, 4, 1);

IF NOT EXISTS (SELECT 1 FROM Venues) INSERT INTO Venues (Owner_ID, City_ID, Name, Street_Address, Description, Capacity, Area_M2, Price_Per_Day, Deposit, Available_From, Available_To, Is_Active, photo) VALUES 
(2, 1, N'Neonowy Loft Nad Odrą', N'ul. Księcia Witolda 48, Wrocław', N'Surowe, ceglane wnętrze idealne na imprezy firmowe i urodziny.', 50, 180.00, 1200.00, 500.00, '2026-04-01', '2026-12-31', 1, N'venues_photos/neonowy_loft.png'),
(3, 2, N'Willa Konstancin', N'ul. Warszawska 21, Konstancin-Jeziorna', N'Ekskluzywna willa z basenem i ogrodem.', 120, 420.00, 3500.00, 2000.00, '2026-04-15', '2026-10-31', 1, N'venues_photos/willa_konstancin.png'),
(2, 4, N'Hala Stocznia', N'ul. Elektryków 2, Gdańsk', N'Ogromna przestrzeń stoczniowa na duże wydarzenia.', 300, 900.00, 4500.00, 3000.00, '2026-05-01', '2026-12-15', 1, N'venues_photos/hala_stocznia.png'),
(3, 3, N'Ogród z Alpakami', N'ul. Podgórska 14, Kraków', N'Cicha przestrzeń plenerowa z alpakami.', 30, 250.00, 800.00, 200.00, '2026-04-01', '2026-09-30', 1, N'venues_photos/ogrod_z_alpakami.png');

IF NOT EXISTS (SELECT 1 FROM Venue_Category) INSERT INTO Venue_Category (Venue_ID, Category_ID) VALUES
(1, 2), (1, 3), (2, 5), (3, 2), (3, 3), (4, 4);

IF NOT EXISTS (SELECT 1 FROM Bookings) INSERT INTO Bookings (Venue_ID, Renter_ID, Start_Date, End_Date, Total_Price, Owner_Payout, Platform_Commission, Commission_Rate_Applied, Payment_Method, Payment_Status, Status) VALUES 
(1, 4, '2026-05-01 16:00:00', '2026-05-03 10:00:00', 2700.00, 2400.00, 300.00, 12.50, 'ONLINE', 'OPLACONA', 'OPLACONA'),
(3, 5, '2026-05-15 14:00:00', '2026-05-17 12:00:00', 10125.00, 9000.00, 1125.00, 12.50, 'GOTOWKA', 'OCZEKUJACA', 'OCZEKUJACA');

IF NOT EXISTS (SELECT 1 FROM Reviews) INSERT INTO Reviews (Venue_ID, Reviewer_ID, Rating, Comment, Created_At) VALUES
(1, 4, 5, N'Bardzo klimatyczne miejsce, świetne nagłośnienie i kontakt z właścicielem.', '2026-05-04 10:00:00'),
(1, 5, 4, N'Duży plus za lokalizację. Przy większej imprezie przydałaby się dodatkowa szatnia.', '2026-05-05 12:00:00'),
(2, 4, 5, N'Elegancka willa, idealna na rodzinne przyjęcie.', '2026-05-06 09:00:00'),
(3, 5, 4, N'Bardzo duża przestrzeń, dobra na większe wydarzenia.', '2026-05-07 11:30:00'),
(4, 4, 5, N'Ogród robi świetne wrażenie, a alpaki to hit imprezy.', '2026-05-08 15:00:00');
GO
