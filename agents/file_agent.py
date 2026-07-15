# ============================================================
# file_agent.py — Category A: File and Log Analysis
# ============================================================
# Runs LOCALLY using Ollama (qwen2.5:0.5b).
# Reads a log file and extracts error-level events.
# ============================================================

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "qwen2.5:0.5b"


def run(log_content: str) -> str:
    """Reads log content, extracts ERROR-level lines, summarises root cause."""
    prompt = f"""You are a log analysis specialist.
Read the following server log and extract ONLY the ERROR-level lines.
For each error, state the timestamp and what went wrong.
Then in one sentence summarise the main issue.

LOG:
{log_content}

Respond in this format:
ERRORS FOUND:
- [timestamp]: [what went wrong]

ROOT CAUSE SUMMARY:
[one sentence]"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
        timeout=120
    )
    return response.json().get("response", "").strip()
