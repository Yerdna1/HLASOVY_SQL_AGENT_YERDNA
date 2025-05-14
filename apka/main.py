"""
Hlavný súbor aplikácie Chainlit pre real-time asistenta s Ultravox.
"""

import traceback
import chainlit as cl
# Removed Select import as LLM provider is handled by Ultravox
from chainlit.input_widget import TextInput
from chainlit.logger import logger
import requests
import datetime
# import calendar # Removed unused import
# import time # Removed unused import
import os
import json
import asyncio # Added for Ultravox async operations
from dotenv import load_dotenv # Na explicitné načítanie .env

# Import Ultravox client
import ultravox_client as uv

# Načítanie environmentálnych premenných
load_dotenv()

# Import nástrojov - predpokladáme, že tento import zostáva alebo bude upravený
from apka.custom_nastroje import nastroje

# --- Helper funkcia na maskovanie kľúčov ---
def mask_api_key(api_key: str | None) -> str:
    """Maskuje API kľúč, zobrazí prvé 4 a posledné 4 znaky."""
    if not api_key or len(api_key) < 9:
        return "Nenastavený alebo príliš krátky"
    return f"{api_key[:4]}...{api_key[-4:]}"

# --- Removed OpenAI Cost Fetching ---

# Placeholder for Ultravox API Key and Endpoint - replace with actual values from .env
ULTRAVOX_API_KEY = os.getenv("ULTRAVOX_API_KEY", "YOUR_ULTRAVOX_API_KEY_HERE") # Replace placeholder if needed
ULTRAVOX_API_ENDPOINT = os.getenv("ULTRAVOX_API_ENDPOINT", "https://api.ultravox.ai/api/calls") # Default endpoint

