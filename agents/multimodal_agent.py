# ============================================================
# multimodal_agent.py — Category E: Multimodal Tasks
# ============================================================
# Runs on the CLOUD using GPT-4o (vision capable).
# Local SLMs cannot process images — this MUST go to cloud.
# Given a screenshot, describes the error shown.
# ============================================================

import base64
import openai


def encode_image(image_path: str) -> str:
    """Reads an image file and converts it to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def run(image_path: str, client: openai.OpenAI) -> dict:
    """Sends an image to GPT-4o and asks it to identify the issue shown."""
    base64_image = encode_image(image_path)
    ext = image_path.split(".")[-1].lower()
    mime_type = f"image/{ext}" if ext != "jpg" else "image/jpeg"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "This is a screenshot. Identify any errors or issues shown. Describe what is wrong and suggest a fix in 2-3 sentences."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                    }
                ]
            }
        ],
        max_tokens=300
    )

    return {
        "response": response.choices[0].message.content.strip(),
        "tokens_used": response.usage.total_tokens
    }
