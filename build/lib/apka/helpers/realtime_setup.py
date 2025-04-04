"""Pomocné funkcie pre nastavenie real-time klienta v Chainlit."""

import asyncio
from uuid import uuid4
import chainlit as cl
from chainlit.logger import logger

# Import
from apka.rec import KlientRealnehoCasu
# Predpokladáme, že 'nastroje' budú definované a importované v main.py alebo inom module
# from apka.custom_nastroje import nastroje # Príklad, upraviť podľa skutočnosti

async def nastav_realtime_klienta(zoznam_nastrojov):
    """Inštancuje a konfiguruje KlientaRealnehoCasu."""
    klient_realneho_casu = KlientRealnehoCasu()
    cl.user_session.set("id_sledovania", str(uuid4()))

    async def spracuj_aktualizaciu_konverzacie(udalost):
        polozka = udalost.get("item")
        delta = udalost.get("delta")
        """Používa sa na streamovanie audia späť klientovi."""
        if delta:
            # Len jedna z nasledujúcich hodnôt bude vyplnená pre danú udalosť
            if "audio" in delta:
                audio_data = delta["audio"]
                # Predpokladáme, že audio_data sú už bajty alebo ich možno konvertovať
                # Ak je to numpy pole, treba ho konvertovať:
                # if isinstance(audio_data, np.ndarray):
                #     audio_data = audio_data.tobytes()
                await cl.context.emitter.send_audio_chunk(
                    cl.OutputAudioChunk(
                        mimeType="pcm16",
                        data=audio_data,
                        track=cl.user_session.get("id_sledovania"),
                    )
                )
            if "transcript" in delta:
                prepis = delta["transcript"]
                # TODO: Prípadné spracovanie prepisu
                pass
            if "arguments" in delta:
                argumenty = delta["arguments"]
                # TODO: Prípadné spracovanie argumentov funkcie
                pass

    async def spracuj_dokoncenie_polozky(polozka):
        """Používa sa na naplnenie kontextu chatu prepisom po dokončení položky."""
        # logger.info(f"Položka dokončená: {polozka}")
        pass

    async def spracuj_prerusenie_konverzacie(udalost):
        """Používa sa na zrušenie predchádzajúceho prehrávania audia klienta."""
        cl.user_session.set("id_sledovania", str(uuid4()))
        await cl.context.emitter.send_audio_interrupt()

    async def spracuj_chybu(udalost):
        """Spracuje chyby z klienta."""
        logger.error(f"Chyba real-time klienta: {udalost}")

    # Registrácia spracovateľov udalostí
    klient_realneho_casu.on("conversation.updated", spracuj_aktualizaciu_konverzacie) # Kľúč API
    klient_realneho_casu.on("conversation.item.completed", spracuj_dokoncenie_polozky)
    klient_realneho_casu.on("conversation.interrupted", spracuj_prerusenie_konverzacie)
    klient_realneho_casu.on("error", spracuj_chybu)

    # Uloženie klienta do session
    cl.user_session.set("klient_realneho_casu", klient_realneho_casu)

    # Pridanie nástrojov (ak sú poskytnuté)
    if zoznam_nastrojov:
        korutiny = [
            klient_realneho_casu.pridaj_nastroj(definicia, spracovatel)
            for definicia, spracovatel in zoznam_nastrojov
        ]
        await asyncio.gather(*korutiny)
    else:
        logger.warning("Neboli poskytnuté žiadne nástroje pre real-time klienta.")

    return klient_realneho_casu
