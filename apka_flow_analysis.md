# Analýza Toku Vykonávania Aplikácie `apka`

Tento dokument popisuje sekvenciu volaní metód a funkcií počas typických interakcií v aplikácii Chainlit.

## 1. Inicializácia Aplikácie (`@cl.on_chat_start` v `main.py`)

1.  **`load_dotenv()`**: Načítajú sa environmentálne premenné zo súboru `.env`.
2.  **Načítanie premenných**: Získajú sa hodnoty pre cestu k DB a API kľúče (`os.getenv`).
3.  **`mask_api_key()`**: Pomocná funkcia na maskovanie API kľúčov pre zobrazenie.
4.  **`cl.ChatSettings(...).send()`**: Vytvorí a odošle panel nastavení do UI. Obsahuje:
    *   `cl.Select` pre výber LLM providera (Gemini, OpenAI, Groq).
    *   `cl.TextInput` (disabled) pre cestu k DB.
    *   `cl.TextInput` (disabled) pre maskované API kľúče.
5.  **`cl.user_session.set("selected_llm_provider", ...)`**: Uloží počiatočný výber LLM do session.
6.  **`cl.Message(...).send()`**: Odošle úvodnú správu "Ahoj! ...".
7.  **`get_openai_monthly_cost()`**: Zavolá funkciu na získanie nákladov OpenAI (použije kľúč z `os.getenv`).
8.  **`cl.Message(...).send()`**: Odošle správu s nákladmi OpenAI (alebo chybovú správu).
9.  **`nastav_realtime_klienta(nastroje)`** (v `helpers/realtime_setup.py`):
    *   Vytvorí inštanciu `KlientRealnehoCasu` (z `rec/client.py`).
    *   Nastaví `id_sledovania` v `cl.user_session`.
    *   Definuje vnorené `async` funkcie na spracovanie udalostí z klienta (`spracuj_aktualizaciu_konverzacie`, `spracuj_dokoncenie_polozky`, `spracuj_prerusenie_konverzacie`, `spracuj_chybu`).
    *   Registruje tieto funkcie ako handlery pre udalosti z `klient_realneho_casu` pomocou `klient_realneho_casu.on(...)`.
    *   Uloží inštanciu `klient_realneho_casu` do `cl.user_session`.
    *   Iteruje cez `zoznam_nastrojov` (importovaný ako `nastroje` z `custom_nastroje/__init__.py`).
    *   Pre každý nástroj volá `klient_realneho_casu.pridaj_nastroj(definicia, spracovatel)`.
        *   V `pridaj_nastroj` (v `rec/client.py`): Uloží definíciu a handler nástroja do slovníka `self.nastroje` a zavolá `self.aktualizuj_relaciu`.
            *   V `aktualizuj_relaciu`: Zostaví zoznam všetkých nástrojov a odošle `session.update` cez `self.realtime_api`.
10. **`cl.Message(...).send()`**: Odošle správu s tlačidlom "Zobraziť históriu".

## 2. Spracovanie Textovej Správy (`@cl.on_message` v `main.py`)

1.  Získa `klient_realneho_casu` z `cl.user_session`.
2.  Ak je klient pripojený, volá `klient_realneho_casu.posli_obsah_spravy_pouzivatela(content)` (v `rec/client.py`).
    *   V `posli_obsah_spravy_pouzivatela`:
        *   Volá `self._log_event("user_message_sent", ...)` na zápis do `conversation_log.jsonl`.
        *   Odošle udalosť `conversation.item.create` s rolou `user` a textovým obsahom cez `self.realtime_api.posli`.
        *   Volá `self.vytvor_odpoved()`.
            *   V `vytvor_odpoved`: Odošle udalosť `response.create` cez `self.realtime_api.posli`.

## 3. Spracovanie Audio Vstupu (v `main.py`)

1.  **`@cl.on_audio_start`**:
    *   Získa `klient_realneho_casu`.
    *   Ak nie je pripojený, volá `klient_realneho_casu.pripoj()`.
        *   V `pripoj` (v `rec/client.py`): Volá `self.realtime_api.pripoj()` a `self.aktualizuj_relaciu()`.
2.  **`@cl.on_audio_chunk`**:
    *   Získa `klient_realneho_casu`.
    *   Volá `klient_realneho_casu.pridaj_vstupne_audio(chunk.data)`.
        *   V `pridaj_vstupne_audio` (v `rec/client.py`): Konvertuje audio dáta na base64 a odošle udalosť `input_audio_buffer.append` cez `self.realtime_api.posli`. Pridá surové bajty do `self.vstupny_audio_buffer`.
3.  **`@cl.on_audio_end`**: (Momentálne prázdne, ale mohlo by volať `klient_realneho_casu.vytvor_odpoved()`, ak by bola detekcia reči (VAD) vypnutá).

## 4. Spracovanie Odpovede Asistenta a Volanie Nástrojov (v `rec/client.py`)

