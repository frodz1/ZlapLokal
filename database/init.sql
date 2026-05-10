USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'ZlapLokalDB')
BEGIN
    CREATE DATABASE ZlapLokalDB;
END
GO

USE ZlapLokalDB;
GO

CREATE TABLE Provinces (
    Province_ID INT PRIMARY KEY IDENTITY(1,1),
    Name NVARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE Cities (
    City_ID INT PRIMARY KEY IDENTITY(1,1),
    Province_ID INT FOREIGN KEY REFERENCES Provinces(Province_ID),
    Name NVARCHAR(100) NOT NULL
);

CREATE TABLE Categories (
    Category_ID INT PRIMARY KEY IDENTITY(1,1),
    Category_Name NVARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE System_Config (
    Config_ID INT PRIMARY KEY IDENTITY(1,1),
    Commission_Rate DECIMAL(5,2) NOT NULL,
    Updated_At DATETIME DEFAULT GETDATE()
);

CREATE TABLE Users (
    User_ID INT PRIMARY KEY IDENTITY(1,1),
    Email NVARCHAR(255) UNIQUE NOT NULL,
    Password_Hash NVARCHAR(255) NOT NULL,
    Role NVARCHAR(50) CHECK (Role IN ('Role_Admin', 'Role_Owner', 'Role_Renter')),
    Created_At DATETIME DEFAULT GETDATE(),
    Is_Active BIT DEFAULT 1
);

CREATE TABLE Venues (
    Venue_ID INT PRIMARY KEY IDENTITY(1,1),
    Owner_ID INT FOREIGN KEY REFERENCES Users(User_ID),
    City_ID INT FOREIGN KEY REFERENCES Cities(City_ID),
    Name NVARCHAR(255) NOT NULL,
    Description NVARCHAR(MAX),
    Capacity INT,
    Price_Per_Day MONEY NOT NULL,
    Deposit MONEY DEFAULT 0 CHECK (Deposit >= 0),
    Is_Deleted BIT DEFAULT 0
);

CREATE TABLE Venue_Category (
    Venue_ID INT FOREIGN KEY REFERENCES Venues(Venue_ID),
    Category_ID INT FOREIGN KEY REFERENCES Categories(Category_ID),
    PRIMARY KEY (Venue_ID, Category_ID)
);


CREATE TABLE Bookings (
    Booking_ID INT PRIMARY KEY IDENTITY(1,1),
    Venue_ID INT FOREIGN KEY REFERENCES Venues(Venue_ID),
    Renter_ID INT FOREIGN KEY REFERENCES Users(User_ID),
    Start_Date DATETIME NOT NULL,
    End_Date DATETIME NOT NULL,
    Total_Cost MONEY,
    System_Commission MONEY,
    Status NVARCHAR(50) DEFAULT 'Pending' CHECK (Status IN ('Pending', 'Confirmed', 'Paid', 'Completed', 'Cancelled')),
    CONSTRAINT CHK_Dates CHECK (Start_Date < End_Date)
);
GO

CREATE TRIGGER TRG_CheckOverbooking
ON Bookings
AFTER INSERT, UPDATE
AS
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM Bookings b
        JOIN inserted i ON b.Venue_ID = i.Venue_ID
        WHERE b.Booking_ID <> i.Booking_ID 
          AND i.Start_Date < b.End_Date 
          AND i.End_Date > b.Start_Date 
          AND b.Status NOT IN ('Cancelled')
    )
    BEGIN
        RAISERROR ('Error 50000: The dates are already booked for this venue!', 16, 1);
        ROLLBACK TRANSACTION; 
    END
END;
GO

CREATE TRIGGER TRG_CalculateCost
ON Bookings
AFTER INSERT
AS
BEGIN
    UPDATE b
    SET 
        Total_Cost = v.Price_Per_Day * DATEDIFF(day, i.Start_Date, i.End_Date),
        System_Commission = (v.Price_Per_Day * DATEDIFF(day, i.Start_Date, i.End_Date)) * (c.Commission_Rate / 100.0)
    FROM Bookings b
    JOIN inserted i ON b.Booking_ID = i.Booking_ID
    JOIN Venues v ON i.Venue_ID = v.Venue_ID
    CROSS JOIN (SELECT TOP 1 Commission_Rate FROM System_Config ORDER BY Config_ID DESC) c;
END;
GO

-- Testowe dane potem mozna usunac
INSERT INTO System_Config (Commission_Rate) VALUES (12.50);

INSERT INTO Provinces (Name) VALUES 
('Dolnoslaskie'), ('Mazowieckie'), ('Malopolskie'), ('Pomorskie');

INSERT INTO Cities (Province_ID, Name) VALUES 
(1, 'Wroclaw'), (2, 'Warszawa'), (3, 'Krakow'), (4, 'Gdansk'), (4, 'Sopot');

INSERT INTO Categories (Category_Name) VALUES 
('Sala bankietowa'), ('Loft industrialny'), ('Klub nocny'), ('Plener i Ogród'), ('Willa z basenem');

INSERT INTO Users (Email, Password_Hash, Role) VALUES
('admin@zlaplokal.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Admin'),
('kontakt@event-space.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Owner'),
('janusz.wlasciciel@gmail.com', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Owner'),
('tomasz.imprezowicz@wp.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Renter'),
('kasia.studentka@stud.pwr.edu.pl', '$2a$12$eImiTXuWVxfM37uY4JANjQ==', 'Role_Renter');

INSERT INTO Venues (Owner_ID, City_ID, Name, Description, Capacity, Price_Per_Day, Deposit) VALUES 
(2, 1, 'Neonowy Loft Nad Odra', 'Surowe, ceglane wnetrze z profesjonalnym naglosnieniem i oswietleniem LED. Idealne na 18-stki i imprezy firmowe.', 50, 1200.00, 500.00),
(3, 2, 'Willa Konstancin', 'Ekskluzywna willa z duzym ogrodem i basenem. Wymagana doplata za sprzatanie. Tylko dla osob powyzej 25 roku zycia.', 120, 3500.00, 2000.00),
(2, 4, 'Hala Stocznia', 'Ogromna przestrzen w starym budynku stoczniowym. Brak ciszy nocnej! Mozliwosc wjazdu foodtruckiem do srodka.', 300, 4500.00, 3000.00),
(3, 3, 'Ogród z Alpakami', 'Cicha i spokojna przestrzen na obrzezach miasta. W cenie wynajmu dostep do altany, grilla i... dwoch alpak.', 30, 800.00, 200.00);

INSERT INTO Venue_Category (Venue_ID, Category_ID) VALUES 
(1, 2), (1, 3), (2, 5), (3, 2), (3, 3), (4, 4);

INSERT INTO Bookings (Venue_ID, Renter_ID, Start_Date, End_Date, Status) 
VALUES (1, 4, '2026-05-01 16:00:00', '2026-05-03 10:00:00', 'Paid');

INSERT INTO Bookings (Venue_ID, Renter_ID, Start_Date, End_Date, Status) 
VALUES (3, 5, '2026-05-15 14:00:00', '2026-05-17 12:00:00', 'Confirmed');

INSERT INTO Bookings (Venue_ID, Renter_ID, Start_Date, End_Date, Status) 
VALUES (2, 4, '2026-06-10 12:00:00', '2026-06-12 12:00:00', 'Pending');

INSERT INTO Bookings (Venue_ID, Renter_ID, Start_Date, End_Date, Status) 
VALUES (4, 5, '2026-07-01 10:00:00', '2026-07-02 18:00:00', 'Cancelled');