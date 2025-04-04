"""
Skript na vytvorenie rozšírenej SQLite databázy pre knižničný systém.
Obsahuje 8 prepojených tabuliek a komplexné dotazy.
"""

import os
import sqlite3
from datetime import datetime, timedelta
import random

# Cesta k databáze
DB_PATH = "database.db"

# Vzorové dáta - autori
AUTORI = [
    ("Jozef", "Mak", "1890-05-15", "Slovensko", "Klasická literatúra"),
    ("Anna", "Nováková", "1950-09-23", "Slovensko", "Romantika"),
    ("Martin", "Horváth", "1978-03-10", "Slovensko", "Sci-fi"),
    ("Elena", "Kováčová", "1965-12-05", "Slovensko", "Detektívka"),
    ("Ján", "Botto", "1829-01-27", "Slovensko", "Romantizmus"),
    ("Pavol", "Országh Hviezdoslav", "1849-02-02", "Slovensko", "Realizmus"),
    ("Božena", "Slančíková-Timrava", "1867-11-02", "Slovensko", "Realizmus"),
    ("Margita", "Figuli", "1909-10-02", "Slovensko", "Naturizmus"),
    ("Ladislav", "Mňačko", "1919-01-29", "Slovensko", "Socialistický realizmus"),
    ("Dominik", "Tatarka", "1913-03-14", "Slovensko", "Postmoderna")
]

# Vzorové dáta - vydavatelia
VYDAVATELIA = [
    ("Slovenský Spisovateľ", "Bratislava", "1950", "info@sspis.sk", True),
    ("Ikar", "Bratislava", "1990", "ikar@ikar.sk", True),
    ("Tatran", "Bratislava", "1947", "tatran@tatran.sk", True),
    ("Slovart", "Bratislava", "1991", "slovart@slovart.sk", True),
    ("Matica slovenská", "Martin", "1863", "matica@matica.sk", True)
]

# Vzorové dáta - knihy
KNIHY = [
    ("Smrť sa volá Engelchen", 9, 4, 1959, "978-80-8202-031-4", 12.99, 120),
    ("Tri gaštanové kone", 8, 1, 1940, "978-80-8046-431-5", 10.50, 80),
    ("Slávy dcéra", 6, 3, 1952, "978-80-8202-032-1", 11.99, 150),
    ("Krvavý mesiac", 3, 2, 2005, "978-80-556-1234-5", 14.50, 200),
    ("Zbojnícka mladosť", 5, 5, 1937, "978-80-8046-425-4", 9.99, 75),
    ("Keď báseň zakvitne", 6, 3, 1960, "978-80-8202-045-1", 8.50, 100),
    ("Neznámy svet", 3, 4, 2010, "978-80-556-1299-4", 16.99, 180),
    ("Ťapákovci", 7, 1, 1963, "978-80-8046-411-7", 7.99, 60),
    ("Babylon", 9, 2, 1984, "978-80-556-1288-8", 13.50, 95),
    ("Tiene v raji", 10, 5, 1972, "978-80-8202-099-4", 15.99, 130),
    ("Čakanie na tmu", 4, 2, 2015, "978-80-556-1567-4", 17.50, 210),
    ("Horúci dych", 2, 3, 2008, "978-80-8202-144-1", 12.99, 85),
    ("Medzi nebom a zemou", 1, 4, 1995, "978-80-8046-500-8", 11.50, 70),
    ("Smäd", 8, 5, 1949, "978-80-556-1321-2", 9.99, 110),
    ("Stretnutie", 3, 1, 2018, "978-80-8202-200-4", 19.99, 240)
]

# Vzorové dáta - žánre
ZANRE = [
    "Romantika",
    "Detektívka",
    "Fantasy",
    "Sci-fi",
    "Historický román",
    "Dráma",
    "Poézia",
    "Biografia",
    "Cestopis",
    "Young Adult"
]

