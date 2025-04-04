"""Spoločné utility a konfigurácie."""

import os
import logging
from dotenv import load_dotenv
from together import Together
from tavily import TavilyClient

# Načítanie environmentálnych premenných
load_dotenv()

# Nastavenie logovania
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
zapisovac = logging.getLogger(__name__)

# Adresár pre dočasné súbory (scratchpad)
# Cesta je relatívna k tomuto súboru (apka/widgets/spolocne.py)
scratch_pad_adresar = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scratchpad"))
os.makedirs(scratch_pad_adresar, exist_ok=True)

# Inicializácia klientov
# Názvy klientov ponechané pre jasnosť, odkiaľ pochádzajú
together_client = Together(api_key=os.environ.get("TOGETHER_API_KEY"))
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
