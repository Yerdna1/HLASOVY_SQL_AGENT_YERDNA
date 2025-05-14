
"""Nástroj na dopytovanie databázy s konverziou prirodzeného jazyka na SQL."""

"""Nástroj na dopytovanie databázy s konverziou prirodzeného jazyka na SQL."""

"""Nástroj na dopytovanie databázy s konverziou prirodzeného jazyka na SQL."""

"""Nástroj na dopytovanie databázy s konverziou prirodzeného jazyka na SQL."""

"""Nástroj na dopytovanie databázy s konverziou prirodzeného jazyka na SQL."""

import json # Add missing import
import chainlit as cl
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field
from ultravox_client.session import ClientToolResult # Import ClientToolResult from specific module
# Removed incorrect ClientToolResult import

# Predpokladáme, že tieto budú dostupné po refaktorizácii/preklade príslušných modulov
# Používame priamo db_konfiguracia namiesto aliasu db_config
from apka.settings.databaza import db_konfiguracia, db_connection, dialect_info
from apka.widgets.LLM_modely import ziskaj_llm
from apka.widgets.spolocne import zapisovac
from apka.utils.schema_helper import POPIS_SCHEMY
from apka.models.sql_models import SQLDotaz


definicia_vykonaj_sql = {
    "name": "vykonaj_sql",
    "description": "Prevedie prirodzený jazyk na SQL a vykoná dotaz v databáze.",
    "parameters": {
        "type": "object",
        "properties": {
            "otazka": {
                "type": "string",
                "description": "Otázka v prirodzenom jazyku týkajúca sa dát (napr. 'Ukáž mi všetkých používateľov, ktorí sa pridali minulý mesiac')",
            },
        },
        "required": ["otazka"],
    },
}