# Vzorové dáta - používatelia
POUZIVATELIA = [
    ("Peter", "Novák", "peter.novak@gmail.com", "0901234567", "Bratislava", True),
    ("Mária", "Kováčová", "maria.kovacova@gmail.com", "0912345678", "Košice", True),
    ("Ján", "Horváth", "jan.horvath@gmail.com", "0923456789", "Banská Bystrica", True),
    ("Zuzana", "Tóthová", "zuzana.tothova@gmail.com", "0934567890", "Nitra", True),
    ("Michal", "Baláž", "michal.balaz@gmail.com", "0945678901", "Trnava", True),
    ("Eva", "Lukáčová", "eva.lukacova@gmail.com", "0956789012", "Prešov", False),
    ("Tomáš", "Polák", "tomas.polak@gmail.com", "0967890123", "Žilina", True),
    ("Katarína", "Štefanková", "katarina.stefankova@gmail.com", "0978901234", "Trenčín", False),
    ("Marek", "Kučera", "marek.kucera@gmail.com", "0989012345", "Martin", True),
    ("Simona", "Danišová", "simona.danisova@gmail.com", "0990123456", "Poprad", True)
]

# Vzorové dáta - pobočky knižnice
POBOCKY = [
    ("Centrálna knižnica", "Námestie SNP 1", "Bratislava", "02/12345678", "central@kniznica.sk"),
    ("Pobočka Juh", "Južná 15", "Bratislava", "02/23456789", "juh@kniznica.sk"),
    ("Pobočka Košice", "Hlavná 25", "Košice", "055/6789012", "kosice@kniznica.sk"),
    ("Pobočka Žilina", "Mariánske námestie 3", "Žilina", "041/5678901", "zilina@kniznica.sk"),
    ("Detská knižnica", "Školská 5", "Bratislava", "02/34567890", "detska@kniznica.sk")
]

# Udalosti knižnice
UDALOSTI = [
    ("Noc literatúry", "Čítanie z novej slovenskej literatúry", "2024-05-15 18:00:00", "2024-05-15 22:00:00", 1),
    ("Autorské čítanie: Anna Nováková", "Predstavenie novej knihy", "2024-06-10 17:00:00", "2024-06-10 19:00:00", 2),
    ("Detský literárny workshop", "Tvorivé písanie pre deti", "2024-06-20 14:00:00", "2024-06-20 16:00:00", 5),
    ("Knižný festival", "Celoslovenský knižný veľtrh", "2024-07-05 09:00:00", "2024-07-07 18:00:00", 1),
    ("Beseda o sci-fi literatúre", "Diskusia s autormi sci-fi", "2024-08-12 17:00:00", "2024-08-12 19:30:00", 3)
]

