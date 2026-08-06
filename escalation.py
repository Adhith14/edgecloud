# ============================================================
# escalation.py — Cloud Escalation (Dynamic Routing, Option A)
# ============================================================
# When a local agent's output scores below the threshold (or a
# code task fails execution), the same task is escalated to the
# cloud model for a better answer.
#
# NOTE ON CODE TASKS: the cloud model tends to wrap code in
# markdown fences and add explanatory prose. That breaks
# exec()-based scoring, so for execution-scored tasks we ask
# for bare code AND strip any fences that come back anyway.
# ============================================================

import openai
from config import CLOUD_ESCALATION_MODEL, CLOUD_TEMPERATURE


def _strip_code_fences(text: str) -> str:
    """
    Extracts the contents of the first markdown code block, if present.
    Handles both ```python ... ``` and bare ``` ... ``` forms.
    Returns the text unchanged if no fence is found.
    """
    if "```" not in text:
        return text

    parts = text.split("```")
    if len(parts) < 2:
        return text

    block = parts[1]
    lines = block.split("\n")

    # Drop a leading language tag line (e.g. "python", "sql")
    if lines and lines[0].strip().lower() in ("python", "py", "sql", "json", "javascript", "js", ""):
        block = "\n".join(lines[1:])

    return block.strip()


def escalate_to_cloud(task_description: str, task_input: str, client: openai.OpenAI,
                      is_code_task: bool = False) -> dict:
    """
    Sends a task that the local agent handled poorly to the cloud
    model for a stronger answer.

    Args:
        task_description: what the task is asking for
        task_input:       the data/content for the task
        client:           the initialised OpenAI client
        is_code_task:     True for execution-scored tasks — makes the
                          model return bare runnable code

    Returns:
        dict with 'output' (the cloud's answer) and 'tokens_used'
    """

    # Extra instruction so code tasks come back runnable, not prose-wrapped
    code_note = (
        "\nIMPORTANT: Return ONLY runnable code. No explanations, no commentary, "
        "no markdown fences. Use plain ASCII quotes and apostrophes.\n"
        if is_code_task else ""
    )

    prompt = f"""You are an expert assistant handling a task that a smaller
local model was unable to complete satisfactorily.

TASK: {task_description}
{code_note}
INPUT:
{task_input}

Provide a high-quality, complete response to the task."""

    response = client.chat.completions.create(
        model=CLOUD_ESCALATION_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=CLOUD_TEMPERATURE
    )

    output = response.choices[0].message.content.strip()

    # Only strip fences for code tasks — stripping prose answers would
    # discard legitimate content around any incidental code block.
    if is_code_task:
        output = _strip_code_fences(output)
        # Normalise smart quotes, which break exec() with U+2019 errors
        output = (output.replace("\u2019", "'").replace("\u2018", "'")
                        .replace("\u201c", '"').replace("\u201d", '"'))

    return {
        "output": output,
        "tokens_used": response.usage.total_tokens
    }