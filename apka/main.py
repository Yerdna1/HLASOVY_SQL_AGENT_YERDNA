"""
Hlavný súbor aplikácie Chainlit pre real-time asistenta.
Odvodené z https://github.com/Chainlit/cookbook/tree/main/realtime-assistant
"""

import traceback
import chainlit as cl
from chainlit.input_widget import Select, TextInput # Import pre settings
from chainlit.logger import logger
import requests
import datetime
import calendar
import time
import os
import json
from dotenv import load_dotenv # Na explicitné načítanie .env

# Načítanie environmentálnych premenných
load_dotenv()

# Import pomocných funkcií
from apka.rec import KlientRealnehoCasu
from apka.helpers.realtime_setup import nastav_realtime_klienta
# Import nástrojov - predpokladáme, že tento import zostáva alebo bude upravený
from apka.custom_nastroje import nastroje

# --- Helper funkcia na maskovanie kľúčov ---
def mask_api_key(api_key: str | None) -> str:
    """Maskuje API kľúč, zobrazí prvé 4 a posledné 4 znaky."""
    if not api_key or len(api_key) < 9:
        return "Nenastavený alebo príliš krátky"
    return f"{api_key[:4]}...{api_key[-4:]}"

# --- OpenAI Cost Fetching ---
# TODO: Presunúť OPENAI_ADMIN_API_KEY do .env, ak tam ešte nie je
OPENAI_ADMIN_API_KEY_VALUE = os.getenv("OPENAI_ADMIN_API_KEY") # Premenovaná pre jasnosť

def get_openai_monthly_cost(): # Odstránený argument api_key
    """Získa náklady na OpenAI API od začiatku aktuálneho mesiaca."""
    # Použijeme hodnotu načítanú z .env
    if not OPENAI_ADMIN_API_KEY_VALUE or OPENAI_ADMIN_API_KEY_VALUE == "YOUR_OPENAI_ADMIN_API_KEY_HERE": # Pridaná kontrola pre placeholder
        logger.warning("OPENAI_ADMIN_API_KEY nebol nájdený v .env alebo je placeholder. Náklady nebudú zobrazené.")
        return "Chyba: OpenAI Admin API kľúč nie je nakonfigurovaný v .env."

    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_month_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_time_unix = int(start_of_month_dt.timestamp())

    headers = {
        "Authorization": f"Bearer {OPENAI_ADMIN_API_KEY_VALUE}",
        "Content-Type": "application/json",
    }
    params = {
        "start_time": start_time_unix,
    }
    url = "https://api.openai.com/v1/organization/costs"
    response = None

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10) # Pridaný timeout
        response.raise_for_status()
        data = response.json()

        total_cost = 0.0
        currency = "USD"

        if data.get("data"):
            for bucket in data["data"]:
                if bucket.get("results"):
                    for result in bucket["results"]:
                        if result.get("amount"):
                            total_cost += result["amount"].get("value", 0.0)
                            currency = result["amount"].get("currency", currency).upper()

            # Vráti formátovaný reťazec s nákladmi
            return f"Náklady na OpenAI tento mesiac: ${total_cost:.2f} {currency}"
        else:
            if data.get("error"):
                 error_msg = data["error"].get("message", "Neznáma chyba API.")
                 logger.error(f"Chyba API pri získavaní nákladov OpenAI: {error_msg}")
                 if "Incorrect API key" in error_msg or "authentication" in error_msg.lower() or "insufficient permissions" in error_msg.lower():
                     # Vráti chybovú správu špecifickú pre API kľúč
                     return "Chyba: Neplatný alebo neautorizovaný OpenAI Admin API kľúč."
                 # Vráti všeobecnú chybovú správu API
                 return f"Chyba API pri získavaní nákladov: {error_msg}"
            # Vráti správu, ak neboli nájdené žiadne dáta
            return "Nepodarilo sa získať údaje o nákladoch (žiadne dáta)."

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP chyba pri volaní OpenAI Costs API: {http_err}")
        if response is not None:
            status_code = response.status_code
            try:
                error_details = response.json().get("error", {})
                error_message = error_details.get("message", str(http_err))
                error_type = error_details.get("type")
                logger.error(f"Stavový kód: {status_code}, Typ chyby: {error_type}, Správa: {error_message}")
                if status_code == 401 or status_code == 403:
                    # Vráti chybovú správu špecifickú pre API kľúč
                    return "Chyba: Neplatný alebo neautorizovaný OpenAI Admin API kľúč."
                elif status_code == 429:
                    return "Chyba: Prekročený limit požiadaviek na OpenAI API."
                else:
                    # Vráti všeobecnú chybovú správu API
                    return f"Chyba API ({status_code}): {error_message}"
            except Exception as json_err:
                 logger.error(f"Nepodarilo sa parsovať JSON z chybovej odpovede: {json_err}")
                 # Vráti všeobecnú HTTP chybovú správu
                 return f"HTTP chyba pri získavaní nákladov: {http_err}"
        else:
             # Vráti všeobecnú HTTP chybovú správu, ak odpoveď neexistuje
            return f"HTTP chyba pri získavaní nákladov: {http_err}"
    except requests.exceptions.Timeout:
        logger.error("Timeout pri volaní OpenAI Costs API.")
        # Vráti správu o timeoute
        return "Chyba: Vypršal časový limit pri získavaní nákladov."
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Chyba pripojenia pri volaní OpenAI Costs API: {req_err}")
        # Vráti správu o chybe pripojenia
        return f"Chyba pripojenia pri získavaní nákladov: {req_err}"
    except Exception as e:
        logger.error(f"Neočekávaná chyba pri získavaní OpenAI nákladov: {traceback.format_exc()}")
        # Vráti všeobecnú neočakávanú chybovú správu
        return f"Neočekávaná chyba: {e}"

