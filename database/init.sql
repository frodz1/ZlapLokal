USE ZlapLokalDB;
GO

-- --- TWORZENIE TABEL (Tylko jeśli nie istnieją) ---

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[System_Config]') AND type in (N'U'))
CREATE TABLE System_Config (Config_ID INT PRIMARY KEY IDENTITY(1,1), Commission_Rate DECIMAL(5,2));

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Provinces]') AND type in (N'U'))
CREATE TABLE Provinces (Province_ID INT PRIMARY KEY IDENTITY(1,1), Name NVARCHAR(100) UNIQUE);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Cities]') AND type in (N'U'))
CREATE TABLE Cities (City_ID INT PRIMARY KEY IDENTITY(1,1), Province_ID INT FOREIGN KEY REFERENCES Provinces(Province_ID), Name NVARCHAR(100));

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Categories]') AND type in (N'U'))
CREATE TABLE Categories (Category_ID INT PRIMARY KEY IDENTITY(1,1), Category_Name NVARCHAR(100) UNIQUE);

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Users]') AND type in (N'U'))
CREATE TABLE Users (User_ID INT PRIMARY KEY IDENTITY(1,1), Email NVARCHAR(255) UNIQUE, Password_Hash NVARCHAR(255), Role NVARCHAR(50));

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Venues]') AND type in (N'U'))
CREATE TABLE Venues (Venue_ID INT PRIMARY KEY IDENTITY(1,1), Owner_ID INT FOREIGN KEY REFERENCES Users(User_ID), City_ID INT FOREIGN KEY REFERENCES Cities(City_ID), Name NVARCHAR(255), Description NVARCHAR(MAX), Capacity INT, Price_Per_Day DECIMAL(10,2), Deposit DECIMAL(10,2), photo NVARCHAR(255));

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Venue_Category]') AND type in (N'U'))
CREATE TABLE Venue_Category (Venue_ID INT FOREIGN KEY REFERENCES Venues(Venue_ID), Category_ID INT FOREIGN KEY REFERENCES Categories(Category_ID), PRIMARY KEY (Venue_ID, Category_ID));

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Bookings]') AND type in (N'U'))
CREATE TABLE Bookings (Booking_ID INT PRIMARY KEY IDENTITY(1,1), Venue_ID INT FOREIGN KEY REFERENCES Venues(Venue_ID), Renter_ID INT FOREIGN KEY REFERENCES Users(User_ID), Start_Date DATETIME, End_Date DATETIME, Total_Price DECIMAL(10,2), Status NVARCHAR(50));

-- --- WSTAWIANIE DANYCH ---

IF NOT EXISTS (SELECT 1 FROM System_Config) INSERT INTO System_Config (Commission_Rate) VALUES (12.50);

IF NOT EXISTS (SELECT 1 FROM Provinces) INSERT INTO Provinces (Name) VALUES ('Dolnoslaskie'), ('Mazowieckie'), ('Malopolskie'), ('Pomorskie');

IF NOT EXISTS (SELECT 1 FROM Cities) INSERT INTO Cities (Province_ID, Name) VALUES (1, 'Wroclaw'), (2, 'Warszawa'), (3, 'Krakow'), (4, 'Gdansk'), (4, 'Sopot');

IF NOT EXISTS (SELECT 1 FROM Categories) INSERT INTO Categories (Category_Name) VALUES ('Sala bankietowa'), ('Loft industrialny'), ('Klub nocny'), ('Plener i Ogród'), ('Willa z basenem');

IF NOT EXISTS (SELECT 1 FROM Users) INSERT INTO Users (Email, Password_Hash, Role) VALUES
('admin@zlaplokal.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Admin'),
('kontakt@event-space.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Owner'),
('janusz.wlasciciel@gmail.com', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Owner'),
('tomasz.imprezowicz@wp.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Renter'),
('kasia.studentka@stud.pwr.edu.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Renter');

IF NOT EXISTS (SELECT 1 FROM Venues) INSERT INTO Venues (Owner_ID, City_ID, Name, Description, Capacity, Price_Per_Day, Deposit, photo) VALUES 
(2, 1, 'Neonowy Loft Nad Odra', 'Surowe, ceglane wnetrze.', 50, 1200.00, 500.00, 'venues_photos/neonowy_loft.png'),
(3, 2, 'Willa Konstancin', 'Ekskluzywna willa z basenem.', 120, 3500.00, 2000.00, 'venues_photos/willa_konstancin.png'),
(2, 4, 'Hala Stocznia', 'Ogromna przestrzen stoczniowa.', 300, 4500.00, 3000.00, 'venues_photos/hala_stocznia.png'),
(3, 3, 'Ogród z Alpakami', 'Cicha przestrzen z alpakami.', 30, 800.00, 200.00, 'venues_photos/ogrod_z_alpakami.png');

IF NOT EXISTS (SELECT 1 FROM Venue_Category) INSERT INTO Venue_Category (Venue_ID, Category_ID) VALUES (1, 2), (1, 3), (2, 5), (3, 2), (3, 3), (4, 4);

IF NOT EXISTS (SELECT 1 FROM Bookings) INSERT INTO Bookings (Venue_ID, Renter_ID, Start_Date, End_Date, Status) VALUES 
(1, 4, '2026-05-01 16:00:00', '2026-05-03 10:00:00', 'Paid'),
(3, 5, '2026-05-15 14:00:00', '2026-05-17 12:00:00', 'Confirmed');

GO