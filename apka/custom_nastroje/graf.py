import chainlit as cl
import plotly.graph_objects as go # Import graph_objects
import os
import json
from datetime import datetime
from apka.widgets.spolocne import zapisovac
from ultravox_client.session import ClientToolResult # Import ClientToolResult from specific module

# Create directory for storing graphs if it doesn't exist
GRAPHS_DIR = "static/graphs"
os.makedirs(GRAPHS_DIR, exist_ok=True)

definicia_nakresli_plotly_graf = {
    "name": "nakresli_plotly_graf",
    "description": "Nakreslí jednoduchý stĺpcový Plotly graf na základe poskytnutých dát (napr. autori a počet kníh) a zobrazí ho spolu so sprievodnou správou. Dáta by mali byť získané z predchádzajúceho kroku (napr. SQL dotaz).",
    "parameters": {
        "type": "object",
        "properties": {
            "sprava": {
                "type": "string",
                "description": "Správa, ktorá sa má zobraziť nad grafom (napr. 'Počet kníh podľa autora').",
            },
            "x_data": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Zoznam hodnôt pre os X (napr. mená autorov).",
            },
            "y_data": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Zoznam číselných hodnôt pre os Y (napr. počty kníh). Musí mať rovnakú dĺžku ako x_data.",
            },
            "x_title": {
                "type": "string",
                "description": "Názov osi X (napr. 'Autor').",
            },
            "y_title": {
                "type": "string",
                "description": "Názov osi Y (napr. 'Počet kníh').",
            },
            "y_range_min": {
                "type": "number",
                "description": "Voliteľná minimálna hodnota pre rozsah osi Y.",
            },
            "y_range_max": {
                "type": "number",
                "description": "Voliteľná maximálna hodnota pre rozsah osi Y.",
            },
             "nazov_suboru": {
                "type": "string",
                "description": "Voliteľný názov súboru pre uloženie grafu (bez prípony). Ak nie je poskytnutý, vygeneruje sa automaticky.",
             },
        },
        "required": ["sprava"], # Only message is strictly required now
    },
}


# Modify function signature to accept a single dictionary argument
async def spracuj_nakreslenie_plotly_grafu(params: dict) -> str:
    """Spracuje požiadavku na nakreslenie Plotly grafu z poskytnutých dát (ak sú k dispozícii) a uloží ho ako súbor."""

    # Extract parameters from the dictionary, providing defaults
    sprava = params.get("sprava", "Graf") # Default title if 'sprava' is missing
    x_data = params.get("x_data")
    y_data = params.get("y_data")
    x_title = params.get("x_title", "Os X")
    y_title = params.get("y_title", "Os Y")
    y_range_min = params.get("y_range_min") # Extract new params
    y_range_max = params.get("y_range_max") # Extract new params
    nazov_suboru = params.get("nazov_suboru")

    # Use default data if specific data is missing or invalid format (basic check)
    if not isinstance(x_data, list) or not x_data:
        x_data = ["N/A"]
    if not isinstance(y_data, list) or not y_data:
         # Ensure y_data matches x_data length if defaulted
        y_data = [0] * len(x_data) 

    # Check for length mismatch
    if len(x_data) != len(y_data):
        # Define error_msg before using it
        error_msg = f"Dĺžka x_data ({len(x_data)}) sa nezhoduje s dĺžkou y_data ({len(y_data)})."
        zapisovac.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg, type="error").send()
        return ClientToolResult(result=f"Error: {error_msg}") # Wrap in ClientToolResult

    try:
        # Log the received parameters dictionary for debugging
        zapisovac.info(f"🎨 Kreslí sa Plotly graf s parametrami: {params}")

        # Create Plotly figure from extracted data
        figura = go.Figure(data=[go.Bar(x=x_data, y=y_data)])
        
        # More explicit layout configuration
        layout_args = {
            "title": sprava,
            "xaxis": {
                "title": x_title, # Explicitly set title within xaxis dict
                'categoryorder':'total descending'
            },
            "yaxis": {
                "title": y_title # Explicitly set title within yaxis dict
            }
        }
        # Add y-axis range if provided
        if y_range_min is not None and y_range_max is not None:
            try:
                # Add range to the yaxis dictionary
                if "yaxis" not in layout_args: layout_args["yaxis"] = {} # Ensure yaxis dict exists
                layout_args["yaxis"]["range"] = [float(y_range_min), float(y_range_max)]
            except (ValueError, TypeError):
                 zapisovac.warning(f"Neplatné hodnoty pre y_range: min={y_range_min}, max={y_range_max}. Použije sa automatický rozsah.")

        figura.update_layout(**layout_args)

        # Generate filename if not provided
        # Use a distinct variable name here to avoid potential confusion later
        final_nazov_suboru_calc = nazov_suboru 
        if not final_nazov_suboru_calc:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_nazov_suboru_calc = f"graf_{timestamp}"
        
        # Ensure filename has no extension
        final_nazov_suboru_calc = os.path.splitext(final_nazov_suboru_calc)[0]
        
        # Full path for the HTML file
        html_cesta = os.path.join(GRAPHS_DIR, f"{final_nazov_suboru_calc}.html")
        
        # Log right before saving
        zapisovac.info(f"💾 Pripravuje sa na uloženie grafu ako HTML: {html_cesta} (Názov súboru: {final_nazov_suboru_calc})")

        # Save as HTML
        figura.write_html(html_cesta, include_plotlyjs=True, full_html=True)
        zapisovac.info(f"💾 Graf uložený ako HTML: {html_cesta}")
        
        # Create a file element for the saved HTML
        file_element = cl.File(
            name=f"{final_nazov_suboru_calc}.html", # Use calculated name
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

        # Return a success string wrapped in ClientToolResult
        return ClientToolResult(result=f"Graf úspešne vygenerovaný a uložený ako {final_nazov_suboru_calc}.html. Zobrazuje sa v chate.")

    except json.JSONDecodeError as json_err:
        # Removed JSON parsing error handling as we now generate the figure
        pass # Added pass to fix indentation error
    except Exception as e:
        error_msg = f"Chyba pri generovaní alebo ukladaní Plotly grafu: {str(e)}"
        zapisovac.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg, type="error").send()
        return ClientToolResult(result=f"Error: {error_msg}") # Wrap in ClientToolResult


nakresli_plotly_graf = (definicia_nakresli_plotly_graf, spracuj_nakreslenie_plotly_grafu)
