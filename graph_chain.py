# ============================================================
# graph_chain.py — Multi-Agent Chaining Graph (v2)
# ============================================================
# For composite tasks that need more than one specialist.
#
#   supervisor  -> cloud CEO decomposes into ordered subtasks
#   router      -> picks the next subtask
#   specialist  -> runs it, seeing all prior subtask outputs
#   (loop until subtasks exhausted)
#   synthesis   -> combines results into the final answer
#
# This is a SEPARATE graph from graph.py. Single-agent tasks keep
# using the original path untouched, so a failure here cannot break
# the existing 40-task benchmark.
#
# Agent-to-agent handoff happens two ways:
#   1. prior outputs passed as context in the prompt
#   2. write_file / read_file for larger artefacts
# ============================================================

import json
from typing import TypedDict, List

import openai
from langgraph.graph import StateGraph, END

import config
import agents_v2


# ── STATE ───────────────────────────────────────────────────
class ChainState(TypedDict):
    task_id: str
    task_description: str
    subtasks: List[dict]        # [{"agent": ..., "instruction": ...}, ...]
    completed: List[dict]       # [{"agent":..., "instruction":..., "output":...}]
    current_index: int
    final_output: str
    tools_called: List[str]
    models_used: List[str]
    history: List[str]
    decomposition_tokens: int


# The OpenAI client is set once per run by run_chained_task()
_client = None


# ── NODE 1: SUPERVISOR (decomposition) ──────────────────────
DECOMPOSE_PROMPT = """You are the supervisor of a team of specialist AI agents.

Available agents:
- file_agent: reads and analyses files and logs. Has tools to list, read and write files.
- code_agent: writes, fixes and executes code. Has tools to run Python, read and write files.
- document_agent: reads and processes documents. Has tools to list, read and write files.
- planning_agent: produces plans and decompositions. Has no tools.

Break the following task into an ORDERED sequence of subtasks, each assigned to
one agent. Each subtask must be a concrete instruction that agent can carry out.
Later subtasks may rely on the output of earlier ones.

Use between 2 and {max_subtasks} subtasks. Use the smallest number that genuinely
completes the task.

TASK:
{task}

Respond ONLY with a valid JSON array, no markdown and no explanation:
[
  {{"agent": "file_agent", "instruction": "..."}},
  {{"agent": "code_agent", "instruction": "..."}}
]"""


def supervisor_node(state: ChainState) -> dict:
    """Cloud CEO decomposes the task into ordered subtasks."""
    prompt = DECOMPOSE_PROMPT.format(
        task=state["task_description"],
        max_subtasks=config.MAX_SUBTASKS,
    )

    subtasks = []
    tokens = 0
    try:
        resp = _client.chat.completions.create(
            model=config.CLOUD_ORCHESTRATOR_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=config.CLOUD_TEMPERATURE,
        )
        tokens = resp.usage.total_tokens
        raw = resp.choices[0].message.content.strip()

        # Strip markdown fences if the model added them
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        parsed = json.loads(raw)
        # Keep only well-formed entries naming a real agent
        valid_agents = {"file_agent", "code_agent", "document_agent", "planning_agent"}
        subtasks = [
            s for s in parsed
            if isinstance(s, dict) and s.get("agent") in valid_agents and s.get("instruction")
        ][:config.MAX_SUBTASKS]

    except Exception as e:
        # FALLBACK: if decomposition fails for any reason, run the whole task
        # as a single file_agent subtask rather than failing the run.
        return {
            "subtasks": [{"agent": "file_agent", "instruction": state["task_description"]}],
            "completed": [],
            "current_index": 0,
            "decomposition_tokens": tokens,
            "history": [f"supervisor: decomposition failed ({str(e)[:60]}), falling back to single agent"],
        }

    if not subtasks:
        subtasks = [{"agent": "file_agent", "instruction": state["task_description"]}]

    plan = " -> ".join(s["agent"] for s in subtasks)
    return {
        "subtasks": subtasks,
        "completed": [],
        "current_index": 0,
        "decomposition_tokens": tokens,
        "history": [f"supervisor: decomposed into {len(subtasks)} subtasks ({plan})"],
    }