1.  Server (napr. OpenAI Realtime API) posiela udalosti (`server.response.created`, `server.response.output_item.added`, `server.response.text.delta`, `server.response.output_item.done`, atď.).
2.  **`_pridaj_spracovatelov_api_udalosti`**: Registruje metódy klienta ako handlery pre tieto udalosti.
3.  **`_spracuj_udalost_konverzacie`**: Väčšina udalostí je delegovaná na `self.konverzacia.spracuj_udalost` (v `rec/conversation.py`), ktorá aktualizuje interný stav konverzácie. Následne sa odošle udalosť `conversation.updated` do UI (spracovaná v `helpers/realtime_setup.py` -> `spracuj_aktualizaciu_konverzacie` na streamovanie audia/textu).
4.  **`_pri_dokonceni_vystupnej_polozky`**: Handler pre `server.response.output_item.done`.
    *   Volá `_spracuj_udalost_konverzacie`.
    *   Odošle `conversation.item.completed` do UI.
    *   Ak je dokončená položka správa asistenta (`role == "assistant"`), volá `self._log_event("assistant_message_completed", ...)` na zápis do logu.
    *   Ak dokončená položka obsahuje volanie nástroja (`polozka.get("formatted", {}).get("tool")`), volá `self._zavolaj_nastroj(tool_data)`.
        *   V `_zavolaj_nastroj`:
            *   Získa názov nástroja, argumenty (JSON string), ID volania.
            *   Volá `self._log_event("tool_call_started", ...)` na zápis do logu.
            *   Pokúsi sa parsovať argumenty (`json.loads`).
                *   Ak parsovanie zlyhá (`json.JSONDecodeError`): Zaloguje chybu vrátane surových argumentov, odošle `conversation.item.create` s chybovým výstupom funkcie cez `realtime_api` a **ukončí** spracovanie tohto volania.
            *   Získa handler nástroja zo slovníka `self.nastroje`.
            *   Volá handler nástroja (`await konfiguracia_nastroja["handler"](**json_argumenty)`).
                *   **Príklad: `spracuj_sql_dotaz`** (v `databaza.py`):
                    *   Získa LLM (`ziskaj_llm`).
                    *   Vytvorí štruktúrovaný LLM (`with_structured_output(SQLDotaz)`).
                    *   Pripraví prompt s dialektom a schémou.
                    *   Zavolá LLM reťazec (`retazec.invoke`).
                    *   Zaloguje vygenerovaný SQL a vysvetlenie.
                    *   Odošle SQL a vysvetlenie ako `cl.Message`.
                    *   Vykoná SQL dotaz (`db_connection.vykonaj_dotaz`).
                    *   Odošle výsledky alebo chybu ako `cl.Message`.
                    *   Vráti slovník s výsledkami alebo chybou.
                *   **Príklad: `spracuj_nakreslenie_plotly_grafu`** (v `graf.py`):
                    *   Zaloguje debug informácie.
                    *   Parsovanie JSON na Plotly figúru (`plotly.io.from_json`).
                    *   Vygeneruje unikátny názov súboru a cestu v `apka/output/images/`.
                    *   Pokúsi sa uložiť graf ako PNG (`figura.write_image`). Zaloguje úspech alebo chybu.
                    *   Odošle graf a správu ako `cl.Message` s `cl.Plotly` elementom.
                    *   Vráti slovník obsahujúci správu a prípadne `image_path`.
            *   Po úspešnom vykonaní handleru:
                *   Zostaví `log_data_success` (obsahuje `call_id`, `tool_name`, `result`).
                *   Ak výsledok obsahuje `sql_query` alebo `image_path`, pridá ich do `log_data_success`.
                *   Volá `self._log_event("tool_call_ended", log_data_success)`.
                *   Odošle `conversation.item.create` s výstupom funkcie (výsledok nástroja) cez `realtime_api`.
            *   Po neúspešnom vykonaní handleru (iná chyba ako JSONDecodeError):
                *   Zaloguje chybu.
                *   Volá `self._log_event("tool_call_ended", ...)` s chybovou správou.
                *   Odošle `conversation.item.create` s chybovým výstupom funkcie cez `realtime_api`.
            *   **Nakoniec (po úspechu aj chybe handleru, ale nie po chybe parsovania JSON):** Volá `self.vytvor_odpoved()` na vyžiadanie ďalšej odpovede od asistenta.

## 5. Aktualizácia Nastavení (`@cl.on_settings_update` v `main.py`)

1.  Získa aktualizované hodnoty z `settings`.
2.  Ak sa zmenil `LLMProvider`:
    *   Uloží novú hodnotu do `cl.user_session.set("selected_llm_provider", ...)`.
    *   Zaloguje zmenu.
    *   Odošle `cl.Message` informujúcu používateľa o zmene.
    *   **(TODO)**: V budúcnosti by tu mohla byť logika na re-inicializáciu klienta alebo aktualizáciu jeho konfigurácie.

## 6. Zobrazenie Histórie (`@cl.action_callback("show_history")` v `main.py`)

1.  Zaloguje informáciu o kliknutí.
2.  Skontroluje existenciu `LOG_FILE_PATH` (`apka/output/conversation_log.jsonl`).
3.  Ak súbor existuje a nie je prázdny:
    *   Otvorí a číta súbor riadok po riadku.
    *   Pre každý riadok:
        *   Pokúsi sa parsovať JSON (`json.loads`).
        *   Extrahujte `timestamp`, `event_type`, `data`.
        *   Formátuje záznam do Markdown stringu (`history_content`) na základe `event_type`:
            *   Pre `user_message_sent`: Zobrazí text používateľa.
            *   Pre `assistant_message_completed`: Zobrazí text asistenta.
            *   Pre `tool_call_started`: Zobrazí názov nástroja, ID volania a argumenty.
            *   Pre `tool_call_ended`: Zobrazí názov nástroja, ID volania a buď chybu, alebo výsledok (špeciálne formátovanie pre SQL a obrázky).
            *   Pre ostatné typy: Zobrazí surové dáta.
        *   Pridá oddeľovač (`---`).
        *   Zachytáva a formátuje chyby pri parsovaní JSON alebo spracovaní záznamu.
4.  Ak súbor neexistuje alebo je prázdny, pridá príslušnú správu do `history_content`.
5.  Zachytáva všeobecné chyby pri čítaní súboru.
6.  Odošle celý `history_content` ako jednu `cl.Message`.
