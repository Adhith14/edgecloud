# ============================================================
# file_agent.py — Category A: File and Log Analysis
# ============================================================
# Runs LOCALLY using Ollama (qwen2.5:0.5b).
# Reads a log file and extracts error-level events.
# ============================================================

import requests
from config import OLLAMA_URL, LOCAL_MODEL, LOCAL_TIMEOUT


def run(task_description: str, content: str) -> str:
    """Generic file/log specialist — the task tells it what to do."""
    prompt = f"""You are a file and log analysis specialist.

TASK: {task_description}

INPUT:
{content}

Complete the task accurately using only the input above."""

    response = requests.post(
        OLLAMA_URL,
        json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
        timeout=LOCAL_TIMEOUT
    )
    return response.json().get("response", "").strip()