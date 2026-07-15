# ============================================================
# planning_agent.py — Category C: Planning and Task Decomposition
# ============================================================
# Runs LOCALLY using Ollama (qwen2.5:0.5b).
# Breaks down a high-level goal into ordered subtasks.
# ============================================================

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "qwen2.5:0.5b"


def run(goal: str) -> str:
    """Decomposes a high-level goal into a numbered list of subtasks."""
    prompt = f"""You are a software project planning specialist.
Break down the following high-level goal into a clear, ordered list of subtasks.
Number each subtask. Be specific and practical.
Keep each subtask to one sentence.

GOAL: {goal}

SUBTASKS:"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
        timeout=120
    )
    return response.json().get("response", "").strip()
