"""Skript na vytvorenie vzorovej SQLite databázy pre kníhkupectvo klasickej literatúry."""

import os
import sqlite3
from datetime import datetime, timedelta
import random
from .vzorove_data import VZOROVI_POUZIVATELIA, VZOROVE_KNIHY

# Cesta k databáze
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scratchpad", "database.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _vytvor_tabulku_pouzivatelia(kurzor):
    """Vytvorí tabuľku používateľov."""
    kurzor.execute(
        """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN NOT NULL
    )
    """
    )

def _vytvor_tabulku_knihy(kurzor):
    """Vytvorí tabuľku kníh."""
    kurzor.execute(
        """
    CREATE TABLE books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        genre TEXT NOT NULL,
        publication_year INTEGER NOT NULL,
        stock INTEGER DEFAULT 100
    )
    """
    )

def _vytvor_tabulku_objednavky(kurzor):
    """Vytvorí tabuľku objednávok."""
    kurzor.execute(
        """
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_amount DECIMAL(10,2) NOT NULL,
        status TEXT CHECK(status IN ('pending', 'completed', 'cancelled')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (book_id) REFERENCES books (id)
    )
    """
    )

def _vloz_vzorovych_pouzivatelov(kurzor, aktualny_cas):
    """Vloží vzorových používateľov do databázy."""
    cas = aktualny_cas
    for meno, priezvisko, email, je_aktivny in VZOROVI_POUZIVATELIA:
        kurzor.execute(
            "INSERT INTO users (first_name, last_name, email, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
            (meno, priezvisko, email, cas, je_aktivny),
        )
        cas -= timedelta(days=random.randint(1, 90))

def _vloz_vzorove_knihy(kurzor):
    """Vloží vzorové knihy do databázy."""
    for nazov, autor, cena, zaner, rok in VZOROVE_KNIHY:
        kurzor.execute(
            "INSERT INTO books (title, author, price, genre, publication_year) VALUES (?, ?, ?, ?, ?)",
            (nazov, autor, cena, zaner, rok),
        )

def _vloz_vzorove_objednavky(kurzor, datum_otvorenia_obchodu):
    """Vloží vzorové objednávky do databázy."""
    stavy = ["completed"] * 8 + ["pending"] * 1 + ["cancelled"] * 1  # 80% dokončených, 10% čakajúcich, 10% zrušených

    # Vytvorí viacero objednávok pre každého používateľa
    for id_pouzivatela in range(1, len(VZOROVI_POUZIVATELIA) + 1):
        # Vygeneruje 5-15 objednávok na používateľa
        pocet_objednavok = random.randint(5, 15)
        for _ in range(pocet_objednavok):
            id_knihy = random.randint(1, len(VZOROVE_KNIHY))
            mnozstvo = random.randint(1, 3)
            # Získa cenu knihy priamo z VZOROVE_KNIHY pomocou id_knihy - 1 ako indexu
            cena_knihy = VZOROVE_KNIHY[id_knihy - 1][2]  # Index 2 je cena v tuple knihy
            celkova_suma = round(mnozstvo * cena_knihy, 2)
            stav = random.choice(stavy)

            # Objednávky za posledné 3 mesiace
            datum_objednavky = datum_otvorenia_obchodu + timedelta(
                days=random.randint(0, 90), hours=random.randint(0, 23), minutes=random.randint(0, 59)
            )

            kurzor.execute(
                "INSERT INTO orders (user_id, book_id, quantity, total_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (id_pouzivatela, id_knihy, mnozstvo, celkova_suma, stav, datum_objednavky),
            )

def _vypis_vzorove_dotazy(kurzor):
    """Vypíše výsledky niekoľkých vzorových dotazov."""
    print("\n📊 Vzorové Dotazy:")

    print("\nAktívni Používatelia:")
    kurzor.execute(
        """
        SELECT first_name, last_name, email
        FROM users
        WHERE is_active = 1
        LIMIT 3
    """
    )
    print(kurzor.fetchall())

    print("\nDostupné Knihy:")
    kurzor.execute(
        """
        SELECT title, author, price
        FROM books
        LIMIT 3
    """
    )
    print(kurzor.fetchall())

    print("\nNedávne Objednávky:")
    kurzor.execute(
        """
        SELECT u.first_name, u.last_name, b.title, o.quantity, o.total_amount, o.created_at
        FROM orders o
        JOIN users u ON o.user_id = u.id
        JOIN books b ON o.book_id = b.id
        ORDER BY o.created_at DESC
        LIMIT 3
    """
    )
    print(kurzor.fetchall())


def vytvor_vzorovu_databazu():
    """Vytvorí vzorovú databázu kníhkupectva s tabuľkami používateľov, kníh a objednávok."""

    # Nastaví dátum otvorenia obchodu (3 mesiace pred 25. decembrom 2024)
    DATUM_OTVORENIA_OBCHODU = datetime(2024, 9, 25)
    AKTUALNY_DATUM = datetime(2024, 12, 25)

    # Pripojí sa k SQLite databáze (vytvorí ju, ak neexistuje)
    spojenie = sqlite3.connect(DB_PATH)
    kurzor = spojenie.cursor()

    try:
        # Vytvorí tabuľky
        _vytvor_tabulku_pouzivatelia(kurzor)
        _vytvor_tabulku_knihy(kurzor)
        _vytvor_tabulku_objednavky(kurzor)

        # Vloží vzorové dáta
        _vloz_vzorovych_pouzivatelov(kurzor, AKTUALNY_DATUM)
        _vloz_vzorove_knihy(kurzor)
        _vloz_vzorove_objednavky(kurzor, DATUM_OTVORENIA_OBCHODU)

        # Potvrdí zmeny
        spojenie.commit()
        print(f"✅ Vzorová databáza kníhkupectva úspešne vytvorená v {DB_PATH}")

        # Vypíše vzorové dáta
        _vypis_vzorove_dotazy(kurzor)

    except Exception as e:
        print(f"❌ Chyba pri vytváraní databázy: {str(e)}")
        spojenie.rollback()
    finally:
        spojenie.close()


if __name__ == "__main__":
    vytvor_vzorovu_databazu()
