"""Klient pre real-time komunikáciu s AI modelom."""

import asyncio
import json
import os # Pridané pre prácu s cestami
from datetime import datetime
import numpy as np
import base64

# Import preložených častí
from .event_handler import SpracovatelUdalostiRealnehoCasu
from .api import APIRealnehoCasu
from .conversation import KonverzaciaRealnehoCasu
from .utils import ziskaj_instrukcie_realneho_casu, buffer_pola_na_base64, PREDVOLENA_FREKVENCIA
from apka.widgets.spolocne import zapisovac

# Definovanie cesty k log súboru
LOG_FILE_PATH = os.path.join("apka", "output", "conversation_log.jsonl")
# Zabezpečenie existencie adresára (aj keď sme ho vytvorili externe)
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)


class KlientRealnehoCasu(SpracovatelUdalostiRealnehoCasu):
    def __init__(self, url=None, api_kluc=None):
        super().__init__()
        self.log_file_path = LOG_FILE_PATH # Uloženie cesty pre inštanciu
        # Predvolená konfigurácia relácie
        self.predvolena_konfiguracia_relacie = {
            "modalities": ["text", "audio"],
            "instructions": ziskaj_instrukcie_realneho_casu(),
            "voice": "shimmer",
            "input_audio_format": "pcm16", # Kľúč API
            "output_audio_format": "pcm16", # Kľúč API
            "input_audio_transcription": {"model": "whisper-1"}, # Kľúče API
            "turn_detection": {"type": "server_vad"}, # Kľúče API
            "tools": [], # Kľúč API
            "tool_choice": "auto", # Kľúč API
            "temperature": 0.8,
            "max_response_output_tokens": 4096,
        }
        self.konfiguracia_relacie = {}
        self.modely_prepisovania = [{"model": "whisper-1"}]
        self.predvolena_konfiguracia_server_vad = {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 200,
        }
        # Inštancie API a Konverzácie
        self.realtime_api = APIRealnehoCasu(url=url, api_kluc=api_kluc)
        self.konverzacia = KonverzaciaRealnehoCasu()
        self._resetuj_konfiguraciu()
        self._pridaj_spracovatelov_api_udalosti()

    def _resetuj_konfiguraciu(self):
        """Resetuje konfiguráciu klienta."""
        self.relacia_vytvorena = False
        self.nastroje = {}
        self.konfiguracia_relacie = self.predvolena_konfiguracia_relacie.copy()
        self.vstupny_audio_buffer = bytearray()
        return True

    def _pridaj_spracovatelov_api_udalosti(self):
        """Pridá interných spracovateľov pre udalosti z API."""
        self.realtime_api.on("client.*", self._zaznamenaj_udalost)
        self.realtime_api.on("server.*", self._zaznamenaj_udalost)
        self.realtime_api.on("server.session.created", self._pri_vytvoreni_relacie)
        # Udalosti spracované priamo Konverzáciou
        self.realtime_api.on("server.response.created", self._spracuj_udalost_konverzacie)
        self.realtime_api.on("server.response.output_item.added", self._spracuj_udalost_konverzacie)
        self.realtime_api.on("server.response.content_part.added", self._spracuj_udalost_konverzacie)
        self.realtime_api.on("server.input_audio_buffer.speech_started", self._pri_zaciatku_reci)
        self.realtime_api.on("server.input_audio_buffer.speech_stopped", self._pri_konci_reci)
        self.realtime_api.on("server.conversation.item.created", self._pri_vytvoreni_polozky)
        self.realtime_api.on("server.conversation.item.truncated", self._spracuj_udalost_konverzacie)
        self.realtime_api.on("server.conversation.item.deleted", self._spracuj_udalost_konverzacie)
        self.realtime_api.on(
            "server.conversation.item.input_audio_transcription.completed",
            self._spracuj_udalost_konverzacie,
        )
        # Delty spracované Konverzáciou
        self.realtime_api.on("server.response.audio_transcript.delta", self._spracuj_udalost_konverzacie)
        self.realtime_api.on("server.response.audio.delta", self._spracuj_udalost_konverzacie)
        self.realtime_api.on("server.response.text.delta", self._spracuj_udalost_konverzacie)
        self.realtime_api.on("server.response.function_call_arguments.delta", self._spracuj_udalost_konverzacie)
        # Špeciálne spracovanie pre dokončenie položky
        self.realtime_api.on("server.response.output_item.done", self._pri_dokonceni_vystupnej_polozky)

    def _log_event(self, event_type: str, data: dict):
        """Zapíše štruktúrovanú udalosť do log súboru."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            zapisovac.error(f"Chyba pri zápise do log súboru {self.log_file_path}: {e}")


    def _zaznamenaj_udalost(self, udalost):
        """Zaznamená RAW udalosť klienta alebo servera (môže byť príliš verbose)."""
        udalost_realneho_casu = {
            "time": datetime.utcnow().isoformat(),
            "source": "client" if udalost["type"].startswith("client.") else "server",
            "event": udalost,
        }
        self.odosli("realtime.event", udalost_realneho_casu)

    def _pri_vytvoreni_relacie(self, udalost):
        """Spracuje udalosť vytvorenia relácie."""
        self.relacia_vytvorena = True

    def _spracuj_udalost_konverzacie(self, udalost, *args):
        """Spracuje udalosť pomocou inštancie Konverzacie."""
        polozka, delta = self.konverzacia.spracuj_udalost(udalost, *args)
        if polozka:
            # Odošle aktualizovanú položku a deltu
            self.odosli("conversation.updated", {"item": polozka, "delta": delta})
        return polozka, delta

    def _pri_zaciatku_reci(self, udalost):
        """Spracuje začiatok reči."""
        self._spracuj_udalost_konverzacie(udalost)
        # Odošle udalosť prerušenia (napr. na zastavenie prehrávania)
        self.odosli("conversation.interrupted", udalost)

    def _pri_konci_reci(self, udalost):
        """Spracuje koniec reči, odovzdá audio buffer."""
        self._spracuj_udalost_konverzacie(udalost, self.vstupny_audio_buffer)

    def _pri_vytvoreni_polozky(self, udalost):
        """Spracuje vytvorenie novej položky konverzácie."""
        polozka, delta = self._spracuj_udalost_konverzacie(udalost)
        if polozka:
            self.odosli("conversation.item.appended", {"item": polozka})
            if polozka.get("status") == "completed":
                self.odosli("conversation.item.completed", {"item": polozka})

    async def _pri_dokonceni_vystupnej_polozky(self, udalost):
        """Spracuje dokončenie výstupnej položky, potenciálne volá nástroj."""
        polozka, delta = self._spracuj_udalost_konverzacie(udalost)
        if polozka and polozka.get("status") == "completed":
            self.odosli("conversation.item.completed", {"item": polozka})
            # Logovanie dokončenej správy asistenta
            if polozka.get("type") == "message" and polozka.get("role") == "assistant":
                 self._log_event("assistant_message_completed", {"message_id": polozka.get("id"), "content": polozka.get("content")})

        # Ak je dokončená položka volanie nástroja, zavoláme ho
        if polozka and polozka.get("formatted", {}).get("tool"):
            # Logovanie začiatku volania nástroja bude v _zavolaj_nastroj
            await self._zavolaj_nastroj(polozka["formatted"]["tool"])
        # TODO: Pridať logovanie pre iné typy dokončených položiek ak je potrebné

    async def _zavolaj_nastroj(self, nastroj_data):
        """Zavolá zaregistrovaný nástroj s danými argumentmi."""
        nazov_nastroja = nastroj_data.get("name")
        argumenty_str = nastroj_data.get("arguments", "{}")
        id_volania = nastroj_data.get("call_id")

        # Logovanie začiatku volania nástroja
        self._log_event("tool_call_started", {
            "call_id": id_volania,
            "tool_name": nazov_nastroja,
            "arguments": argumenty_str # Logujeme string, aby sme sa vyhli chybám pri parsovaní tu
        })

        try:
            # Pokus o parsovanie JSON argumentov
            try:
                json_argumenty = json.loads(argumenty_str)
            except json.JSONDecodeError as json_err:
                # Špecifické logovanie a chyba pre neplatný JSON
                error_message = f"Neplatný JSON v argumentoch nástroja: {json_err}. Prijaté: {argumenty_str}"
                zapisovac.error(error_message)
                self._log_event("tool_call_ended", {
                    "call_id": id_volania,
                    "tool_name": nazov_nastroja,
                    "error": error_message,
                    "raw_arguments": argumenty_str # Pridáme surové argumenty pre debugovanie
                })
                # Odoslanie chyby späť ako výstup funkcie
                await self.realtime_api.posli(
                    "conversation.item.create",
                    {
                        "item": {
                            "type": "function_call_output",
                            "call_id": id_volania,
                            "output": json.dumps({"error": "Invalid JSON arguments received from model."}),
                        }
                    },
                )
                # Nevyžadujeme novú odpoveď, LLM by mal opraviť volanie nástroja
                return # Ukončíme spracovanie tohto volania

            # Pokračujeme, ak bol JSON platný
            konfiguracia_nastroja = self.nastroje.get(nazov_nastroja)
            if not konfiguracia_nastroja:
                raise Exception(f'Nástroj "{nazov_nastroja}" nebol pridaný')
            # Zavolanie asynchrónneho spracovateľa nástroja
            vysledok = await konfiguracia_nastroja["handler"](**json_argumenty)

            # Logovanie úspešného výsledku nástroja
            log_data_success = {
                 "call_id": id_volania,
                 "tool_name": nazov_nastroja,
                 "result": vysledok # Ukladáme celý výsledok (môže obsahovať 'message' a 'image_path')
            }
            # Ak nástroj vrátil SQL (predpoklad pre databaza.py)
            if isinstance(vysledok, dict) and "sql_query" in vysledok:
                 log_data_success["sql_query"] = vysledok["sql_query"]
                 log_data_success["sql_explanation"] = vysledok.get("explanation", "")
            # Ak nástroj vrátil cestu k obrázku (predpoklad pre graf.py)
            if isinstance(vysledok, dict) and "image_path" in vysledok:
                 log_data_success["image_path"] = vysledok["image_path"]

            self._log_event("tool_call_ended", log_data_success)

            # Odoslanie výsledku späť ako výstup funkcie
            await self.realtime_api.posli(
                "conversation.item.create",
                {
                    "item": {
                        "type": "function_call_output",
                        "call_id": id_volania,
                        "output": json.dumps(vysledok), # Odosielame pôvodný výsledok
                    }
                },
            )
        except Exception as e:
            error_message = str(e)
            zapisovac.error(f"Chyba pri volaní nástroja: {error_message}")
            # Logovanie chyby nástroja
            self._log_event("tool_call_ended", {
                "call_id": id_volania,
                "tool_name": nazov_nastroja,
                "error": error_message
            })
            # Odoslanie chyby späť ako výstup funkcie
            await self.realtime_api.posli(
                "conversation.item.create",
                {
                    "item": {
                        "type": "function_call_output",
                        "call_id": id_volania,
                        "output": json.dumps({"error": error_message}),
                    }
                },
            )
        # Po volaní nástroja (úspešnom aj neúspešnom) vyžiadame novú odpoveď
        await self.vytvor_odpoved()

    # --- Verejné metódy klienta ---

    def je_pripojeny(self):
        """Skontroluje, či je klient pripojený k API."""
        return self.realtime_api.je_pripojeny()

    def reset(self):
        """Resetuje klienta do počiatočného stavu."""
        self.odpoj()
        self.realtime_api.vymaz_spracovatelov_udalosti()
        self._resetuj_konfiguraciu()
        self._pridaj_spracovatelov_api_udalosti()
        return True

    async def pripoj(self):
        """Pripojí klienta k API a aktualizuje reláciu."""
        if self.je_pripojeny():
            raise Exception("Už pripojené, najprv použite .odpoj()")
        await self.realtime_api.pripoj()
        await self.aktualizuj_relaciu()
        return True

    async def pockaj_na_vytvorenie_relacie(self):
        """Čaká, kým server nepotvrdí vytvorenie relácie."""
        if not self.je_pripojeny():
            raise Exception("Nie je pripojené, najprv použite .pripoj()")
        while not self.relacia_vytvorena:
            await asyncio.sleep(0.001)
        return True

    async def odpoj(self):
        """Odpojí klienta od API."""
        self.relacia_vytvorena = False
        self.konverzacia.vymaz()
        if self.realtime_api.je_pripojeny():
            await self.realtime_api.odpoj()

    def ziskaj_typ_detekcie_tahu(self):
        """Získa typ detekcie konca ťahu z konfigurácie."""
        return self.konfiguracia_relacie.get("turn_detection", {}).get("type")

    async def pridaj_nastroj(self, definicia, spracovatel):
        """Pridá nástroj (funkciu), ktorý môže AI volať."""
        nazov = definicia.get("name")
        if not nazov:
            raise Exception("Chýba názov nástroja v definícii")
        if nazov in self.nastroje:
            raise Exception(
                f'Nástroj "{nazov}" už bol pridaný. Použite .odstran_nastroj("{nazov}") pred opätovným pridaním.'
            )
        if not callable(spracovatel):
            raise Exception(f'Spracovateľ nástroja "{nazov}" musí byť funkcia')
        self.nastroje[nazov] = {"definition": definicia, "handler": spracovatel}
        # Aktualizujeme reláciu na serveri s novým nástrojom
        await self.aktualizuj_relaciu()
        return self.nastroje[nazov]

    async def odstran_nastroj(self, nazov):
        """Odstráni nástroj."""
        if nazov not in self.nastroje:
            raise Exception(f'Nástroj "{nazov}" neexistuje, nedá sa odstrániť.')
        del self.nastroje[nazov]
        # Aktualizujeme reláciu na serveri bez odstráneného nástroja
        await self.aktualizuj_relaciu()
        return True

    async def zmaz_polozku(self, id_polozky):
        """Požiada server o zmazanie položky konverzácie."""
        await self.realtime_api.posli("conversation.item.delete", {"item_id": id_polozky})
        return True

    async def aktualizuj_relaciu(self, **kwargs):
        """Aktualizuje konfiguráciu relácie na serveri."""
        self.konfiguracia_relacie.update(kwargs)
        # Získanie definícií všetkých aktuálne pridaných nástrojov
        pouzivane_nastroje = [
            {**definicia_nastroja, "type": "function"}
            for definicia_nastroja in self.konfiguracia_relacie.get("tools", [])
        ] + [{**self.nastroje[kluc]["definition"], "type": "function"} for kluc in self.nastroje]
        # Vytvorenie finálnej konfigurácie relácie na odoslanie
        relacia_data = {**self.konfiguracia_relacie, "tools": pouzivane_nastroje}
        if self.realtime_api.je_pripojeny():
            await self.realtime_api.posli("session.update", {"session": relacia_data})
        return True

    async def vytvor_polozku_konverzacie(self, polozka):
        """Odošle požiadavku na vytvorenie novej položky konverzácie."""
        await self.realtime_api.posli("conversation.item.create", {"item": polozka})

    async def posli_obsah_spravy_pouzivatela(self, obsah=[]):
        """Odošle obsah správy od používateľa (text, audio) a vyžiada odpoveď."""
        if obsah:
            # Logovanie odoslanej správy používateľa
            self._log_event("user_message_sent", {"content": obsah})

            # Konverzia audio dát na base64 pred odoslaním
            processed_content = []
            for cast in obsah:
                 processed_cast = cast.copy() # Vytvoríme kópiu, aby sme neupravovali pôvodný obsah pre logovanie
                 if processed_cast["type"] == "input_audio":
                     if isinstance(processed_cast["audio"], (bytes, bytearray)):
                         processed_cast["audio"] = buffer_pola_na_base64(np.frombuffer(processed_cast["audio"], dtype=np.int16))
                     elif isinstance(processed_cast["audio"], np.ndarray):
                          processed_cast["audio"] = buffer_pola_na_base64(processed_cast["audio"])
                 processed_content.append(processed_cast)


            await self.realtime_api.posli(
                "conversation.item.create",
                {
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": processed_content, # Odosielame spracovaný obsah
                    }
                },
            )
        # Po odoslaní správy používateľa vždy vyžiadame odpoveď
        await self.vytvor_odpoved()
        return True

    async def pridaj_vstupne_audio(self, buffer_pola):
        """Pridá časť vstupného audia do bufferu a odošle ho."""
        if len(buffer_pola) > 0:
             # Konverzia numpy poľa alebo bajtov na base64
             if isinstance(buffer_pola, np.ndarray):
                  audio_base64 = buffer_pola_na_base64(buffer_pola)
             elif isinstance(buffer_pola, (bytes, bytearray)):
                  # Predpokladáme správny formát (napr. int16)
                  audio_base64 = base64.b64encode(buffer_pola).decode('utf-8')
             else:
                  raise TypeError("Nepodporovaný typ pre audio buffer")

             await self.realtime_api.posli(
                 "input_audio_buffer.append",
                 {
                     "audio": audio_base64,
                 },
             )
             # Pridanie surových bajtov do lokálneho bufferu
             if isinstance(buffer_pola, np.ndarray):
                  self.vstupny_audio_buffer.extend(buffer_pola.tobytes())
             else:
                  self.vstupny_audio_buffer.extend(buffer_pola)
        return True

    async def vytvor_odpoved(self):
        """Vyžiada od servera vytvorenie odpovede."""
        # Ak sa používa manuálna detekcia konca ťahu, potvrdíme buffer pred vyžiadaním odpovede
        if self.ziskaj_typ_detekcie_tahu() is None and len(self.vstupny_audio_buffer) > 0:
            await self.realtime_api.posli("input_audio_buffer.commit")
            # Zaradíme aktuálny buffer do fronty pre Konverzáciu
            self.konverzacia.zarad_vstupne_audio_do_fronty(self.vstupny_audio_buffer)
            self.vstupny_audio_buffer = bytearray()
        # Vyžiadanie vytvorenia odpovede
        await self.realtime_api.posli("response.create")
        return True

    async def zrus_odpoved(self, id_polozky=None, pocet_vzoriek=0):
        """Zruší generovanie aktuálnej odpovede."""
        if not id_polozky:
            # Jednoduché zrušenie bez skrátenia audia
            await self.realtime_api.posli("response.cancel")
            return {"item": None}
        else:
            # Zrušenie so skrátením audia na konkrétnej položke
            polozka = self.konverzacia.ziskaj_polozku(id_polozky)
            if not polozka:
                raise Exception(f'Nebolo možné nájsť položku "{id_polozky}"')
            if polozka.get("type") != "message":
                raise Exception('Metódu zrus_odpoved možno použiť len pre správy typu "message"')
            if polozka.get("role") != "assistant":
                raise Exception('Metódu zrus_odpoved možno použiť len pre správy s rolou "assistant"')

            await self.realtime_api.posli("response.cancel")
            # Nájdenie indexu audio obsahu
            audio_index = next((i for i, c in enumerate(polozka.get("content", [])) if c.get("type") == "audio"), -1)
            if audio_index == -1:
                zapisovac.warning(f"Nebolo možné nájsť audio obsah na položke {id_polozky} pre zrušenie.")
                # Aj tak vrátime položku, keďže zrušenie bolo odoslané
                return {"item": polozka}

            # Odoslanie požiadavky na skrátenie audia
            await self.realtime_api.posli(
                "conversation.item.truncate",
                {
                    "item_id": id_polozky,
                    "content_index": audio_index,
                    "audio_end_ms": int((pocet_vzoriek / PREDVOLENA_FREKVENCIA) * 1000),
                },
            )
            return {"item": polozka}

    async def pockaj_na_dalsiu_polozku(self):
        """Asynchrónne čaká na pridanie ďalšej položky do konverzácie."""
        udalost = await self.pockaj_na_dalsiu("conversation.item.appended")
        return {"item": udalost["item"]}

    async def pockaj_na_dalsiu_dokoncenu_polozku(self):
        """Asynchrónne čaká na dokončenie ďalšej položky konverzácie."""
        udalost = await self.pockaj_na_dalsiu("conversation.item.completed")
        return {"item": udalost["item"]}
