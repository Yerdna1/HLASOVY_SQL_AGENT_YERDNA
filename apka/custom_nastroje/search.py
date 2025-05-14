"""Internet search tool using Tavily API."""

"""Internet search tool using Tavily API."""

"""Internet search tool using Tavily API."""

import os
import chainlit as cl
from tavily import TavilyClient # Import TavilyClient
from ultravox_client.session import ClientToolResult # Ensure correct import
from apka.widgets.LLM_modely import ziskaj_llm
# Assuming logger is defined elsewhere or replacing with standard logging if needed
# from utils.db_utils import logger # This might be incorrect if logger isn't there
from apka.widgets.spolocne import zapisovac as logger # Using the logger from spolocne like in other tools

internet_search_def = {
    "name": "internet_search",
    "description": "Performs an internet search using the Tavily API.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up on the internet (e.g., 'What's the weather like in Madrid tomorrow?').",
            },
        },
        "required": ["query"],
    },
}


# Initialize Tavily client using API key from environment
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    logger.error("❌ TAVILY_API_KEY not found in environment variables.")
    # Handle the case where the key is missing, maybe raise an error or use a dummy client
    tavily_client = None
else:
    tavily_client = TavilyClient(api_key=tavily_api_key)


async def internet_search_handler(query: str) -> str | dict: # Return string on error, dict on success
    """Executes an internet search using the Tavily API and returns the result."""
    if not tavily_client:
        error_msg = "Tavily client not initialized due to missing API key."
        logger.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg).send()
        return ClientToolResult(result=f"Error: {error_msg}") # Already wrapped

    try:
        logger.info(f"🕵 Performing internet search for query: '{query}'")
        # Use the initialized client
        response = tavily_client.search(query=query, search_depth="basic") # Using basic search depth

        results = response.get("results", [])
        if not results:
            no_results_msg = f"No results found for '{query}'."
            await cl.Message(content=no_results_msg).send()
            return ClientToolResult(result=no_results_msg) # Already wrapped

        formatted_results = "\n".join(
            [
                f"{i+1}. [{result['title']}]({result['url']})\n{result['content'][:200]}..."
                for i, result in enumerate(results)
            ]
        )

        message_content = f"Search Results for '{query}':\n\n{formatted_results}"
        await cl.Message(content=message_content).send()

        logger.info(f"📏 Search results for '{query}' retrieved successfully.")
        # Return the raw results dictionary as expected by the calling code (based on previous logs)
        # The Ultravox SDK expects a string or a specific ClientToolResult object.
        # Let's return a summary string for now, as returning the full dict might be too large.
        result_str = f"Found {len(results)} results. First result: {results[0]['title']}"
        return ClientToolResult(result=result_str) # Already wrapped
        # return response["results"] # Returning the full dict caused the NoneType error before
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error performing internet search: {error_str}")
        await cl.Message(content=f"An error occurred while performing the search: {error_str}").send()
        return ClientToolResult(result=f"Error during search: {error_str}") # Already wrapped


internet_search = (internet_search_def, internet_search_handler)
