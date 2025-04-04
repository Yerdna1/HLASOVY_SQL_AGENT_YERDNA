"""
Hlavný súbor aplikácie Chainlit pre real-time asistenta.
Odvodené z https://github.com/Chainlit/cookbook/tree/main/realtime-assistant
"""

import traceback
import chainlit as cl
from chainlit.logger import logger

# Import pomocných funkcií
from apka.rec import KlientRealnehoCasu
from apka.helpers.realtime_setup import nastav_realtime_klienta
# Import nástrojov - predpokladáme, že tento import zostáva alebo bude upravený
from apka.custom_nastroje import nastroje


@cl.on_chat_start
async def start():
    """Inicializuje chat a nastaví real-time klienta."""
    await cl.Message(content="Ahoj! Som tu. Stlač `P` pre rozprávanie!").send()
    # Nastavenie klienta pomocou importovanej funkcie a nástrojov
    await nastav_realtime_klienta(nastroje)


@cl.on_message
async def on_message(sprava: cl.Message):
    """Spracuje textovú správu od používateľa."""
    # Získanie klienta zo session
    klient_realneho_casu: KlientRealnehoCasu = cl.user_session.get("klient_realneho_casu")

    if klient_realneho_casu and klient_realneho_casu.je_pripojeny():
        # TODO: Skúsiť spracovanie obrázkov s message.elements
        # Odoslanie textového obsahu správy
        await klient_realneho_casu.posli_obsah_spravy_pouzivatela(
            [{"type": "input_text", "text": sprava.content}]
        )
    else:
        await cl.Message(
            content="Prosím, aktivujte hlasový režim pred odoslaním správ!"
        ).send()


@cl.on_audio_start
async def on_audio_start():
    """Spracuje začiatok nahrávania audia."""
    try:
        klient_realneho_casu: KlientRealnehoCasu = cl.user_session.get("klient_realneho_casu")
        if not klient_realneho_casu:
             logger.error("Real-time klient nebol inicializovaný v session.")
             await cl.ErrorMessage(content="Chyba: Real-time klient nie je dostupný.").send()
             return False

        # Pripojenie klienta, ak ešte nie je pripojený
        if not klient_realneho_casu.je_pripojeny():
            await klient_realneho_casu.pripoj()
            logger.info("Pripojené k real-time API")
        else:
             logger.info("Real-time klient je už pripojený.")

        # TODO: Možno bude potrebné znovu vytvoriť položky na obnovenie kontextu
        # klient_realneho_casu.vytvor_polozku_konverzacie(polozka)
        return True
    except Exception as e:
        logger.error(f"Chyba pri pripájaní k real-time API: {traceback.format_exc()}")
        await cl.ErrorMessage(
            content=f"Nepodarilo sa pripojiť k real-time API: {e}"
        ).send()
        return False


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Spracuje prichádzajúci audio chunk."""
    klient_realneho_casu: KlientRealnehoCasu = cl.user_session.get("klient_realneho_casu")
    if klient_realneho_casu and klient_realneho_casu.je_pripojeny():
        # Pridanie audio dát do bufferu klienta
        await klient_realneho_casu.pridaj_vstupne_audio(chunk.data)
    else:
        # Logovanie, ak klient nie je pripojený, ale neposielame správu používateľovi
        logger.warning("Real-time klient nie je pripojený pri spracovaní audio chunku.")


@cl.on_audio_end
@cl.on_chat_end
@cl.on_stop
async def on_end():
    """Spracuje ukončenie audia, chatu alebo zastavenie aplikácie."""
    klient_realneho_casu: KlientRealnehoCasu = cl.user_session.get("klient_realneho_casu")
    if klient_realneho_casu and klient_realneho_casu.je_pripojeny():
        logger.info("Odpojuje sa real-time klient.")
        await klient_realneho_casu.odpoj()
