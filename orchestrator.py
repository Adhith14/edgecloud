# ============================================================
# orchestrator.py — The Cloud CEO
# ============================================================
# The brain of the system. Two jobs:
#   1. PLAN: receives all 5 tasks, decides which agent handles
#      each one (delegation)
#   2. SYNTHESIZE: after agents return, produces a final summary
# Both call the cloud LLM (gpt-4o-mini — cheap, plenty smart).
# ============================================================

import json
import openai
from config import CLOUD_ORCHESTRATOR_MODEL, CLOUD_TEMPERATURE

def plan_tasks(tasks: list, client: openai.OpenAI) -> dict:
    """Cloud LLM produces a delegation plan: which agent handles which task."""
    task_list = "\n".join([
        f"- Task {t['id']} (Category {t['category']}): {t['description']}"
        for t in tasks
    ])

    prompt = f"""You are the orchestrator of a multi-agent AI system.
You have the following specialist agents available:
- file_agent: handles log and file analysis tasks
- code_agent: handles code generation and debugging tasks
- planning_agent: handles planning and task decomposition
- document_agent: handles document summarisation and processing
- multimodal_agent: handles image and visual analysis tasks (MUST be used for any image task)

Here are the tasks to delegate:
{task_list}

Respond ONLY with a valid JSON array. No explanation. No markdown.
Each item must have exactly two fields: task_id, agent. No reason field.

Example format:
Example format:
[
  {{"task_id": "A1", "agent": "file_agent"}},
  {{"task_id": "B1", "agent": "code_agent"}}
]"""

    response = client.chat.completions.create(
        model=CLOUD_ORCHESTRATOR_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=CLOUD_TEMPERATURE
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [WARNING] Could not parse orchestrator plan. Raw output:\n{raw}")
        plan = []

    return {"plan": plan, "tokens_used": response.usage.total_tokens}


def synthesize_results(task_results: list, client: openai.OpenAI) -> dict:
    """Cloud LLM produces a final combined summary of all agent results."""
    results_text = "\n\n".join([
        f"Task {r['task_id']} ({r['agent']}):\n{r['output']}"
        for r in task_results
    ])

    prompt = f"""You are the orchestrator of a multi-agent AI system.
Your specialist agents have completed the following tasks.
Write a brief overall summary (4-6 sentences) of what was accomplished,
noting any key findings or outputs from the agents.

AGENT RESULTS:
{results_text}

OVERALL SUMMARY:"""

    response = client.chat.completions.create(
        model=CLOUD_ORCHESTRATOR_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=CLOUD_TEMPERATURE
    )

    return {"summary": response.choices[0].message.content.strip(),
            "tokens_used": response.usage.total_tokens}
