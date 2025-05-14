"""Image generation tool."""

"""Image generation tool."""

"""Image generation tool."""

import base64
import os

import chainlit as cl
import together
from langchain.prompts import PromptTemplate
from ultravox_client.session import ClientToolResult # Ensure correct import
from pydantic import BaseModel, Field
from apka.widgets.LLM_modely import ziskaj_llm
# Assuming logger is defined elsewhere or replacing with standard logging if needed
# from utils.db_utils import logger # This might be incorrect if logger isn't there
from apka.widgets.spolocne import zapisovac as logger, scratch_pad_adresar# Using the logger from spolocne like in other tools

from apka.widgets.LLM_modely import ziskaj_konfiguraciu_generovania_obrazkov
# Initialize Together AI client
together_client = together.Together(api_key=os.getenv('TOGETHER_API_KEY'))



class EnhancedPrompt(BaseModel):
    """Class for the text prompt"""

    content: str = Field(
        ...,
        description="The enhanced text prompt to generate an image",
    )


generate_image_def = {
    "name": "generate_image",
    "description": "Generates an image based on a given prompt.",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt to generate an image (e.g., 'A beautiful sunset over the mountains')",
            },
        },
        "required": ["prompt"],
    },
}


# Modify function signature to accept a single dictionary argument
async def generate_image_handler(params: dict) -> str:
    """Generates an image based on a given prompt using the Together API."""
    # Extract prompt from the dictionary
    prompt = params.get("prompt")
    if not prompt or not isinstance(prompt, str):
        error_msg = "Chyba: Chýbajúci alebo neplatný parameter 'prompt'."
        logger.error(f"❌ {error_msg}")
        await cl.Message(content=error_msg, type="error").send()
        return ClientToolResult(result=f"Error: {error_msg}") # Wrap in ClientToolResult

    try:
        logger.info(f"✨ Enhancing prompt: '{prompt}'")

        llm = ziskaj_llm("image_prompt")

        structured_llm = llm.with_structured_output(EnhancedPrompt)

        system_template = """
        Enhance the given prompt the best prompt engineering techniques such as providing context, specifying style, medium, lighting, and camera details if applicable. If the prompt requests a realistic style, the enhanced prompt should include the image extension .HEIC.

        # Original Prompt
        {prompt}

        # Objective
        **Enhance Prompt**: Add relevant details to the prompt, including context, description, specific visual elements, mood, and technical details. For realistic prompts, add '.HEIC' in the output specification.

        # Example
        "realistic photo of a person having a coffee" -> "photo of a person having a coffee in a cozy cafe, natural morning light, shot with a 50mm f/1.8 lens, 8425.HEIC"
        """

        prompt_template = PromptTemplate(
            input_variables=["prompt"],
            template=system_template,
        )

        chain = prompt_template | structured_llm
        enhanced_prompt = chain.invoke({"prompt": prompt}).content

        logger.info(f"🌄 Generating image based on prompt: '{enhanced_prompt}'")

        # Get image generation configuration
        img_config = ziskaj_konfiguraciu_generovania_obrazkov()
        response = together_client.images.generate(
            prompt=prompt,
            model=img_config["name"],
            width=img_config["width"],
            height=img_config["height"],
            steps=img_config["steps"],
            n=img_config["n"],
            response_format=img_config["response_format"],
        )

        b64_image = response.data[0].b64_json
        image_data = base64.b64decode(b64_image)

        img_path = os.path.join(scratch_pad_adresar, "generated_image.jpeg")
        with open(img_path, "wb") as f:
            f.write(image_data)

        logger.info(f"🖼️ Image generated and saved successfully at {img_path}")
        image = cl.Image(path=img_path, name="Generated Image", display="inline")
        await cl.Message(
            content=f"Image generated with the prompt '{enhanced_prompt}'",
            elements=[image],
        ).send()

        # Return success string wrapped in ClientToolResult
        return ClientToolResult(result=f"Image successfully generated for prompt: '{enhanced_prompt}' and saved to {img_path}")

    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error generating image: {error_str}")
        # Send error message to Chainlit UI if possible
        try:
            await cl.Message(content=f"An error occurred while generating the image: {error_str}", type="error").send()
        except Exception as cl_err:
            logger.error(f"Failed to send error message to Chainlit UI: {cl_err}")
        # Return error string wrapped in ClientToolResult
        return ClientToolResult(result=f"Error generating image: {error_str}") # Already wrapped


generate_image = (generate_image_def, generate_image_handler)
