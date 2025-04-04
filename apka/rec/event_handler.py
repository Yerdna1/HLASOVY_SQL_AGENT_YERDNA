"""Obsluha udalostí pre komunikáciu v reálnom čase."""

import asyncio
import inspect
from collections import defaultdict

class SpracovatelUdalostiRealnehoCasu:
    def __init__(self):
        self._spracovatelia_udalosti = defaultdict(list)

    def on(self, nazov_udalosti, spracovatel):
        """Zaregistruje spracovateľa pre danú udalosť."""
        self._spracovatelia_udalosti[nazov_udalosti].append(spracovatel)

    def vymaz_spracovatelov_udalosti(self):
        """Vymaže všetkých registrovaných spracovateľov udalostí."""
        self._spracovatelia_udalosti = defaultdict(list)

    def odosli(self, nazov_udalosti, udalost):
        """Odošle udalosť všetkým registrovaným spracovateľom."""
        for spracovatel in self._spracovatelia_udalosti[nazov_udalosti]:
            if inspect.iscoroutinefunction(spracovatel):
                asyncio.create_task(spracovatel(udalost))
            else:
                try:
                    spracovatel(udalost)
                except Exception as e:
                    # Logovanie chyby v synchrónnom spracovateli
                    print(f"Chyba v synchrónnom spracovateli pre udalosť '{nazov_udalosti}': {e}")


    async def pockaj_na_dalsiu(self, nazov_udalosti):
        """Asynchrónne čaká na nasledujúcu udalosť daného typu."""
        buducnost = asyncio.Future()

        def spracovatel(udalost):
            if not buducnost.done():
                buducnost.set_result(udalost)

        self.on(nazov_udalosti, spracovatel)
        return await buducnost