# --- Koniec OpenAI Cost Fetching ---


# --- Koniec OpenAI Cost Fetching ---


@cl.on_chat_start
async def start():
    """Inicializuje chat, nastaví klienta a zobrazí nastavenia."""

    # Načítanie hodnôt z .env pre zobrazenie v nastaveniach
    db_path = os.getenv("DB_DATABASE", "Nenájdené v .env")
    openai_admin_key = os.getenv("OPENAI_ADMIN_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    together_key = os.getenv("TOGETHER_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    # Predvolený LLM provider (môže byť prepísaný nastaveniami)
    default_llm_provider = os.getenv("AGENT_MODE", "Groq").upper() # Predvolená hodnota Groq, ak AGENT_MODE nie je nastavený

    # Definovanie Chat Settings
    settings = await cl.ChatSettings(
        [
            Select(
                id="LLMProvider",
                label="Poskytovateľ LLM",
                values=["Gemini", "OpenAI", "Groq"], # Pridajte ďalšie podľa potreby
                initial_index=["Gemini", "OpenAI", "Groq"].index(default_llm_provider) if default_llm_provider in ["Gemini", "OpenAI", "Groq"] else 2 # Index pre Groq ako fallback
            ),
            TextInput(id="DBPath", label="Cesta k databáze", initial=db_path, disabled=True),
            TextInput(id="OpenAIAdminKey", label="OpenAI Admin Key", initial=mask_api_key(openai_admin_key), disabled=True),
            TextInput(id="GeminiKey", label="Gemini Key", initial=mask_api_key(gemini_key), disabled=True),
            TextInput(id="OpenAIKey", label="OpenAI Key", initial=mask_api_key(openai_key), disabled=True),
            TextInput(id="TogetherKey", label="Together Key", initial=mask_api_key(together_key), disabled=True),
            TextInput(id="TavilyKey", label="Tavily Key", initial=mask_api_key(tavily_key), disabled=True),
            TextInput(id="GroqKey", label="Groq Key", initial=mask_api_key(groq_key), disabled=True),
        ]
    ).send()

    # Uloženie počiatočného výberu LLM do session
    selected_llm = settings.get("LLMProvider")
    cl.user_session.set("selected_llm_provider", selected_llm)
    logger.info(f"Počiatočný LLM poskytovateľ nastavený na: {selected_llm}")

    # Zobrazenie úvodnej správy
    await cl.Message(content="Ahoj! Som tu. Stlač `P` pre rozprávanie!").send()

    # Získanie a zobrazenie nákladov OpenAI (ak je kľúč platný)
    cost_message_content = get_openai_monthly_cost() # Už nepotrebuje argument
    await cl.Message(content=cost_message_content, author="Systémové Info").send()

    # Nastavenie klienta pomocou importovanej funkcie a nástrojov
    # TODO: Upraviť nastav_realtime_klienta, aby akceptovala a použila selected_llm
    await nastav_realtime_klienta(nastroje) # Zatiaľ voláme bez LLM providera

    # Pridanie tlačidla pre históriu
    actions = [
        cl.Action(name="show_history", value="show", label="Zobraziť históriu")
    ]
    await cl.Message(content="Môžete zobraziť históriu konverzácie.", actions=actions).send()


LOG_FILE_PATH = os.path.join("apka", "output", "conversation_log.jsonl")

@cl.on_settings_update
async def on_settings_update(settings):
    """Spracuje aktualizáciu nastavení."""
    selected_llm = settings.get("LLMProvider")
    if selected_llm:
        cl.user_session.set("selected_llm_provider", selected_llm)
        logger.info(f"LLM poskytovateľ aktualizovaný na: {selected_llm}")
        await cl.Message(content=f"Poskytovateľ LLM bol zmenený na **{selected_llm}**. Zmena sa prejaví pri ďalšej interakcii.").send()
        # TODO: Potenciálne reinicializovať klienta alebo len zmeniť model pri ďalšom volaní
        # klient: KlientRealnehoCasu = cl.user_session.get("klient_realneho_casu")
        # if klient:
        #     await klient.aktualizuj_konfiguraciu_llm(selected_llm) # Hypotetická funkcia


@cl.action_callback("show_history")
async def on_show_history(action: cl.Action):
    """Načíta a zobrazí históriu konverzácie z log súboru."""
    logger.info(f"Kliknuté na akciu: {action.name} - Načítava sa história...")
    history_content = "### História Konverzácie\n\n"
    try:
        if not os.path.exists(LOG_FILE_PATH):
            history_content += "*História zatiaľ neexistuje.*"
        else:
            with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    history_content += "*História je prázdna.*"
                else:
                    for line in lines:
                        try:
                            log_entry = json.loads(line.strip())
                            timestamp = log_entry.get("timestamp", "N/A")
                            event_type = log_entry.get("event_type", "Neznámy typ")
                            data = log_entry.get("data", {})
                            history_content += f"**Čas:** {timestamp}\n"
                            history_content += f"**Typ:** `{event_type}`\n"

                            if event_type == "user_message_sent":
                                content_list = data.get("content", [])
                                text_content = next((item.get("text") for item in content_list if item.get("type") == "input_text"), None)
                                if text_content:
                                     history_content += f"**Používateľ:** {text_content}\n"
                                else:
                                     history_content += f"**Používateľ:** (Obsah bez textu)\n"
                            elif event_type == "assistant_message_completed":
                                content_list = data.get("content", [])
                                text_content = next((item.get("text") for item in content_list if item.get("type") == "output_text"), None)
                                if text_content:
                                     history_content += f"**Asistent:** {text_content}\n"
                                else:
                                     history_content += f"**Asistent:** (Obsah bez textu)\n"
                            elif event_type == "tool_call_started":
                                history_content += f"**Volanie nástroja začalo:** `{data.get('tool_name')}` (ID: {data.get('call_id')})\n"
                                history_content += f"**Argumenty:** ```json\n{data.get('arguments', '{}')}\n```\n"
                            elif event_type == "tool_call_ended":
                                history_content += f"**Volanie nástroja skončilo:** `{data.get('tool_name')}` (ID: {data.get('call_id')})\n"
                                if "error" in data:
                                    history_content += f"**Chyba:** {data.get('error')}\n"
                                else:
                                    result = data.get('result', {})
                                    if "sql_query" in data:
                                         history_content += f"**SQL Dotaz:** ```sql\n{data.get('sql_query')}\n```\n"
                                         history_content += f"**Vysvetlenie:** {data.get('sql_explanation', '')}\n"
                                    elif "image_path" in data:
                                         history_content += f"**Správa:** {result.get('message', '')}\n"
                                         history_content += f"**Uložený obrázok:** `{data.get('image_path')}`\n"
                                    else:
                                         # Všeobecný výsledok nástroja
                                         history_content += f"**Výsledok:** ```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```\n"
                            else:
                                # Pre ostatné typy udalostí zobrazíme surové dáta
                                history_content += f"**Dáta:** ```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```\n"

                            history_content += "---\n" # Oddeľovač medzi záznamami
                        except json.JSONDecodeError:
                            history_content += f"*Chyba pri čítaní riadku:* `{line.strip()}`\n---\n"
                        except Exception as parse_err:
                             history_content += f"*Chyba pri spracovaní záznamu:* {parse_err}\n---\n"

    except Exception as e:
        logger.error(f"Chyba pri čítaní log súboru {LOG_FILE_PATH}: {e}")
        history_content = f"Chyba pri načítaní histórie: {e}"

    # Odoslanie histórie ako jednej správy (môže byť dlhá)
    await cl.Message(content=history_content).send()
    # Môžeme odstrániť tlačidlo po kliknutí, ak je to žiaduce
    # await action.remove()


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
