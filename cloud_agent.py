# ============================================================
# cloud_agent.py — Cloud-Only Baseline
# ============================================================
# Used when SYSTEM_MODE = "cloud_only".
# Every task goes directly to the cloud model, with no local
# agents involved. This is the performance/cost ceiling that
# the other two systems are compared against.
# ============================================================

import openai
from config import CLOUD_ONLY_MODEL, CLOUD_TEMPERATURE


def run(task_description: str, task_input: str, client: openai.OpenAI, is_code_task: bool = False) -> dict:
    code_note = "\nReturn ONLY runnable code. No explanations, no markdown fences.\n" if is_code_task else ""
    
    """
    Sends a task straight to the cloud model.

    Returns dict with 'output' and 'tokens_used'.
    """
    prompt = f"""You are an expert assistant.

TASK: {task_description}
{code_note}
INPUT:
{task_input}

Complete the task accurately using only the input above."""

    response = client.chat.completions.create(
        model=CLOUD_ONLY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=CLOUD_TEMPERATURE
    )

    output = response.choices[0].message.content.strip()

    # The cloud model tends to wrap code in markdown fences and add prose.
    # For code tasks this breaks exec()-based scoring, so extract the code block.
    if is_code_task and "```" in output:
        output = (output.replace("\u2019", "'").replace("\u2018", "'")
                        .replace("\u201c", '"').replace("\u201d", '"'))
        parts = output.split("```")
        # parts[1] is the first fenced block; drop a leading language tag line
        if len(parts) >= 2:
            block = parts[1]
            lines = block.split("\n")
            if lines and lines[0].strip().lower() in ("python", "py", "sql", "json", ""):
                block = "\n".join(lines[1:])
            output = block.strip()

    return {
        "output": output,
        "tokens_used": response.usage.total_tokens
    }