# Modify function signature to accept a single dictionary argument
async def spracuj_sql_dotaz(params: dict) -> str:
    """Prevedie prirodzený jazyk na SQL, vykoná dotaz a vráti výsledky."""
    # Extract otazka from the params dictionary
    otazka = params.get("otazka")
    if not otazka or not isinstance(otazka, str):
        error_msg = "Chyba: Chýbajúci alebo neplatný parameter 'otazka'."
        zapisovac.error(f"❌ {error_msg}")
        # Try sending error to Chainlit UI if possible
        try:
            await cl.Message(content=error_msg, type="error").send()
        except Exception as cl_err:
            zapisovac.error(f"Failed to send error message to Chainlit UI: {cl_err}")
        return f"Error: {error_msg}" # Return error string

    try:
        zapisovac.info(f"🤔 Spracováva sa dotaz v prirodzenom jazyku: '{otazka}'")

        llm = ziskaj_llm("sql_generation")
        strukturovany_llm = llm.with_structured_output(SQLDotaz)

        # Používame priamo db_konfiguracia
        if not db_konfiguracia or not hasattr(db_konfiguracia, 'dialekt'):
             chyba = "Chyba: Konfigurácia databázy (db_konfiguracia) nie je správne inicializovaná alebo jej chýba atribút 'dialekt'."
             zapisovac.error(chyba)
             await cl.Message(content=chyba, type="error").send()
             return ClientToolResult(result=f"Error: {chyba}") # Wrap in ClientToolResult

        dialekt = db_konfiguracia.dialekt.lower()
        pomoc_k_dialektu = dialect_info.get(dialekt, {"notes": "", "examples": ""}) if dialect_info else {"notes": "", "examples": ""}


        systemova_sablona = f"""
        Ste expert na generovanie SQL dotazov pre {dialekt.upper()} databázy. Preveďte danú otázku v prirodzenom jazyku na {dialekt.upper()}-kompatibilný SQL dotaz.
        Zabezpečte, aby bol dotaz efektívny a dodržiaval syntax a osvedčené postupy pre {dialekt.upper()}.

        # Dôležité poznámky pre {dialekt.upper()}
        {pomoc_k_dialektu["notes"]}

        # Schéma Databázy
        {POPIS_SCHEMY}

        # Príkladové Dotazy pre {dialekt.upper()}
        {pomoc_k_dialektu["examples"]}

        # Otázka
        {{otazka}}

        # Úloha
        1. Analyzujte otázku a schému
        2. Vygenerujte {dialekt.upper()}-kompatibilný SQL dotaz
        3. Poskytnite stručné vysvetlenie, čo dotaz robí
        4. Vráťte dotaz aj vysvetlenie
        """

        sablona_promptu = PromptTemplate(
            input_variables=["otazka"],
            template=systemova_sablona,
        )

        retazec = sablona_promptu | strukturovany_llm
        sql_odpoved: SQLDotaz = retazec.invoke({"otazka": otazka})

        # Zaznamenať vygenerované SQL
        zapisovac.info(f"💡 Vygenerovaný SQL dotaz: {sql_odpoved.dotaz}")
        zapisovac.info(f"💡 Vygenerované SQL vysvetlenie: {sql_odpoved.vysvetlenie}")

        # Zoskupiť SQL dotaz a vysvetlenie do jednej správy s prvkami
        formatovany_sql = (
            sql_odpoved.dotaz.replace(" FROM ", "\nFROM ")
            .replace(" JOIN ", "\nJOIN ")
            .replace(" WHERE ", "\nWHERE ")
            .replace(" GROUP BY ", "\nGROUP BY ")
            .replace(" ORDER BY ", "\nORDER BY ")
        )

        await cl.Message(content=formatovany_sql, language="sql").send()
        await cl.Message(content=f"**Vysvetlenie:** {sql_odpoved.vysvetlenie}").send()

        # Vykonanie vygenerovaného SQL dotazu pomocou správnej metódy
        vysledok = db_connection.vykonaj_dotaz(sql_odpoved.dotaz)

        if "error" in vysledok:
            error_msg = f"Chyba pri vykonávaní dotazu: {vysledok['error']}"
            await cl.Message(content=f"❌ {error_msg}", type="error").send()
            return ClientToolResult(result=f"Error: {error_msg}") # Wrap in ClientToolResult

        if "rows" in vysledok:
            # Formátovanie výsledkov SELECT dotazu
            stlpce = vysledok["columns"]
            riadky = vysledok["rows"]

            if not riadky:
                msg = "Dotaz bol úspešne vykonaný. Nenašli sa žiadne výsledky."
                await cl.Message(content=msg).send()
                return ClientToolResult(result=msg) # Wrap in ClientToolResult

            # Vytvorenie markdown tabuľky pre lepšie formátovanie
            hlavicka = "| " + " | ".join(f"**{str(stlpec)}**" for stlpec in stlpce) + " |"
            oddelovac = "|" + "|".join("---" for _ in stlpce) + "|"
            riadky_formatovane = ["| " + " | ".join(str(hodnota) for hodnota in riadok.values()) + " |" for riadok in riadky]

            tabulka = "\n".join([hlavicka, oddelovac] + riadky_formatovane)
            await cl.Message(content=f"**Výsledky Dotazu:**\n\n{tabulka}").send()
            # Return summary string including JSON data wrapped in ClientToolResult
            try:
                # Convert rows (list of dicts) to JSON string
                data_json = json.dumps(riadky, ensure_ascii=False)
                # Return ONLY the JSON data string, wrapped in ClientToolResult
                return ClientToolResult(result=data_json)
            except Exception as json_e:
                zapisovac.error(f"Chyba pri konverzii výsledkov SQL na JSON: {json_e}")
                # Return an error message if JSON conversion fails
                return ClientToolResult(result=f"Dotaz úspešne vykonaný, ale nastala chyba pri formátovaní dát ({json_e}).")
        else:
            # Formátovanie výsledkov INSERT/UPDATE/DELETE
            sprava = f"✅ Dotaz bol úspešne vykonaný. Ovplyvnené riadky: {vysledok['affected_rows']}"
            await cl.Message(content=sprava).send()
            return ClientToolResult(result=sprava) # Wrap in ClientToolResult

    except Exception as e:
        chybova_sprava = f"Chyba pri spracovaní dotazu: {str(e)}"
        zapisovac.error(f"❌ {chybova_sprava}")
        await cl.Message(content=chybova_sprava, type="error").send()
        return ClientToolResult(result=f"Error: {chybova_sprava}") # Wrap in ClientToolResult


vykonaj_sql = (definicia_vykonaj_sql, spracuj_sql_dotaz)
