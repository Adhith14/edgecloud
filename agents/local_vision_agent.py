# ============================================================
# local_vision_agent.py — Category E, LOCAL vision
# ============================================================
# Runs a vision-capable model locally via Ollama (llava,
# qwen2.5-vl). Unlike text models, images must be passed as
# base64 in an "images" array on the chat endpoint — they
# cannot be embedded in the prompt string.
# ============================================================

import base64
import requests
from config import OLLAMA_CHAT_URL, LOCAL_VISION_MODEL, LOCAL_TIMEOUT


def _encode(image_path: str) -> str:
    """Reads an image file and returns it base64-encoded."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def run(task_description: str, image_path: str) -> str:
    """
    Sends an image plus a task instruction to the local vision model.

    Args:
        task_description: what to do with the image
        image_path:       path to the image file on disk

    Returns:
        The model's text response.
    """
    payload = {
        "model": LOCAL_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": task_description,
                "images": [_encode(image_path)]
            }
        ],
        "stream": False
    }

    response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=LOCAL_TIMEOUT)
    data = response.json()

    # The chat endpoint nests the reply under message.content
    return data.get("message", {}).get("content", "").strip()