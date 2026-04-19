USE master;
GO

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'ZlapLokalDB')
BEGIN
    CREATE DATABASE ZlapLokalDB;
END
GO

USE ZlapLokalDB;
GO

CREATE TABLE Wojewodztwa (
    ID_Wojewodztwa INT PRIMARY KEY IDENTITY(1,1),
    Nazwa NVARCHAR(100) NOT NULL
);

CREATE TABLE Miasta (
    ID_Miasta INT PRIMARY KEY IDENTITY(1,1),
    ID_Wojewodztwa INT FOREIGN KEY REFERENCES Wojewodztwa(ID_Wojewodztwa),
    Nazwa NVARCHAR(100) NOT NULL
);

CREATE TABLE Kategorie (
    ID_Kategorii INT PRIMARY KEY IDENTITY(1,1),
    Nazwa_Kategorii NVARCHAR(100) NOT NULL
);

CREATE TABLE System_Config (
    ID_Wpisu INT PRIMARY KEY IDENTITY(1,1),
    Stawka_Prowizji DECIMAL(5,2) NOT NULL,
    Data_Aktualizacji DATETIME DEFAULT GETDATE()
);

CREATE TABLE Uzytkownicy (
    ID_Uzytkownika INT PRIMARY KEY IDENTITY(1,1),
    Email NVARCHAR(255) UNIQUE NOT NULL,
    Haslo_Hash NVARCHAR(255) NOT NULL,
    Rola NVARCHAR(50) CHECK (Rola IN ('Role_Admin', 'Role_Owner', 'Role_Renter')),
    Data_Utworzenia DATETIME DEFAULT GETDATE(),
    Czy_Aktywny BIT DEFAULT 1
);

CREATE TABLE Lokale (
    ID_Lokalu INT PRIMARY KEY IDENTITY(1,1),
    ID_Wlasciciela INT FOREIGN KEY REFERENCES Uzytkownicy(ID_Uzytkownika),
    ID_Miasta INT FOREIGN KEY REFERENCES Miasta(ID_Miasta),
    Nazwa NVARCHAR(255) NOT NULL,
    Opis NVARCHAR(MAX),
    Pojemnosc INT,
    Cena_Doba MONEY NOT NULL,
    Kaucja MONEY DEFAULT 0,
    Czy_Usuniety BIT DEFAULT 0
);

CREATE TABLE Lokal_Kategoria (
    ID_Lokalu INT FOREIGN KEY REFERENCES Lokale(ID_Lokalu),
    ID_Kategorii INT FOREIGN KEY REFERENCES Kategorie(ID_Kategorii),
    PRIMARY KEY (ID_Lokalu, ID_Kategorii)
);

CREATE TABLE Rezerwacje (
    ID_Rezerwacji INT PRIMARY KEY IDENTITY(1,1),
    ID_Lokalu INT FOREIGN KEY REFERENCES Lokale(ID_Lokalu),
    ID_Wynajmujacego INT FOREIGN KEY REFERENCES Uzytkownicy(ID_Uzytkownika),
    Data_Od DATETIME NOT NULL,
    Data_Do DATETIME NOT NULL,
    Koszt_Calkowity MONEY,
    Prowizja_Systemu MONEY,
    Status NVARCHAR(50) DEFAULT 'Oczekujaca'
);
GO

CREATE TRIGGER TRG_CheckOverbooking
ON Rezerwacje
AFTER INSERT, UPDATE
AS
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM Rezerwacje r
        JOIN inserted i ON r.ID_Lokalu = i.ID_Lokalu
        WHERE r.ID_Rezerwacji <> i.ID_Rezerwacji 
          AND i.Data_Od < r.Data_Do 
          AND i.Data_Do > r.Data_Od 
    )
    BEGIN
        RAISERROR ('Blad 50000: Termin jest juz zajety dla tego lokalu!', 16, 1);
        ROLLBACK TRANSACTION; 
    END
END;
GO

CREATE TRIGGER TRG_CalculateCost
ON Rezerwacje
AFTER INSERT
AS
BEGIN
    UPDATE r
    SET 
        Koszt_Calkowity = l.Cena_Doba * DATEDIFF(day, i.Data_Od, i.Data_Do),
        Prowizja_Systemu = (l.Cena_Doba * DATEDIFF(day, i.Data_Od, i.Data_Do)) * (c.Stawka_Prowizji / 100.0)
    FROM Rezerwacje r
    JOIN inserted i ON r.ID_Rezerwacji = i.ID_Rezerwacji
    JOIN Lokale l ON i.ID_Lokalu = l.ID_Lokalu
    CROSS JOIN (SELECT TOP 1 Stawka_Prowizji FROM System_Config ORDER BY ID_Wpisu DESC) c;
END;
GO

INSERT INTO Wojewodztwa (Nazwa) VALUES ('Dolnoslaskie'), ('Mazowieckie');
INSERT INTO Miasta (ID_Wojewodztwa, Nazwa) VALUES (1, 'Wroclaw'), (2, 'Warszawa');
INSERT INTO Kategorie (Nazwa_Kategorii) VALUES ('Sala bankietowa'), ('Loft industrialny');
INSERT INTO System_Config (Stawka_Prowizji) VALUES (10.00);
INSERT INTO Uzytkownicy (Email, Haslo_Hash, Rola) VALUES
('admin@zlaplokal.pl', 'hash1', 'Role_Admin'),
('jan.owner@gmail.com', 'hash2', 'Role_Owner'),
('anna.renter@wp.pl', 'hash3', 'Role_Renter');
INSERT INTO Lokale (ID_Wlasciciela, ID_Miasta, Nazwa, Cena_Doba) VALUES (2, 1, 'Perla Wroclawia', 1500.00);
INSERT INTO Rezerwacje (ID_Lokalu, ID_Wynajmujacego, Data_Od, Data_Do, Status) 
VALUES (1, 3, '2026-05-01 14:00:00', '2026-05-03 12:00:00', 'Potwierdzona');
GO
