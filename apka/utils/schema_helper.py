"""Pomocné funkcie pre načítanie a formátovanie popisu schémy databázy."""

import os
import yaml

def nacitaj_popis_schemy():
    """Načíta a naformátuje popis schémy z YAML súboru."""
    # Cesta k YAML súboru so schémou, relatívne k tomuto súboru
    schema_path = os.path.join(os.path.dirname(__file__), "../settings/popis_schemy.yaml")
    try:
        with open(schema_path, "r", encoding='utf-8') as f: # Pridané kódovanie UTF-8
            schema_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Chyba: Súbor schémy nebol nájdený na ceste: {schema_path}")
        return "Chyba: Popis schémy nie je dostupný."
    except Exception as e:
        print(f"Chyba pri načítaní alebo spracovaní súboru schémy: {e}")
        return "Chyba: Popis schémy nie je dostupný."

    if not schema_data or "schema" not in schema_data or "tables" not in schema_data["schema"]:
         print(f"Chyba: Neplatný formát súboru schémy: {schema_path}")
         return "Chyba: Popis schémy má neplatný formát."


    # Formátovanie popisu schémy
    popis = "Dostupné tabuľky a ich štruktúry:\n\n"

    # Pridanie tabuliek a ich stĺpcov
    for nazov_tabulky, info_tabulky in schema_data["schema"]["tables"].items():
        popis += f"{nazov_tabulky}\n"
        if "columns" in info_tabulky:
            for stlpec in info_tabulky["columns"]:
                obmedzenia = f", {stlpec['constraints']}" if "constraints" in stlpec else ""
                popis += f"- {stlpec['name']} ({stlpec['type']}{obmedzenia})\n"
        popis += "\n"

    # Pridanie príkladových dotazov, ak existujú
    if "example_queries" in schema_data["schema"]:
        popis += "Príkladové dotazy:\n"
        for priklad in schema_data["schema"]["example_queries"]:
            popis += f"O: {priklad['question']}\n"
            popis += f"A: {priklad['sql']}\n\n"

    return popis
# Načítanie popisu schémy pri importe modulu
POPIS_SCHEMY = nacitaj_popis_schemy()
