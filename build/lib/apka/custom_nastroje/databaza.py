"""Nástroj na dopytovanie databázy s konverziou prirodzeného jazyka na SQL."""

import chainlit as cl
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field

# Predpokladáme, že tieto budú dostupné po refaktorizácii/preklade príslušných modulov
from apka.settings.databaza import db_config, db_connection, dialect_info # Upraviť podľa finálnej štruktúry settings.databaza
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


async def spracuj_sql_dotaz(otazka: str):
    """Prevedie prirodzený jazyk na SQL, vykoná dotaz a vráti výsledky."""
    try:
        zapisovac.info(f"🤔 Spracováva sa dotaz v prirodzenom jazyku: '{otazka}'")

        llm = ziskaj_llm("sql_generation")
        strukturovany_llm = llm.with_structured_output(SQLDotaz)

        dialekt = db_config.dialect.lower()
        pomoc_k_dialektu = dialect_info.get(dialekt, {"notes": "", "examples": ""})

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

        # Vykonanie vygenerovaného SQL dotazu
        vysledok = db_connection.execute_query(sql_odpoved.dotaz)

        if "error" in vysledok:
            await cl.Message(content=f"❌ Chyba pri vykonávaní dotazu: {vysledok['error']}", type="error").send()
            return vysledok

        if "rows" in vysledok:
            # Formátovanie výsledkov SELECT dotazu
            stlpce = vysledok["columns"]
            riadky = vysledok["rows"]

            if not riadky:
                await cl.Message(content="Dotaz bol úspešne vykonaný. Nenašli sa žiadne výsledky.").send()
                return {"message": "Žiadne výsledky"}

            # Vytvorenie markdown tabuľky pre lepšie formátovanie
            hlavicka = "| " + " | ".join(f"**{str(stlpec)}**" for stlpec in stlpce) + " |"
            oddelovac = "|" + "|".join("---" for _ in stlpce) + "|"
            riadky_formatovane = ["| " + " | ".join(str(hodnota) for hodnota in riadok.values()) + " |" for riadok in riadky]

            tabulka = "\n".join([hlavicka, oddelovac] + riadky_formatovane)
            await cl.Message(content=f"**Výsledky Dotazu:**\n\n{tabulka}").send()
            return {"rows": riadky}
        else:
            # Formátovanie výsledkov INSERT/UPDATE/DELETE
            sprava = f"✅ Dotaz bol úspešne vykonaný. Ovplyvnené riadky: {vysledok['affected_rows']}"
            await cl.Message(content=sprava).send()
            return vysledok

    except Exception as e:
        chybova_sprava = f"Chyba pri spracovaní dotazu: {str(e)}"
        zapisovac.error(f"❌ {chybova_sprava}")
        await cl.Message(content=chybova_sprava, type="error").send()
        return {"error": chybova_sprava}


vykonaj_sql = (definicia_vykonaj_sql, spracuj_sql_dotaz)