def vytvor_tabulky(kurzor):
    """Vytvorí všetky potrebné tabuľky v databáze."""
    
    # Tabuľka autorov
    kurzor.execute("""
    CREATE TABLE autori (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meno TEXT NOT NULL,
        priezvisko TEXT NOT NULL,
        datum_narodenia DATE,
        krajina TEXT,
        hlavny_zaner TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabuľka vydavateľov
    kurzor.execute("""
    CREATE TABLE vydavatelia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nazov TEXT NOT NULL,
        mesto TEXT NOT NULL,
        rok_zalozenia TEXT,
        kontakt TEXT,
        je_aktivny BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabuľka žánrov
    kurzor.execute("""
    CREATE TABLE zanre (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nazov TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabuľka kníh
    kurzor.execute("""
    CREATE TABLE knihy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nazov TEXT NOT NULL,
        id_autora INTEGER NOT NULL,
        id_vydavatela INTEGER NOT NULL,
        rok_vydania INTEGER NOT NULL,
        isbn TEXT UNIQUE,
        cena DECIMAL(10,2) NOT NULL,
        pocet_stran INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_autora) REFERENCES autori (id),
        FOREIGN KEY (id_vydavatela) REFERENCES vydavatelia (id)
    )
    """)
    
    # Prepojovacia tabuľka medzi knihami a žánrami (many-to-many)
    kurzor.execute("""
    CREATE TABLE knihy_zanre (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_knihy INTEGER NOT NULL,
        id_zanru INTEGER NOT NULL,
        FOREIGN KEY (id_knihy) REFERENCES knihy (id),
        FOREIGN KEY (id_zanru) REFERENCES zanre (id),
        UNIQUE(id_knihy, id_zanru)
    )
    """)
    
    # Tabuľka používateľov
    kurzor.execute("""
    CREATE TABLE pouzivatelia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meno TEXT NOT NULL,
        priezvisko TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        telefon TEXT,
        mesto TEXT,
        je_aktivny BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabuľka pobočiek knižnice
    kurzor.execute("""
    CREATE TABLE pobocky (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nazov TEXT NOT NULL,
        adresa TEXT NOT NULL,
        mesto TEXT NOT NULL,
        telefon TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Tabuľka výpožičiek
    kurzor.execute("""
    CREATE TABLE vypozicky (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pouzivatela INTEGER NOT NULL,
        id_knihy INTEGER NOT NULL,
        id_pobocky INTEGER NOT NULL,
        datum_vypozicky TIMESTAMP NOT NULL,
        datum_vratenia TIMESTAMP,
        predpokladany_datum_vratenia TIMESTAMP NOT NULL,
        stav TEXT CHECK(stav IN ('požičaná', 'vrátená', 'prekročená', 'stratená')) NOT NULL DEFAULT 'požičaná',
        FOREIGN KEY (id_pouzivatela) REFERENCES pouzivatelia (id),
        FOREIGN KEY (id_knihy) REFERENCES knihy (id),
        FOREIGN KEY (id_pobocky) REFERENCES pobocky (id)
    )
    """)
    
    # Tabuľka udalostí
    kurzor.execute("""
    CREATE TABLE udalosti (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nazov TEXT NOT NULL,
        popis TEXT,
        datum_zaciatku TIMESTAMP NOT NULL,
        datum_konca TIMESTAMP NOT NULL,
        id_pobocky INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_pobocky) REFERENCES pobocky (id)
    )
    """)

def vloz_vzorove_data(kurzor):
    """Vloží vzorové dáta do všetkých tabuliek."""
    
    # Vloženie autorov
    for meno, priezvisko, datum_narodenia, krajina, hlavny_zaner in AUTORI:
        kurzor.execute(
            "INSERT INTO autori (meno, priezvisko, datum_narodenia, krajina, hlavny_zaner) VALUES (?, ?, ?, ?, ?)",
            (meno, priezvisko, datum_narodenia, krajina, hlavny_zaner)
        )
    
    # Vloženie vydavateľov
    for nazov, mesto, rok_zalozenia, kontakt, je_aktivny in VYDAVATELIA:
        kurzor.execute(
            "INSERT INTO vydavatelia (nazov, mesto, rok_zalozenia, kontakt, je_aktivny) VALUES (?, ?, ?, ?, ?)",
            (nazov, mesto, rok_zalozenia, kontakt, je_aktivny)
        )
    
    # Vloženie žánrov
    for zaner in ZANRE:
        kurzor.execute("INSERT INTO zanre (nazov) VALUES (?)", (zaner,))
    
    # Vloženie kníh
    for nazov, id_autora, id_vydavatela, rok_vydania, isbn, cena, pocet_stran in KNIHY:
        kurzor.execute(
            "INSERT INTO knihy (nazov, id_autora, id_vydavatela, rok_vydania, isbn, cena, pocet_stran) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nazov, id_autora, id_vydavatela, rok_vydania, isbn, cena, pocet_stran)
        )
    
    # Vytvorenie prepojenia kníh so žánrami (každá kniha má 1-3 žánre)
    for id_knihy in range(1, len(KNIHY) + 1):
        # Náhodný výber 1-3 žánrov pre každú knihu
        pocet_zanrov = random.randint(1, 3)
        vybrane_zanre = random.sample(range(1, len(ZANRE) + 1), pocet_zanrov)
        
        for id_zanru in vybrane_zanre:
            kurzor.execute(
                "INSERT INTO knihy_zanre (id_knihy, id_zanru) VALUES (?, ?)",
                (id_knihy, id_zanru)
            )
    
    # Vloženie používateľov
    for meno, priezvisko, email, telefon, mesto, je_aktivny in POUZIVATELIA:
        kurzor.execute(
            "INSERT INTO pouzivatelia (meno, priezvisko, email, telefon, mesto, je_aktivny) VALUES (?, ?, ?, ?, ?, ?)",
            (meno, priezvisko, email, telefon, mesto, je_aktivny)
        )
    
    # Vloženie pobočiek
    for nazov, adresa, mesto, telefon, email in POBOCKY:
        kurzor.execute(
            "INSERT INTO pobocky (nazov, adresa, mesto, telefon, email) VALUES (?, ?, ?, ?, ?)",
            (nazov, adresa, mesto, telefon, email)
        )
    
    # Vloženie udalostí
    for nazov, popis, datum_zaciatku, datum_konca, id_pobocky in UDALOSTI:
        kurzor.execute(
            "INSERT INTO udalosti (nazov, popis, datum_zaciatku, datum_konca, id_pobocky) VALUES (?, ?, ?, ?, ?)",
            (nazov, popis, datum_zaciatku, datum_konca, id_pobocky)
        )
    
    # Vloženie výpožičiek (približne 30 výpožičiek za posledných 6 mesiacov)
    aktualny_datum = datetime.now()
    stavy = ["požičaná", "vrátená", "vrátená", "vrátená", "prekročená", "stratená"]  # Viac vrátených kníh ako ostatných stavov
    
    for _ in range(30):
        id_pouzivatela = random.randint(1, len(POUZIVATELIA))
        id_knihy = random.randint(1, len(KNIHY))
        id_pobocky = random.randint(1, len(POBOCKY))
        
        # Náhodný dátum výpožičky v posledných 6 mesiacoch
        datum_vypozicky = aktualny_datum - timedelta(days=random.randint(0, 180))
        
        # Predpokladané vrátenie o 14-30 dní
        predpokladany_datum_vratenia = datum_vypozicky + timedelta(days=random.randint(14, 30))
        
        # Stav výpožičky
        stav = random.choice(stavy)
        
        # Ak je stav "vrátená", nastavíme dátum vrátenia, inak None
        datum_vratenia = None
        if stav == "vrátená":
            datum_vratenia = datum_vypozicky + timedelta(days=random.randint(7, 25))
        elif stav == "prekročená":
            datum_vratenia = None  # Ešte nevrátená, ale mala by už byť
        
        kurzor.execute(
            "INSERT INTO vypozicky (id_pouzivatela, id_knihy, id_pobocky, datum_vypozicky, datum_vratenia, predpokladany_datum_vratenia, stav) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id_pouzivatela, id_knihy, id_pobocky, datum_vypozicky, datum_vratenia, predpokladany_datum_vratenia, stav)
        )

def vypis_vzorove_dotazy(kurzor):
    """Vypíše výsledky niekoľkých vzorových dotazov."""
    print("\n===== ZÁKLADNÉ DOTAZY =====")

    print("\n1. Zoznam všetkých autorov:")
    kurzor.execute("""
        SELECT meno, priezvisko, krajina, hlavny_zaner 
        FROM autori 
        ORDER BY priezvisko
    """)
    for autor in kurzor.fetchall():
        print(autor)

    print("\n2. Zoznam kníh s cenou vyššou ako 12 €:")
    kurzor.execute("""
        SELECT nazov, cena, rok_vydania
        FROM knihy
        WHERE cena > 12.00
        ORDER BY cena DESC
    """)
    for kniha in kurzor.fetchall():
        print(kniha)

    print("\n===== ZLOŽITEJŠIE DOTAZY =====")

    print("\n3. Knihy so svojimi autormi a vydavateľmi:")
    kurzor.execute("""
        SELECT k.nazov, a.meno || ' ' || a.priezvisko AS autor, v.nazov AS vydavatel, k.rok_vydania
        FROM knihy k
        JOIN autori a ON k.id_autora = a.id
        JOIN vydavatelia v ON k.id_vydavatela = v.id
        ORDER BY k.nazov
        LIMIT 5
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

    print("\n4. Počet kníh podľa vydavateľov:")
    kurzor.execute("""
        SELECT v.nazov, COUNT(k.id) AS pocet_knih
        FROM vydavatelia v
        LEFT JOIN knihy k ON v.id = k.id_vydavatela
        GROUP BY v.id
        ORDER BY pocet_knih DESC
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

    print("\n5. Knihy s viacerými žánrami:")
    kurzor.execute("""
        SELECT k.nazov, GROUP_CONCAT(z.nazov, ', ') AS zanre
        FROM knihy k
        JOIN knihy_zanre kz ON k.id = kz.id_knihy
        JOIN zanre z ON kz.id_zanru = z.id
        GROUP BY k.id
        ORDER BY k.nazov
        LIMIT 5
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

    print("\n===== KOMPLEXNÉ DOTAZY =====")

    print("\n6. Aktívni používatelia s počtom výpožičiek:")
    kurzor.execute("""
        SELECT p.meno, p.priezvisko, p.mesto, COUNT(v.id) AS pocet_vypoziciek
        FROM pouzivatelia p
        LEFT JOIN vypozicky v ON p.id = v.id_pouzivatela
        WHERE p.je_aktivny = 1
        GROUP BY p.id
        ORDER BY pocet_vypoziciek DESC
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

    print("\n7. Momentálne požičané knihy s detailmi:")
    kurzor.execute("""
        SELECT 
            k.nazov AS kniha, 
            a.meno || ' ' || a.priezvisko AS autor,
            p.meno || ' ' || p.priezvisko AS pouzivatel,
            pb.nazov AS pobocka,
            v.datum_vypozicky,
            v.predpokladany_datum_vratenia
        FROM vypozicky v
        JOIN knihy k ON v.id_knihy = k.id
        JOIN autori a ON k.id_autora = a.id
        JOIN pouzivatelia p ON v.id_pouzivatela = p.id
        JOIN pobocky pb ON v.id_pobocky = pb.id
        WHERE v.stav = 'požičaná'
        ORDER BY v.predpokladany_datum_vratenia
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

    print("\n8. Najobľúbenejšie žánre podľa výpožičiek:")
    kurzor.execute("""
        SELECT z.nazov AS zaner, COUNT(v.id) AS pocet_vypoziciek
        FROM zanre z
        JOIN knihy_zanre kz ON z.id = kz.id_zanru
        JOIN knihy k ON kz.id_knihy = k.id
        JOIN vypozicky v ON k.id = v.id_knihy
        GROUP BY z.id
        ORDER BY pocet_vypoziciek DESC
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

    print("\n9. Štatistika výpožičiek podľa pobočiek:")
    kurzor.execute("""
        SELECT 
            pb.nazov AS pobocka, 
            COUNT(v.id) AS celkovy_pocet,
            SUM(CASE WHEN v.stav = 'požičaná' THEN 1 ELSE 0 END) AS aktivne_vypozicky,
            SUM(CASE WHEN v.stav = 'vrátená' THEN 1 ELSE 0 END) AS vratene,
            SUM(CASE WHEN v.stav = 'prekročená' THEN 1 ELSE 0 END) AS prekrocene
        FROM pobocky pb
        LEFT JOIN vypozicky v ON pb.id = v.id_pobocky
        GROUP BY pb.id
        ORDER BY celkovy_pocet DESC
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

    print("\n10. Meškajúce výpožičky s informáciami o používateľoch:")
    kurzor.execute("""
        SELECT 
            p.meno || ' ' || p.priezvisko AS pouzivatel,
            p.email,
            p.telefon,
            k.nazov AS kniha,
            v.predpokladany_datum_vratenia,
            julianday('now') - julianday(v.predpokladany_datum_vratenia) AS dni_po_termine
        FROM vypozicky v
        JOIN pouzivatelia p ON v.id_pouzivatela = p.id
        JOIN knihy k ON v.id_knihy = k.id
        WHERE v.stav = 'prekročená'
        ORDER BY dni_po_termine DESC
    """)
    for riadok in kurzor.fetchall():
        print(riadok)

def vytvor_vzorovu_databazu():
    """Vytvorí vzorovú knižničnú databázu s 8 tabuľkami a vzájomným prepojením."""
    
    # Odstráni existujúcu databázu ak existuje
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    # Pripojí sa k SQLite databáze (vytvorí ju, ak neexistuje)
    spojenie = sqlite3.connect(DB_PATH)
    kurzor = spojenie.cursor()
    
    try:
        # Vytvorí tabuľky
        vytvor_tabulky(kurzor)
        
        # Vloží vzorové dáta
        vloz_vzorove_data(kurzor)
        
        # Potvrdí zmeny
        spojenie.commit()
        
        print(f"✅ Rozšírená knižničná databáza úspešne vytvorená v {DB_PATH}")
        
        # Vypíše vzorové dotazy
        vypis_vzorove_dotazy(kurzor)
        
    except Exception as e:
        print(f"❌ Chyba pri vytváraní databázy: {str(e)}")
        spojenie.rollback()
    finally:
        spojenie.close()

if __name__ == "__main__":
    vytvor_vzorovu_databazu()