# --- Helper function for REST API call ---
def create_ultravox_call_session(api_key: str, endpoint_url: str, tools_config: list) -> str | None:
    """Makes a REST API call to Ultravox to create a call session and returns the joinUrl."""
    if not api_key or api_key == "YOUR_ULTRAVOX_API_KEY_HERE":
        logger.error("❌ Ultravox API Key not configured in .env.")
        return None

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    # Prepare tool definitions for the API call
    # Assuming 'nastroje' contains tuples like ({'name': 'tool_name', ...}, handler)
    # We need to format them according to Ultravox API specs
    selected_tools = []
    for tool_def, _ in tools_config:
        tool_name = tool_def.get("name")
        if tool_name:
            # Mark as client-side tool for SDK handling
            # Rename 'name' to 'modelToolName' and move 'parameters' under 'dynamicParameters'
            api_tool_def = tool_def.copy()
            if "name" in api_tool_def:
                api_tool_def["modelToolName"] = api_tool_def.pop("name")
            if "parameters" in api_tool_def:
                original_params = api_tool_def.pop("parameters")
                dynamic_params_list = []
                properties = original_params.get("properties", {})
                required_list = original_params.get("required", [])

                for param_name, param_schema in properties.items():
                    dynamic_params_list.append({
                        "name": param_name,
                        "location": 4, # For client-side tools
                        "schema": param_schema, # Schema for the individual parameter
                        "required": param_name in required_list
                    })

                if dynamic_params_list:
                    api_tool_def["dynamicParameters"] = dynamic_params_list

            api_tool_def["client"] = {}

            # Structure according to API error message: list of objects with EITHER toolName OR temporaryTool
            # Since we define inline, use only temporaryTool
            selected_tools.append({
                "temporaryTool": api_tool_def
            })
        else:
            logger.warning(f"Skipping tool due to missing 'name': {tool_def}")

    payload = {
        "model": "fixie-ai/ultravox-70B", # Or configure as needed
        # "voice": "...", # Removed voice setting to use default
        "selectedTools": selected_tools,
        # Add other necessary parameters like systemPrompt, etc.
        "systemPrompt": "You are a helpful voice assistant.",
    }
    logger.info(f"Creating Ultravox call with payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(endpoint_url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        join_url = data.get("joinUrl")
        if not join_url:
            logger.error(f"❌ Failed to get joinUrl from Ultravox API response: {data}")
            return None
        logger.info(f"✅ Successfully created Ultravox call session. Join URL obtained.")
        return join_url
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error creating Ultravox call session: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response status: {e.response.status_code}")
             try:
                 logger.error(f"Response body: {e.response.text}")
             except Exception:
                 pass # Ignore if response body cannot be read
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error during Ultravox API call: {traceback.format_exc()}")
        return None

# --- End Helper function ---


# --- End Helper function ---


# Store join_url in session for connect button
def store_join_url(join_url: str | None):
    if join_url:
        cl.user_session.set("ultravox_join_url", join_url)
    else:
        cl.user_session.set("ultravox_join_url", None)

@cl.on_chat_start
async def start():
    """Initializes chat, prepares Ultravox session, and displays settings/buttons."""
    # Load necessary env vars
    db_path = os.getenv("DB_DATABASE", "Nenájdené v .env")
    # Removed OpenAI/Gemini/etc key loading for simplicity, add back if needed
    groq_key = os.getenv("GROQ_API_KEY") # Keep if tools still use it internally
    ultravox_key = os.getenv("ULTRAVOX_API_KEY")

    # Define Chat Settings (Simplified)
    settings = await cl.ChatSettings(
        [
            # Removed LLMProvider selection as Ultravox manages the model
            TextInput(id="DBPath", label="Cesta k databáze", initial=db_path, disabled=True),
            TextInput(id="GroqKey", label="Groq Key (for tools)", initial=mask_api_key(groq_key), disabled=True),
            TextInput(id="UltravoxKey", label="Ultravox Key", initial=mask_api_key(ultravox_key), disabled=True),
        ]
    ).send()

    # --- Initialize Ultravox Session (without connecting) ---
    try:
        session = uv.UltravoxSession()
        cl.user_session.set("ultravox_session", session)
        logger.info("UltravoxSession initialized (but not connected).")

        # Register Event Handlers
        @session.on("status")
        def on_status():
            status = session.status
            logger.info(f"Ultravox Status: {status}")
            # Optional: Update UI based on status
            if status == uv.UltravoxSessionStatus.DISCONNECTED:
                 # Handle disconnection if needed
                 # Ensure cleanup happens, potentially trigger done event if using one
                 logger.warning("Ultravox session disconnected.")
                 # done_event = cl.user_session.get("ultravox_done_event") # If using an event for waiting
                 # if done_event: done_event.set()
                 # Update button states if necessary
                 asyncio.create_task(update_connect_buttons(connected=False))
                 pass

        @session.on("transcripts")
        def on_transcript():
            # Process transcripts if needed (e.g., display in UI)
            # Note: This provides text, not audio chunks for playback
            if session.transcripts:
                 last_transcript = session.transcripts[-1]
                 # Example: Send transcript to Chainlit UI
                 # Need to manage message updates carefully if streaming transcripts
                 # asyncio.create_task(cl.Message(content=f"{last_transcript.speaker}: {last_transcript.text} ({'Final' if last_transcript.final else 'Partial'})").send())
                 logger.info(f"Transcript ({'Final' if last_transcript.final else 'Partial'}): {last_transcript.speaker} - {last_transcript.text}")


        @session.on("error")
        def on_error(error):
            logger.error(f"Ultravox Session Error: {error}", exc_info=error)
            asyncio.create_task(cl.ErrorMessage(content=f"Ultravox Error: {error}").send())
            # Consider cleanup or session reset here
            # done_event = cl.user_session.get("ultravox_done_event")
            # if done_event: done_event.set()


        # 4. Register Tool Implementations
        tool_implementations = {}
        for tool_def, handler in nastroje:
             tool_name = tool_def.get("name")
             if tool_name and callable(handler):
                 # Make handler async if it's not already, as SDK might expect awaitable
                 if not asyncio.iscoroutinefunction(handler):
                     # Simple wrapper to make sync function awaitable
                     async def async_handler_wrapper(sync_handler=handler, **kwargs):
                         # Consider running sync handler in executor if it's blocking
                         # loop = asyncio.get_running_loop()
                         # return await loop.run_in_executor(None, sync_handler, **kwargs)
                         return sync_handler(**kwargs)
                     tool_implementations[tool_name] = async_handler_wrapper
                 else:
                     tool_implementations[tool_name] = handler
             # Use modelToolName for registration key if available, otherwise original name
             sdk_tool_name = tool_def.get("modelToolName", tool_def.get("name"))
             if sdk_tool_name and callable(handler):
                 # Make handler async if it's not already, as SDK might expect awaitable
                 if not asyncio.iscoroutinefunction(handler):
                     # Simple wrapper to make sync function awaitable
                     async def async_handler_wrapper(sync_handler=handler, **kwargs):
                         # Consider running sync handler in executor if it's blocking
                         # loop = asyncio.get_running_loop()
                         # return await loop.run_in_executor(None, sync_handler, **kwargs)
                         return sync_handler(**kwargs)
                     tool_implementations[sdk_tool_name] = async_handler_wrapper
                 else:
                     tool_implementations[sdk_tool_name] = handler
             else:
                 logger.warning(f"Skipping invalid tool registration: {tool_def.get('name', 'N/A')}")

        if tool_implementations:
             session.register_tool_implementations(tool_implementations)
             logger.info(f"Registered tools: {list(tool_implementations.keys())}")

        # Do NOT join call automatically here
        logger.info("Ultravox setup complete. Ready to connect.")
        await update_connect_buttons(connected=False) # Show initial buttons

    except Exception as e:
        logger.error(f"❌ Failed to initialize Ultravox session: {traceback.format_exc()}")
        await cl.ErrorMessage(content=f"Error setting up Ultravox: {e}").send()
        cl.user_session.set("ultravox_session", None) # Ensure session is None if setup failed

    # --- End Ultravox Setup ---


# --- Connection Control Actions ---

async def update_connect_buttons(connected: bool):
    """Sends or updates the connection control buttons."""
    actions = [
        cl.Action(name="connect_ultravox", value="connect", label="📞 Connect", disabled=connected),
        cl.Action(name="disconnect_ultravox", value="disconnect", label="🔌 Disconnect", disabled=not connected),
        cl.Action(name="disconnect_ultravox", value="disconnect_x", label="❌ Stop", disabled=not connected) # Added Stop button
    ]
    status_msg = "Ultravox Connected" if connected else "Ultravox Disconnected"
    # Try to get existing message to update, otherwise send new
    msg = cl.user_session.get("connection_status_msg")
    content = f"**Status:** {status_msg}"
    if msg:
        msg.content = content
        msg.actions = actions
        await msg.update()
    else:
        msg = cl.Message(content=content, actions=actions)
        await msg.send()
        cl.user_session.set("connection_status_msg", msg)


@cl.action_callback("connect_ultravox")
async def on_connect_ultravox(action: cl.Action):
    """Handles the Connect button click."""
    await action.remove() # Remove button temporarily to prevent double clicks
    session: uv.UltravoxSession = cl.user_session.get("ultravox_session")

    if not session:
        await cl.ErrorMessage(content="Ultravox session not initialized properly.").send()
        await update_connect_buttons(connected=False) # Show buttons again
        return

    if session.status.is_live():
        await cl.Message(content="Already connected to Ultravox.").send()
        await update_connect_buttons(connected=True) # Ensure buttons reflect state
        return

    await cl.Message(content="Connecting to Ultravox...").send()

    # 1. Create Call Session via REST API
    join_url = create_ultravox_call_session(ULTRAVOX_API_KEY, ULTRAVOX_API_ENDPOINT, nastroje)

    if not join_url:
        await cl.ErrorMessage(content="Failed to create Ultravox call session. Please check API key and logs.").send()
        await update_connect_buttons(connected=False) # Show buttons again
        return

    # 2. Join the Call
    try:
        await session.join_call(join_url)
        logger.info("Attempted to join Ultravox call.")
        await cl.Message(content="✅ Ultravox Connected. Voice interaction might use system defaults.").send()
        await update_connect_buttons(connected=True)
    except Exception as e:
        logger.error(f"❌ Failed to join Ultravox call: {traceback.format_exc()}")
        await cl.ErrorMessage(content=f"Error joining Ultravox call: {e}").send()
        await update_connect_buttons(connected=False) # Show buttons again


@cl.action_callback("disconnect_ultravox")
async def on_disconnect_ultravox(action: cl.Action):
    """Handles the Disconnect button click."""
    await action.remove() # Remove button temporarily
    session: uv.UltravoxSession = cl.user_session.get("ultravox_session")

    if not session:
        await cl.ErrorMessage(content="Ultravox session not initialized.").send()
        await update_connect_buttons(connected=False) # Show buttons again
        return

    if not session.status.is_live():
        await cl.Message(content="Already disconnected from Ultravox.").send()
        await update_connect_buttons(connected=False) # Ensure buttons reflect state
        return

    await cl.Message(content="Disconnecting from Ultravox...").send()
    try:
        await session.leave_call()
        logger.info("Left Ultravox call via button.")
        await cl.Message(content="🔌 Ultravox Disconnected.").send()
        # Session status handler should update buttons, but we can force it
        await update_connect_buttons(connected=False)
    except Exception as e:
        logger.error(f"Error leaving Ultravox call via button: {e}")
        await cl.ErrorMessage(content=f"Error disconnecting: {e}").send()
        # Try to update buttons even on error
        await update_connect_buttons(connected=session.status.is_live())

# --- End Connection Control Actions ---



@cl.on_message
async def on_message(sprava: cl.Message):
    """Spracuje textovú správu od používateľa."""
    session: uv.UltravoxSession = cl.user_session.get("ultravox_session")
    if session and session.status.is_live():
        try:
            logger.info(f"Sending text to Ultravox: {sprava.content}")
            await session.send_text(sprava.content)
        except Exception as e:
            logger.error(f"Error sending text to Ultravox: {e}")
            await cl.ErrorMessage(content=f"Error sending message: {e}").send()
    else:
        logger.warning(f"Ultravox session not active (Status: {session.status if session else 'None'}). Cannot send text message.")
        await cl.Message(content="Ultravox session not active. Please connect first.").send()


@cl.on_audio_start
async def on_audio_start():
    """Handles audio start - Ultravox SDK manages connection after join_call."""
    logger.info("Audio recording started by Chainlit.")
    session: uv.UltravoxSession = cl.user_session.get("ultravox_session")
    if not session or not session.status.is_live():
        logger.warning("Ultravox session not active during audio start.")
        await cl.Message(content="Cannot start audio: Ultravox session not connected.").send()
        return False # Indicate Chainlit should not proceed
    # Mic is likely managed by the SDK internally
    logger.info("Ultravox SDK should be handling microphone input.")
    return True


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handles incoming audio chunk."""
    # !!! IMPORTANT LIMITATION !!!
    # The Ultravox Python SDK (based on examples) does not seem to have a public API
    # to accept raw audio chunks like this. It likely manages the microphone
    # directly via the underlying WebRTC library after join_call is initiated.
    # Therefore, this function cannot directly feed audio into the SDK.
    # The audio Chainlit captures here might be ignored by Ultravox.
    # logger.debug("Received audio chunk from Chainlit (likely ignored by Ultravox SDK).")
    pass # Cannot send chunk to Ultravox SDK


@cl.on_audio_end
@cl.on_chat_end
@cl.on_stop
async def on_end():
    """Handles end events, leaves the Ultravox call if connected."""
    logger.info("Received end event (audio/chat/stop).")
    session: uv.UltravoxSession = cl.user_session.get("ultravox_session")
    # Only try to leave if session exists and might be connected
    if session and session.status != uv.UltravoxSessionStatus.DISCONNECTED:
        logger.info("Leaving Ultravox call due to end event...")
        try:
            await session.leave_call()
            logger.info("Left Ultravox call via end event.")
        except Exception as e:
            logger.error(f"Error leaving Ultravox call via end event: {e}")
        # No finally block needed here as the status handler will clear the session if disconnect succeeds
    elif session:
         logger.info("Ultravox session already disconnected on end event.")
         cl.user_session.set("ultravox_session", None) # Ensure cleanup if already disconnected
    else:
        logger.info("No active Ultravox session found on end event.")