# ── NODE 2: SPECIALIST ──────────────────────────────────────
def specialist_node(state: ChainState) -> dict:
    """
    Runs the current subtask. Prior subtask outputs are passed as context,
    which is how one agent's work reaches the next.
    """
    idx = state["current_index"]
    sub = state["subtasks"][idx]

    # Build the handoff context from everything completed so far
    context = ""
    if state["completed"]:
        parts = []
        for c in state["completed"]:
            parts.append(f"--- Output from {c['agent']} (subtask: {c['instruction'][:80]}) ---\n{c['output']}")
        context = (
            "Previous agents on this task produced the following. Use their work; "
            "do not repeat it.\n\n" + "\n\n".join(parts)
        )
        
    instruction = sub["instruction"]
    if sub["agent"] == "code_agent":
        instruction += ("\n\nYou MUST call run_python to execute your code and "
                        "report the actual output it produced. Do not state "
                        "results you have not verified by running the code.")
    result = agents_v2.run_agent(
        sub["agent"],
        instruction,
        extra_context=context,
    )

    completed = state["completed"] + [{
        "agent": sub["agent"],
        "instruction": sub["instruction"],
        "output": result["output"],
    }]

    return {
        "completed": completed,
        "current_index": idx + 1,
        "tools_called": state.get("tools_called", []) + result["tools_called"],
        "models_used": list(set(state.get("models_used", []) + [result["model"]])),
        "history": state.get("history", []) + [
            f"subtask {idx+1}/{len(state['subtasks'])}: {sub['agent']} "
            f"({result['model']}) tools={result['tools_called'] or 'none'}"
        ],
    }


# ── ROUTING ─────────────────────────────────────────────────
def more_subtasks(state: ChainState) -> str:
    """Continue through the chain until every subtask is done."""
    if state["current_index"] < len(state["subtasks"]):
        return "next"
    return "synthesise"


# ── NODE 3: SYNTHESIS ───────────────────────────────────────
def synthesis_node(state: ChainState) -> dict:
    """
    Combines subtask outputs into one final answer.

    If only one subtask ran, its output IS the answer — no need to spend
    a cloud call reformatting it.
    """
    completed = state["completed"]

    if len(completed) == 1:
        return {
            "final_output": completed[0]["output"],
            "history": state.get("history", []) + ["synthesis: single subtask, passed through"],
        }

    parts = "\n\n".join(
        f"[{c['agent']}] {c['instruction']}\n{c['output']}" for c in completed
    )
    prompt = f"""Several specialist agents worked on this task in sequence.

ORIGINAL TASK:
{state['task_description']}

AGENT OUTPUTS:
{parts}

Write the final answer to the original task, combining their work.
Answer the task directly — do not describe what the agents did."""

    try:
        resp = _client.chat.completions.create(
            model=config.CLOUD_ORCHESTRATOR_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=900,
            temperature=config.CLOUD_TEMPERATURE,
        )
        return {
            "final_output": resp.choices[0].message.content.strip(),
            "decomposition_tokens": state.get("decomposition_tokens", 0) + resp.usage.total_tokens,
            "history": state.get("history", []) + ["synthesis: combined outputs"],
        }
    except Exception as e:
        # Fall back to concatenating the outputs rather than losing them
        return {
            "final_output": "\n\n".join(c["output"] for c in completed),
            "history": state.get("history", []) + [f"synthesis: failed ({str(e)[:50]}), concatenated"],
        }


# ── GRAPH ───────────────────────────────────────────────────
_compiled = None

def build_chain_graph():
    global _compiled
    if _compiled is not None:
        return _compiled

    g = StateGraph(ChainState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("specialist", specialist_node)
    g.add_node("synthesis", synthesis_node)

    g.set_entry_point("supervisor")
    g.add_edge("supervisor", "specialist")
    g.add_conditional_edges(
        "specialist",
        more_subtasks,
        {"next": "specialist", "synthesise": "synthesis"},
    )
    g.add_edge("synthesis", END)

    _compiled = g.compile()
    return _compiled


def reset_chain_graph():
    global _compiled
    _compiled = None


# ── PUBLIC ENTRY POINT ──────────────────────────────────────
def run_chained_task(task_id: str, task_description: str, client: openai.OpenAI) -> dict:
    """
    Runs one composite task through the chaining graph.

    Returns the same shape as graph.run_task, plus chain-specific fields,
    so main.py can handle both identically.
    """
    global _client
    _client = client

    graph = build_chain_graph()

    initial: ChainState = {
        "task_id": task_id,
        "task_description": task_description,
        "subtasks": [],
        "completed": [],
        "current_index": 0,
        "final_output": "",
        "tools_called": [],
        "models_used": [],
        "history": [],
        "decomposition_tokens": 0,
    }

    final = graph.invoke(
        initial,
        config={"recursion_limit": (config.MAX_SUBTASKS + 3) * 4},
    )

    return {
        "output": final.get("final_output", ""),
        "iterations_used": len(final.get("completed", [])),   # subtasks run
        "tools_called": final.get("tools_called", []),
        "models_used": final.get("models_used", []),
        "critic_passed": None,          # chain graph has no critic node
        "history": final.get("history", []),
        "agents_chained": [c["agent"] for c in final.get("completed", [])],
        "cloud_tokens": final.get("decomposition_tokens", 0),
    }