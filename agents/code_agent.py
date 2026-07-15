# ============================================================
# code_agent.py — Category B: Code Generation and Debugging
# ============================================================
# Runs LOCALLY using Ollama (qwen2.5:0.5b).
# Generates a Python function that checks if a number is prime.
# ============================================================

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "qwen2.5:0.5b"


def run(task_description: str) -> str:
    """Generates Python code from a plain-English task description."""
    prompt = f"""You are a Python code generation specialist.
Write clean, working Python code for the following task.
Return ONLY the Python code, no explanations, no markdown.

TASK: {task_description}

Python code:"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
        timeout=120
    )

    result = response.json().get("response", "").strip()

    # Strip markdown code fences if the model added them anyway
    if result.startswith("```"):
        lines = result.split("\n")
        result = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return result
