"""Správa stavu konverzácie v reálnom čase."""

from collections import defaultdict
# Import preložených utilít a loggera
from .utils import base64_na_buffer_pola, PREDVOLENA_FREKVENCIA
from apka.widgets.spolocne import zapisovac

class KonverzaciaRealnehoCasu:
    # Predvolená frekvencia z utils
    predvolena_frekvencia = PREDVOLENA_FREKVENCIA

    # Mapovanie typov udalostí na spracovateľské metódy
    SpracovateliaUdalosti = {
        "conversation.item.created": lambda self, udalost: self._spracuj_vytvorenie_polozky(udalost),
        "conversation.item.truncated": lambda self, udalost: self._spracuj_skratenie_polozky(udalost),
        "conversation.item.deleted": lambda self, udalost: self._spracuj_zmazanie_polozky(udalost),
        "conversation.item.input_audio_transcription.completed": lambda self, udalost: self._spracuj_dokoncenie_prepisu_vstupneho_audia(
            udalost
        ),
        "input_audio_buffer.speech_started": lambda self, udalost: self._spracuj_zaciatok_rec(udalost),
        # Potrebuje buffer ako argument
        "input_audio_buffer.speech_stopped": lambda self, udalost, vstupny_audio_buffer: self._spracuj_koniec_reci(
            udalost, vstupny_audio_buffer
        ),
        "response.created": lambda self, udalost: self._spracuj_vytvorenie_odpovede(udalost),
        "response.output_item.added": lambda self, udalost: self._spracuj_pridanie_vystupnej_polozky(udalost),
        "response.output_item.done": lambda self, udalost: self._spracuj_dokoncenie_vystupnej_polozky(udalost),
        "response.content_part.added": lambda self, udalost: self._spracuj_pridanie_casti_obsahu(udalost),
        "response.audio_transcript.delta": lambda self, udalost: self._spracuj_delta_prepis_audia(udalost),
        "response.audio.delta": lambda self, udalost: self._spracuj_delta_audia(udalost),
        "response.text.delta": lambda self, udalost: self._spracuj_delta_textu(udalost),
        "response.function_call_arguments.delta": lambda self, udalost: self._spracuj_delta_argumentov_volania_funkcie(
            udalost
        ),
    }

    def __init__(self):
        self.vymaz()

    def vymaz(self):
        """Vymaže stav konverzácie."""
        self.vyhladavanie_poloziek = {}
        self.polozky = []
        self.vyhladavanie_odpovedi = {}
        self.odpovede = []
        self.polozky_reci_vo_fronte = {}
        self.polozky_prepisu_vo_fronte = {}
        self.vstupne_audio_vo_fronte = None

    def zarad_vstupne_audio_do_fronty(self, vstupne_audio):
        """Zaradí vstupný audio buffer do fronty."""
        self.vstupne_audio_vo_fronte = vstupne_audio

    def spracuj_udalost(self, udalost, *args):
        """Spracuje prichádzajúcu udalosť servera."""
        spracovatel_udalosti = self.SpracovateliaUdalosti.get(udalost["type"])
        if not spracovatel_udalosti:
            raise Exception(f"Chýbajúci spracovateľ udalosti konverzácie pre {udalost['type']}")
        return spracovatel_udalosti(self, udalost, *args)

    def ziskaj_polozku(self, id_polozky):
        """Získa položku konverzácie podľa ID."""
        return self.vyhladavanie_poloziek.get(id_polozky)

    def ziskaj_polozky(self):
        """Vráti kópiu zoznamu všetkých položiek konverzácie."""
        return self.polozky[:]

    # --- Interné metódy spracovania udalostí ---

    def _spracuj_vytvorenie_polozky(self, udalost):
        polozka_data = udalost["item"]
        nova_polozka = polozka_data.copy()
        if nova_polozka["id"] not in self.vyhladavanie_poloziek:
            self.vyhladavanie_poloziek[nova_polozka["id"]] = nova_polozka
            self.polozky.append(nova_polozka)
        # Inicializácia formátovaných dát
        nova_polozka["formatted"] = {"audio": [], "text": "", "transcript": ""} # Kľúč 'formatted' je súčasťou API
        # Spracovanie čakajúcich dát
        if nova_polozka["id"] in self.polozky_reci_vo_fronte:
            queued_speech_info = self.polozky_reci_vo_fronte[nova_polozka["id"]]
            # Ensure 'audio' key exists, though _spracuj_koniec_reci should guarantee it
            nova_polozka["formatted"]["audio"] = queued_speech_info.get("audio", [])
            del self.polozky_reci_vo_fronte[nova_polozka["id"]]
        if "content" in nova_polozka: # Kľúč 'content' je súčasťou API
            textovy_obsah = [c for c in nova_polozka["content"] if c["type"] in ["text", "input_text"]] # Kľúče 'type', 'text', 'input_text' sú súčasťou API
            for obsah in textovy_obsah:
                nova_polozka["formatted"]["text"] += obsah["text"]
        if nova_polozka["id"] in self.polozky_prepisu_vo_fronte:
            nova_polozka["formatted"]["transcript"] = self.polozky_prepisu_vo_fronte[nova_polozka["id"]]["transcript"]
            del self.polozky_prepisu_vo_fronte[nova_polozka["id"]]
        # Nastavenie stavu podľa typu a roly
        if nova_polozka["type"] == "message": # Kľúč 'type' je súčasťou API
            if nova_polozka["role"] == "user": # Kľúč 'role' je súčasťou API
                nova_polozka["status"] = "completed" # Kľúč 'status' je súčasťou API
                if self.vstupne_audio_vo_fronte:
                    nova_polozka["formatted"]["audio"] = self.vstupne_audio_vo_fronte
                    self.vstupne_audio_vo_fronte = None
            else: # assistant
                nova_polozka["status"] = "in_progress" # Kľúč 'status' je súčasťou API
        elif nova_polozka["type"] == "function_call": # Kľúč 'type' je súčasťou API
            nova_polozka["formatted"]["tool"] = { # Kľúč 'tool' je súčasťou API
                "type": "function", # Kľúč 'type' je súčasťou API
                "name": nova_polozka["name"], # Kľúč 'name' je súčasťou API
                "call_id": nova_polozka["call_id"], # Kľúč 'call_id' je súčasťou API
                "arguments": "", # Kľúč 'arguments' je súčasťou API
            }
            nova_polozka["status"] = "in_progress" # Kľúč 'status' je súčasťou API
        elif nova_polozka["type"] == "function_call_output": # Kľúč 'type' je súčasťou API
            nova_polozka["status"] = "completed" # Kľúč 'status' je súčasťou API
            nova_polozka["formatted"]["output"] = nova_polozka["output"] # Kľúč 'output' je súčasťou API
        return nova_polozka, None

    def _spracuj_skratenie_polozky(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        koniec_audia_ms = udalost["audio_end_ms"]
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            zapisovac.warning(f'item.truncated: Položka "{id_polozky}" nenájdená')
            return None, None
        koncovy_index = (koniec_audia_ms * self.predvolena_frekvencia) // 1000
        polozka["formatted"]["transcript"] = ""
        polozka["formatted"]["audio"] = polozka["formatted"]["audio"][:koncovy_index]
        return polozka, None

    def _spracuj_zmazanie_polozky(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            zapisovac.warning(f'item.deleted: Položka "{id_polozky}" nenájdená')
            return None, None # Návrat None, ak položka neexistuje
        del self.vyhladavanie_poloziek[polozka["id"]]
        # Odstránenie zo zoznamu môže byť neefektívne, zvážiť inú štruktúru ak je to problém
        try:
            self.polozky.remove(polozka)
        except ValueError:
             zapisovac.warning(f'item.deleted: Položka "{id_polozky}" už nebola v zozname polozky.')
        return polozka, None

    def _spracuj_dokoncenie_prepisu_vstupneho_audia(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        index_obsahu = udalost["content_index"]
        prepis = udalost["transcript"]
        formatovany_prepis = prepis or " "
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            # Ak položka ešte neexistuje, uložíme prepis do fronty
            self.polozky_prepisu_vo_fronte[id_polozky] = {"transcript": formatovany_prepis}
            return None, None
        # Aktualizácia existujúcej položky
        try:
            polozka["content"][index_obsahu]["transcript"] = prepis
            polozka["formatted"]["transcript"] = formatovany_prepis
        except (IndexError, KeyError) as e:
             zapisovac.error(f"Chyba pri aktualizácii prepisu pre položku {id_polozky}: {e}")
             # Prípadne vytvoriť content, ak chýba? Závisí od očakávaného správania API.
        return polozka, {"transcript": prepis} # Kľúč 'transcript' je súčasťou API

    def _spracuj_zaciatok_rec(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        zaciatok_audia_ms = udalost["audio_start_ms"] # Kľúč 'audio_start_ms' je súčasťou API
        # Uloženie informácie o začiatku reči do fronty
        self.polozky_reci_vo_fronte[id_polozky] = {"audio_start_ms": zaciatok_audia_ms}
        return None, None

    def _spracuj_koniec_reci(self, udalost, vstupny_audio_buffer):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        koniec_audia_ms = udalost["audio_end_ms"] # Kľúč 'audio_end_ms' je súčasťou API
        # Získanie informácií o reči z fronty
        info_o_reci = self.polozky_reci_vo_fronte.get(id_polozky)
        if not info_o_reci:
             zapisovac.warning(f"speech_stopped: Nenašli sa informácie o začiatku reči pre položku {id_polozky}")
             return None, None
        info_o_reci["audio_end_ms"] = koniec_audia_ms
        # Extrahovanie audio segmentu, ak je dostupný buffer
        if vstupny_audio_buffer:
            zaciatocny_index = (info_o_reci["audio_start_ms"] * self.predvolena_frekvencia) // 1000
            koncovy_index = (info_o_reci["audio_end_ms"] * self.predvolena_frekvencia) // 1000
            # Uložíme audio dáta ako zoznam bajtov pre konzistenciu s _spracuj_delta_audia
            info_o_reci["audio"] = [vstupny_audio_buffer[zaciatocny_index:koncovy_index]]
        else:
             info_o_reci["audio"] = [] # Prázdny zoznam, ak buffer nie je dostupný

        # Ak položka už existuje, aktualizujeme ju
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if polozka:
             polozka["formatted"]["audio"] = info_o_reci["audio"]
             # Odstránime zo fronty až po úspešnej aktualizácii
             if id_polozky in self.polozky_reci_vo_fronte:
                  del self.polozky_reci_vo_fronte[id_polozky]

        return None, None # Táto udalosť priamo nemodifikuje položku pre dispatch

    def _spracuj_vytvorenie_odpovede(self, udalost):
        odpoved = udalost["response"] # Kľúč 'response' je súčasťou API
        if odpoved["id"] not in self.vyhladavanie_odpovedi:
            self.vyhladavanie_odpovedi[odpoved["id"]] = odpoved
            self.odpovede.append(odpoved)
        return None, None

    def _spracuj_pridanie_vystupnej_polozky(self, udalost):
        id_odpovede = udalost["response_id"] # Kľúč 'response_id' je súčasťou API
        polozka_data = udalost["item"] # Kľúč 'item' je súčasťou API
        odpoved = self.vyhladavanie_odpovedi.get(id_odpovede)
        if not odpoved:
            zapisovac.warning(f'response.output_item.added: Odpoveď "{id_odpovede}" nenájdená')
            return None, None
        # Pridanie ID položky do zoznamu výstupov odpovede
        if "output" not in odpoved: # Kľúč 'output' je súčasťou API
             odpoved["output"] = []
        odpoved["output"].append(polozka_data["id"])
        return None, None

    def _spracuj_dokoncenie_vystupnej_polozky(self, udalost):
        polozka_data = udalost["item"]
        if not polozka_data:
            raise Exception('response.output_item.done: Chýba "item"')
        najdena_polozka = self.vyhladavanie_poloziek.get(polozka_data["id"])
        if not najdena_polozka:
            zapisovac.warning(f'response.output_item.done: Položka "{polozka_data["id"]}" nenájdená')
            return None, None
        najdena_polozka["status"] = polozka_data.get("status", "completed") # Kľúč 'status' je súčasťou API, pridanie defaultu
        return najdena_polozka, None

    def _spracuj_pridanie_casti_obsahu(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        cast = udalost["part"] # Kľúč 'part' je súčasťou API
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            zapisovac.warning(f'response.content_part.added: Položka "{id_polozky}" nenájdená')
            return None, None
        if "content" not in polozka: # Kľúč 'content' je súčasťou API
            polozka["content"] = []
        polozka["content"].append(cast)
        return polozka, None

    def _spracuj_delta_prepis_audia(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        index_obsahu = udalost["content_index"] # Kľúč 'content_index' je súčasťou API
        delta = udalost["delta"] # Kľúč 'delta' je súčasťou API
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            zapisovac.warning(f'response.audio_transcript.delta: Položka "{id_polozky}" nenájdená')
            return None, None
        try:
            # Zaistenie existencie contentu a indexu
            if "content" not in polozka: polozka["content"] = []
            while len(polozka["content"]) <= index_obsahu: polozka["content"].append({"type": "audio_transcript", "transcript": ""}) # Doplnenie chýbajúcich častí
            if "transcript" not in polozka["content"][index_obsahu]: polozka["content"][index_obsahu]["transcript"] = ""

            polozka["content"][index_obsahu]["transcript"] += delta
            polozka["formatted"]["transcript"] += delta
        except (IndexError, KeyError, TypeError) as e:
             zapisovac.error(f"Chyba pri spracovaní audio_transcript.delta pre položku {id_polozky}: {e}")
             return None, None # Nevrátime deltu, ak nastala chyba
        return polozka, {"transcript": delta} # Kľúč 'transcript' je súčasťou API

    def _spracuj_delta_audia(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        # index_obsahu = udalost["content_index"] # Tento index sa tu zvyčajne nepoužíva priamo pre audio dáta
        delta = udalost["delta"] # Kľúč 'delta' je súčasťou API
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            # Ak položka neexistuje, môžeme audio dočasne uložiť, podobne ako pri speech_stopped
            # Alebo jednoducho logovať varovanie, závisí od očakávaného správania
            zapisovac.debug(f'response.audio.delta: Položka "{id_polozky}" nenájdená, delta sa ignoruje.')
            return None, None
        try:
            buffer_pola = base64_na_buffer_pola(delta)
            pridane_hodnoty = buffer_pola.tobytes()
            # Pridáme bajty do zoznamu v formatted audio
            if "formatted" not in polozka: polozka["formatted"] = {"audio": [], "text": "", "transcript": ""}
            if "audio" not in polozka["formatted"]: polozka["formatted"]["audio"] = []
            polozka["formatted"]["audio"].append(pridane_hodnoty)
        except Exception as e:
             zapisovac.error(f"Chyba pri spracovaní audio.delta pre položku {id_polozky}: {e}")
             return None, None # Nevrátime deltu, ak nastala chyba
        return polozka, {"audio": pridane_hodnoty} # Kľúč 'audio' je súčasťou API

    def _spracuj_delta_textu(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        index_obsahu = udalost["content_index"] # Kľúč 'content_index' je súčasťou API
        delta = udalost["delta"] # Kľúč 'delta' je súčasťou API
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            zapisovac.warning(f'response.text.delta: Položka "{id_polozky}" nenájdená')
            return None, None
        try:
             # Zaistenie existencie contentu a indexu
            if "content" not in polozka: polozka["content"] = []
            while len(polozka["content"]) <= index_obsahu: polozka["content"].append({"type": "text", "text": ""}) # Doplnenie chýbajúcich častí
            if "text" not in polozka["content"][index_obsahu]: polozka["content"][index_obsahu]["text"] = ""

            polozka["content"][index_obsahu]["text"] += delta
            polozka["formatted"]["text"] += delta
        except (IndexError, KeyError, TypeError) as e:
             zapisovac.error(f"Chyba pri spracovaní text.delta pre položku {id_polozky}: {e}")
             return None, None # Nevrátime deltu, ak nastala chyba
        return polozka, {"text": delta} # Kľúč 'text' je súčasťou API

    def _spracuj_delta_argumentov_volania_funkcie(self, udalost):
        id_polozky = udalost["item_id"] # Kľúč 'item_id' je súčasťou API
        delta = udalost["delta"] # Kľúč 'delta' je súčasťou API
        polozka = self.vyhladavanie_poloziek.get(id_polozky)
        if not polozka:
            zapisovac.warning(f'response.function_call_arguments.delta: Položka "{id_polozky}" nenájdená')
            return None, None
        try:
            # Zaistenie existencie arguments a formatted tool
            if "arguments" not in polozka: polozka["arguments"] = ""
            if "formatted" not in polozka: polozka["formatted"] = {}
            if "tool" not in polozka["formatted"]: polozka["formatted"]["tool"] = {"arguments": ""}
            if "arguments" not in polozka["formatted"]["tool"]: polozka["formatted"]["tool"]["arguments"] = ""

            polozka["arguments"] += delta
            polozka["formatted"]["tool"]["arguments"] += delta
        except (KeyError, TypeError) as e:
             zapisovac.error(f"Chyba pri spracovaní function_call_arguments.delta pre položku {id_polozky}: {e}")
             return None, None # Nevrátime deltu, ak nastala chyba
        return polozka, {"arguments": delta} # Kľúč 'arguments' je súčasťou API
