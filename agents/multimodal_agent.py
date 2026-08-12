# ============================================================
# multimodal_agent.py — Category E: Multimodal Tasks
# ============================================================
# Runs on the CLOUD using GPT-4o (vision capable).
# Local SLMs cannot process images — this MUST go to cloud.
# Given a screenshot, describes the error shown.
# ============================================================

import base64
import openai
from config import CLOUD_VISION_MODEL

def encode_image(image_path: str) -> str:
    """Reads an image file and converts it to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def run(image_path: str, client: openai.OpenAI, task_description: str = None) -> dict:
    """
    Sends an image to the cloud vision model with a task instruction.

    Args:
        image_path:       path to the image file
        client:           initialised OpenAI client
        task_description: what to do with the image. If omitted, falls back
                          to a generic description request.

    Returns:
        dict with 'response' text and 'tokens_used'
    """
    base64_image = encode_image(image_path)
    ext = image_path.split(".")[-1].lower()
    mime_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"

    response = client.chat.completions.create(
        model=CLOUD_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": task_description or "Describe this image and identify anything notable or incorrect in it."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                    }
                ]
            }
        ],
        max_tokens=600
    )

    return {
        "response": response.choices[0].message.content.strip(),
        "tokens_used": response.usage.total_tokens
    }

    return {
        "response": response.choices[0].message.content.strip(),
        "tokens_used": response.usage.total_tokens
    }
