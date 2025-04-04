# PoC BOT Yerdna na komunikaciu s SQL

Tento projekt implementuje Proof-of-Concept (PoC) hlasového asistenta ("Yerdna") pre Chainlit, ktorý umožňuje používateľom interaktívne komunikovať s databázou pomocou prirodzeného jazyka (hlasom alebo textom). Agent využíva externé real-time API pre spracovanie reči a jazyka a lokálne nástroje na vykonávanie SQL dotazov a vizualizáciu dát.

## Architektúra a Ako to funguje

Systém kombinuje Chainlit frontend, lokálne Python nástroje a externé real-time API:

1.  **Frontend (Chainlit):**
    *   Používateľ interaguje s aplikáciou cez Chainlit rozhranie (`apka/main.py`).
    *   Podporuje textový vstup aj hlasový vstup v reálnom čase.

2.  **Real-time Klient (`apka/rec/client.py`):**
    *   Tento klient sa pripája k externému real-time API (jeho URL a kľúč sú konfigurovateľné).
    *   Spravuje WebSocket spojenie.
    *   Posiela audio streamy a textové správy používateľa na backend API.
    *   Prijíma inštrukcie z backend API, vrátane požiadaviek na volanie lokálnych nástrojov.
    *   Prijíma spracované odpovede (text, audio, prepisy) z backend API a zobrazuje ich v Chainlit UI.

3.  **Backend Real-time API (Externé):**
    *   *Poznámka: Implementácia tohto API nie je súčasťou tohto repozitára.*
    *   Prijíma audio streamy a vykonáva Speech-to-Text (STT) pomocou **Whisper** (podľa konfigurácie v `client.py`).
    *   Prijíma textové vstupy.
    *   Obsahuje hlavnú logiku LLM agenta:
        *   Interpretuje požiadavky používateľa.
        *   Rozhoduje, kedy je potrebné získať dáta z databázy alebo vizualizovať výsledky.
        *   Posiela požiadavky na volanie lokálnych nástrojov (`vykonaj_sql`, `nakresli_plotly_graf`) späť Chainlit klientovi.
        *   Prijíma výsledky z lokálnych nástrojov.
        *   Formuluje finálnu odpoveď pre používateľa (textovú alebo hlasovú).

4.  **Lokálne Nástroje (`apka/custom_nastroje/`):**
    *   Tieto nástroje sú volané Chainlit klientom *na základe požiadavky z backend API*.
    *   **`vykonaj_sql` (`databaza.py`):**
        *   Tento nástroj je zodpovedný za Text-to-SQL.
        *   Používa **Langchain** (`PromptTemplate`, `llm.with_structured_output`) na zostavenie promptu pre LLM.
        *   Prompt obsahuje schému databázy (`apka/settings/popis_schemy.yaml`), informácie o SQL dialekte a otázku používateľa (ktorú dostal z backend API cez parameter volania nástroja).
        *   Očakáva štruktúrovaný výstup od LLM vo formáte Pydantic modelu `SQLDotaz` (`apka/models/sql_models.py`), ktorý obsahuje SQL dotaz a jeho vysvetlenie.
        *   Používa špecifický LLM model nakonfigurovaný pre SQL (`apka/widgets/LLM_modely.py`).
        *   Vykonáva vygenerovaný SQL dotaz pomocou **SQLAlchemy** (`apka/settings/databaza.py`).
        *   Zobrazuje SQL, vysvetlenie a výsledky (tabuľku alebo správu o úspechu/chybe) v Chainlit UI.
        *   Výsledok (dáta alebo chyba) posiela späť backend API.
    *   **`nakresli_plotly_graf` (`graf.py`):**
        *   Prijme definíciu Plotly grafu (JSON) a sprievodnú správu (z backend API).
        *   Vykreslí graf pomocou knižnice **Plotly** a zobrazí ho v Chainlit UI.
        *   Výsledok (úspech/chyba) posiela späť backend API.

5.  **Konfigurácia a Pomocné Moduly:**
    *   **Databáza (`apka/settings/databaza.py`):** Spravuje pripojenie k databáze (SQLite default, konfigurovateľné cez env premenné) pomocou SQLAlchemy.
    *   **Schéma (`apka/settings/popis_schemy.yaml`, `apka/utils/schema_helper.py`):** Definuje a načítava schému databázy pre LLM.
    *   **LLM Modely (`apka/widgets/LLM_modely.py`):** Umožňuje konfiguráciu a výber LLM modelov pre generovanie SQL.
    *   **Pydantic Modely (`apka/models/sql_models.py`):** Definuje štruktúru pre výstup SQL generujúceho LLM.

## Inštalácia a Spustenie

### Požiadavky
*   Python 3.12+
*   `uv` (alebo `pip`)
*   Prístup k databáze (predvolene SQLite v `scratchpad/apka_databaza.db`, konfigurovateľné cez env premenné pre napr. PostgreSQL)
*   Konfigurácia pre externé real-time API (URL, API kľúč)
*   API kľúče pre LLM modely (napr. OpenAI, Groq, Together - podľa `apka/widgets/LLM_modely.py`)

### Kroky

1.  **Klonovanie repozitára:**
    ```bash
    git clone <URL_repozitara>
    cd <nazov_repozitara>
    ```

2.  **Vytvorenie a aktivácia virtuálneho prostredia (pomocou `uv`):**
    ```bash
    uv venv
    source .venv/bin/activate  # Linux/macOS
    # alebo
    .venv\Scripts\activate    # Windows
    ```

3.  **Inštalácia závislostí:**
    ```bash
    uv pip install -e .
    ```

4.  **Konfigurácia:**
    *   Nastavte premenné prostredia pre pripojenie k databáze (ak nepoužívate predvolené SQLite): `DB_DIALECT`, `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`.
    *   Nastavte premenné prostredia pre API kľúče LLM modelov (napr. `OPENAI_API_KEY`, `GROQ_API_KEY`, `TOGETHER_API_KEY`).
    *   Nastavte premenné prostredia alebo inak nakonfigurujte URL a API kľúč pre externé real-time API, ktoré používa `apka/rec/client.py`.

5.  **Vytvorenie/Inicializácia Databázy (ak je potrebné):**
    *   Pre predvolenú SQLite databázu sa súbor vytvorí automaticky pri prvom pripojení v adresári `scratchpad`.
    *   Ak používate inú databázu, uistite sa, že existuje a je dostupná.
    *   Môže existovať skript na naplnenie databázy dátami:
      ```bash
      # Príklad (upraviť podľa skutočného skriptu, ak existuje)
      # uv run python -m apka.helpers.vytvor_databazu
      ```

6.  **Spustenie Aplikácie (Chainlit):**
    ```bash
    chainlit run apka/main.py -w
    ```
    *   `-w` zapne automatické obnovenie pri zmenách v kóde.
