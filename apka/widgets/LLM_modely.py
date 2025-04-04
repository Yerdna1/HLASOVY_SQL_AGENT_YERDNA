"""Konfigurácia a inicializácia AI modelov."""

import os
import yaml
from langchain_groq import ChatGroq
from apka.widgets.spolocne import zapisovac


def nacitaj_konfiguraciu_modelov():
    """Načíta konfiguráciu AI modelov z YAML súboru."""
    # Cesta ku konfiguračnému súboru, relatívne k tomuto súboru
    config_path = os.path.join(os.path.dirname(__file__), "../settings/definicia_modelov.yaml")
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            return yaml.safe_load(f)["models"]
    except FileNotFoundError:
        zapisovac.error(f"❌ Konfiguračný súbor modelov nebol nájdený: {config_path}")
        return {"default": {"name": "llama-3.1-70b-versatile", "temperature": 0.1, "max_retries": 2}} # Fallback
    except Exception as e:
        zapisovac.error(f"❌ Chyba pri načítaní konfigurácie modelov: {str(e)}")
        return {"default": {"name": "llama-3.1-70b-versatile", "temperature": 0.1, "max_retries": 2}}


def ziskaj_llm(uloha: str = "default") -> ChatGroq:
    """Vráti nakonfigurovanú inštanciu LLM pre špecifikovanú úlohu."""
    try:
        konfiguracia = nacitaj_konfiguraciu_modelov()
        predvolena_konfiguracia = konfiguracia.get("default", {})
        konfiguracia_ulohy = konfiguracia.get(uloha, {})

        # Zlúčenie predvolenej konfigurácie s konfiguráciou špecifickou pre úlohu
        konfiguracia_modelu = {**predvolena_konfiguracia, **konfiguracia_ulohy}

        if not konfiguracia_modelu:
             zapisovac.warning(f"⚠️ Nebola nájdená konfigurácia pre úlohu '{uloha}' ani predvolená konfigurácia. Používa sa núdzová konfigurácia.")
             # Núdzová konfigurácia, ak zlyhá načítanie aj predvolenej
             return ChatGroq(
                 model="llama-3.1-70b-versatile", # Alebo iný spoľahlivý model
                 api_key=os.environ.get("GROQ_API_KEY"),
                 temperature=0.1,
                 max_retries=2,
             )

        return ChatGroq(
            model=konfiguracia_modelu["name"],
            api_key=os.environ.get("GROQ_API_KEY"),
            temperature=konfiguracia_modelu["temperature"],
            max_retries=konfiguracia_modelu["max_retries"],
        )
    except Exception as e:
        zapisovac.error(f"❌ Chyba pri inicializácii LLM pre úlohu '{uloha}': {str(e)}")
        # Núdzová konfigurácia pri akejkoľvek chybe
        return ChatGroq(
            model="llama-3.1-70b-versatile",
            api_key=os.environ.get("GROQ_API_KEY"),
            temperature=0.1,
            max_retries=2,
        )


def ziskaj_konfiguraciu_generovania_obrazkov(uloha: str = "image_generation") -> dict:
    """Vráti konfiguráciu pre generovanie obrázkov."""
    try:
        konfiguracia = nacitaj_konfiguraciu_modelov()
        img_gen_config = konfiguracia.get(uloha)
        if img_gen_config is None:
            raise KeyError(f"Konfigurácia pre '{uloha}' nebola nájdená.")
        return img_gen_config
    except Exception as e:
        zapisovac.error(f"❌ Chyba pri načítaní konfigurácie generovania obrázkov: {str(e)}")
        # Núdzová konfigurácia
        return {
            "provider": "together",
            "name": "stabilityai/stable-diffusion-xl-1024-v1-0", # Príklad fallback modelu
            "width": 1024,
            "height": 1024,
            "steps": 20,
            "n": 1,
            "response_format": "b64_json",
        }
