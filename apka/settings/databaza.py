"""Správa konfigurácie a pripojenia k databáze."""

import os
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import create_engine, text
from apka.widgets.spolocne import zapisovac
from apka.models.db_models import KonfiguraciaDatabazy
from apka.utils.db_utils import INFO_O_DIALEKTE


class PripojenieDatabazy:
    """Spravuje databázové pripojenia a operácie."""

    def __init__(self):
        self._engine = None
        self._retazec_pripojenia = None

    def pripoj(self, konfiguracia: KonfiguraciaDatabazy) -> bool:
        """Vytvorí databázové pripojenie na základe poskytnutej konfigurácie."""
        try:
            # Zostavenie reťazca pripojenia na základe dialektu
            if konfiguracia.dialekt == "sqlite":
                # Zabezpečíme, že cesta pre SQLite je relatívna k root adresáru projektu, ak nie je absolútna
                db_cesta = konfiguracia.databaza
                if not os.path.isabs(db_cesta):
                     # Predpokladáme, že tento súbor je v apka/settings, ideme o 2 úrovne vyššie
                     project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                     db_cesta = os.path.join(project_root, db_cesta)
                     # Vytvoríme adresár, ak neexistuje
                     os.makedirs(os.path.dirname(db_cesta), exist_ok=True)
                self._retazec_pripojenia = f"sqlite:///{db_cesta}"
            else:
                # Pre PostgreSQL, MySQL, atď.
                autentifikacia = f"{konfiguracia.pouzivatelske_meno}:{konfiguracia.heslo}@" if konfiguracia.pouzivatelske_meno else ""
                hostitel = f"{konfiguracia.hostitel}:{konfiguracia.port}" if konfiguracia.hostitel else "localhost"
                self._retazec_pripojenia = f"{konfiguracia.dialekt}://{autentifikacia}{hostitel}/{konfiguracia.databaza}"

            self._engine = create_engine(self._retazec_pripojenia)
            # Otestovanie pripojenia
            with self._engine.connect() as spojenie:
                spojenie.execute(text("SELECT 1"))

            zapisovac.info(f"Úspešne pripojené k {konfiguracia.dialekt} databáze: {konfiguracia.databaza}")
            return True

        except Exception as e:
            zapisovac.error(f"Chyba pri pripájaní k databáze: {str(e)}")
            self._engine = None # Reset engine on connection failure
            self._retazec_pripojenia = None
            return False

    def vykonaj_dotaz(self, dotaz: str) -> Dict[str, Any]:
        """Vykoná SQL dotaz a vráti výsledky."""
        if not self._engine:
            return {"error": "Nie je nadviazané žiadne databázové pripojenie"}

        try:
            with self._engine.connect() as spojenie:
                vysledok = spojenie.execute(text(dotaz))

                # Pre INSERT, UPDATE, DELETE vrátime počet ovplyvnených riadkov
                if not vysledok.returns_rows:
                     spojenie.commit() # Commit changes for non-SELECT statements
                     return {"affected_rows": vysledok.rowcount}

                # Pre SELECT dotazy vrátime výsledky
                stlpce = list(vysledok.keys())
                riadky = [dict(zip(stlpce, riadok)) for riadok in vysledok.fetchall()]
                return {"columns": stlpce, "rows": riadky}

        except Exception as e:
            zapisovac.error(f"Chyba pri vykonávaní dotazu: {str(e)}")
            # V prípade chyby môžeme chcieť vrátiť transakciu späť, ak bola spustená
            # with self._engine.connect() as spojenie:
            #     spojenie.rollback() # Toto nemusí byť vždy potrebné alebo možné v závislosti od chyby
            return {"error": str(e)}

    def je_pripojene(self) -> bool:
         """Skontroluje, či je pripojenie aktívne."""
         return self._engine is not None


def inicializuj_globalne_db_spojenie() -> Tuple[Optional[PripojenieDatabazy], Optional[KonfiguraciaDatabazy], Optional[dict]]:
    """
    Načíta konfiguráciu z prostredia, inicializuje a otestuje globálne pripojenie k databáze.
    Vracia inštanciu pripojenia, konfiguráciu a informácie o dialekte.
    """
    # Konfigurácia pripojenia k databáze z premenných prostredia alebo predvolených hodnôt
    konfiguracia = KonfiguraciaDatabazy(
        dialekt=os.getenv("DB_DIALECT", "sqlite"),
        pouzivatelske_meno=os.getenv("DB_USERNAME"),
        heslo=os.getenv("DB_PASSWORD"),
        hostitel=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None,
        # Predvolená cesta pre SQLite relatívna k root adresáru projektu
        databaza=os.getenv("DB_DATABASE", "scratchpad/apka_databaza.db"),
    )

    # Vytvorenie globálnej inštancie pripojenia k databáze
    spojenie = PripojenieDatabazy()

    # Inicializácia pripojenia k databáze
    if spojenie.pripoj(konfiguracia):
        info_dialekt = INFO_O_DIALEKTE.get(konfiguracia.dialekt.lower(), {})
        return spojenie, konfiguracia, info_dialekt
    else:
        zapisovac.warning("Nepodarilo sa inicializovať globálne databázové pripojenie.")
        return None, konfiguracia, None # Vrátime konfiguráciu pre prípadnú diagnostiku

# Inicializácia globálnych premenných pri importe modulu
db_spojenie, db_konfiguracia, info_o_dialekte = inicializuj_globalne_db_spojenie()

# Export preložených názvov pre kompatibilitu (ak ich iné moduly očakávajú)
# Tieto aliasy by sa mali časom odstrániť a priamo používať nové názvy
db_connection = db_spojenie
db_config = db_konfiguracia
dialect_info = info_o_dialekte
