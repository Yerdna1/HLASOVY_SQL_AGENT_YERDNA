"""Nástroj na kreslenie Plotly grafov."""

import chainlit as cl
import plotly
from apka.widgets.spolocne import zapisovac

definicia_nakresli_plotly_graf = {
    "name": "nakresli_plotly_graf",
    "description": "Nakreslí Plotly graf na základe poskytnutej JSON figúry a zobrazí ho spolu so sprievodnou správou.",
    "parameters": {
        "type": "object",
        "properties": {
            "sprava": {
                "type": "string",
                "description": "Správa, ktorá sa má zobraziť vedľa grafu",
            },
            "plotly_json_fig": {
                "type": "string",
                "description": "JSON reťazec reprezentujúci Plotly figúru, ktorá sa má nakresliť",
            },
        },
        "required": ["sprava", "plotly_json_fig"],
    },
}


async def spracuj_nakreslenie_plotly_grafu(sprava: str, plotly_json_fig):
    """Spracuje požiadavku na nakreslenie Plotly grafu."""
    try:
        zapisovac.info(f"🎨 Kreslí sa Plotly graf so správou: {sprava}")
        figura = plotly.io.from_json(plotly_json_fig)
        elementy = [cl.Plotly(name="chart", figure=figura, display="inline")]
        await cl.Message(content=sprava, elements=elementy).send()
        zapisovac.info(f"💡 Plotly graf úspešne zobrazený.")
    except Exception as e:
        zapisovac.error(f"❌ Chyba pri kreslení Plotly grafu: {str(e)}")
        return {"error": str(e)}


nakresli_plotly_graf = (definicia_nakresli_plotly_graf, spracuj_nakreslenie_plotly_grafu)
