# ============================================================
# document_agent.py — Category D: Document Processing
# ============================================================
# Runs LOCALLY using Ollama (qwen2.5:0.5b).
# Summarises a short document in 2-3 sentences.
# ============================================================

import requests
from config import OLLAMA_URL, LOCAL_MODEL, LOCAL_TIMEOUT


def run(task_description: str, content: str) -> str:
    """Generic document specialist — the task tells it what to do."""
    prompt = f"""You are a document processing specialist.

TASK: {task_description}

DOCUMENT:
{content}

Complete the task accurately using only the document above."""

    response = requests.post(
        OLLAMA_URL,
        json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
        timeout=LOCAL_TIMEOUT
    )
    return response.json().get("response", "").strip()
