import chainlit as cl
import plotly
import os
import json
from datetime import datetime
from apka.widgets.spolocne import zapisovac

# Create directory for storing graphs if it doesn't exist
GRAPHS_DIR = "static/graphs"
os.makedirs(GRAPHS_DIR, exist_ok=True)

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
            "nazov_suboru": {
                "type": "string",
                "description": "Voliteľný názov súboru pre uloženie grafu (bez prípony). Ak nie je poskytnutý, vygeneruje sa automaticky.",
            },
        },
        "required": ["sprava", "plotly_json_fig"],
    },
}


async def spracuj_nakreslenie_plotly_grafu(sprava: str, plotly_json_fig, nazov_suboru=None):
    """Spracuje požiadavku na nakreslenie Plotly grafu a uloží ho ako súbor."""
    try:
        zapisovac.info(f"🎨 Kreslí sa Plotly graf so správou: {sprava}")
        
        # Parse the JSON string to create Plotly figure
        figura = plotly.io.from_json(plotly_json_fig)
        
        # Generate filename if not provided
        if not nazov_suboru:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nazov_suboru = f"graf_{timestamp}"
        
        # Ensure filename has no extension
        nazov_suboru = os.path.splitext(nazov_suboru)[0]
        
        # Full path for the HTML file
        html_cesta = os.path.join(GRAPHS_DIR, f"{nazov_suboru}.html")
        
        # Save as HTML
        figura.write_html(html_cesta, include_plotlyjs=True, full_html=True)
        zapisovac.info(f"💾 Graf uložený ako HTML: {html_cesta}")
        
        # Create a file element for the saved HTML
        file_element = cl.File(
            name=f"{nazov_suboru}.html",
            path=html_cesta,
            display="inline"
        )
        
        # Create a Plotly element for inline display
        plotly_element = cl.Plotly(
            name="graf",
            figure=figura,
            display="inline"
        )
        
        # Send the message with both elements
        await cl.Message(
            content=sprava,
            elements=[plotly_element, file_element]
        ).send()
        
        zapisovac.info(f"💡 Plotly graf úspešne zobrazený a uložený ako stiahnuteľný súbor.")
        
        return {
            "success": True, 
            "file_path": html_cesta, 
            "web_path": f"/static/graphs/{nazov_suboru}.html"
        }
        
    except Exception as e:
        zapisovac.error(f"❌ Chyba pri kreslení alebo ukladaní Plotly grafu: {str(e)}")
        return {"error": str(e)}


nakresli_plotly_graf = (definicia_nakresli_plotly_graf, spracuj_nakreslenie_plotly_grafu)