# ============================================================
# document_agent.py — Category D: Document Processing
# ============================================================
# Runs LOCALLY using Ollama (qwen2.5:0.5b).
# Summarises a short document in 2-3 sentences.
# ============================================================

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
LOCAL_MODEL = "qwen2.5:0.5b"


def run(document_content: str) -> str:
    """Summarises a document's text content in 2-3 sentences."""
    prompt = f"""You are a document summarisation specialist.
Read the following document and write a clear summary in exactly 2-3 sentences.
Cover the main point, one key detail, and the core challenge or conclusion.

DOCUMENT:
{document_content}

SUMMARY:"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
        timeout=120
    )
    return response.json().get("response", "").strip()
