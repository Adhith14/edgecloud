# ============================================================
# planning_agent.py — Category C: Planning and Task Decomposition
# ============================================================
# Runs LOCALLY using Ollama (qwen2.5:0.5b).
# Breaks down a high-level goal into ordered subtasks.
# ============================================================

import requests
from config import OLLAMA_URL, LOCAL_MODEL, LOCAL_TIMEOUT

def run(task_description: str, context: str) -> str:
    """Generic planning specialist — the task tells it what to do."""
    prompt = f"""You are a planning and task decomposition specialist.

TASK: {task_description}

CONTEXT:
{context}

Produce a clear, numbered, practical response to the task."""

    response = requests.post(
        OLLAMA_URL,
        json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
        timeout=LOCAL_TIMEOUT
    )
    return response.json().get("response", "").strip()