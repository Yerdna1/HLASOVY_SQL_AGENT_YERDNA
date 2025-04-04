"""Pomocné funkcie pre spracovanie dát v reálnom čase."""

import os
import base64
import numpy as np
from chainlit.config import config as chainlit_config


def ziskaj_instrukcie_realneho_casu():
    """Načíta inštrukcie pre real-time spracovanie z textového súboru."""
    aktualny_adresar = os.path.dirname(os.path.abspath(__file__))
    # Cesta k inštrukciám, predpokladáme, že sú v settings
    instrukcie_cesta = os.path.join(aktualny_adresar, "../settings/zakladne_instrukcie.txt")

    try:
        with open(instrukcie_cesta, "r", encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Chyba: Súbor s inštrukciami nebol nájdený: {instrukcie_cesta}")
        return "Predvolené inštrukcie: Buď nápomocný asistent." # Fallback
    except Exception as e:
        print(f"Chyba pri načítaní inštrukcií: {e}")
        return "Predvolené inštrukcie: Buď nápomocný asistent."


def float_na_16bit_pcm(float32_pole):
    """
    Konvertuje numpy pole float32 amplitúdových dát na numpy pole vo formáte int16.
    :param float32_pole: numpy pole float32
    :return: numpy pole int16
    """
    int16_pole = np.clip(float32_pole, -1, 1) * 32767
    return int16_pole.astype(np.int16)


def base64_na_buffer_pola(base64_retazec):
    """
    Konvertuje base64 reťazec na numpy pole buffer.
    :param base64_retazec: base64 kódovaný reťazec
    :return: numpy pole uint8
    """
    binarne_data = base64.b64decode(base64_retazec)
    return np.frombuffer(binarne_data, dtype=np.uint8)


def buffer_pola_na_base64(buffer_pola):
    """
    Konvertuje numpy pole buffer na base64 reťazec.
    :param buffer_pola: numpy pole
    :return: base64 kódovaný reťazec
    """
    if buffer_pola.dtype == np.float32:
        buffer_pola = float_na_16bit_pcm(buffer_pola)
        data_na_kodovanie = buffer_pola.tobytes()
    elif buffer_pola.dtype == np.int16:
        data_na_kodovanie = buffer_pola.tobytes()
    else:
        # Predpokladáme, že už sú to bajty alebo ich možno konvertovať
        try:
            data_na_kodovanie = buffer_pola.tobytes()
        except AttributeError:
             # Ak to nie je numpy pole s tobytes(), skúsime priamo
             data_na_kodovanie = bytes(buffer_pola)


    return base64.b64encode(data_na_kodovanie).decode("utf-8")

# Predvolená vzorkovacia frekvencia z konfigurácie Chainlit
PREDVOLENA_FREKVENCIA = chainlit_config.features.audio.sample_rate
