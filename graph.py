# ============================================================
# graph.py — LangGraph Workflow (v2)
# ============================================================
# The v2 execution graph:
#
#   supervisor -> specialist -> critic -> (retry | done)
#                     ^                       |
#                     +-----------------------+
#                        critique fed back
#
# The critic is a LOCAL model, deliberately. The iteration loop is
# part of the architecture, not part of measurement, so it must not
# make cloud calls — otherwise "local-only" would not be local.
# This local self-critique is the mechanism RQ3 asks about.
#
# Escalation to the cloud (hybrid mode) happens OUTSIDE this graph,
# in main.py, after local iterations are exhausted.
# ============================================================

from typing import TypedDict, List, Optional
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

import config
import agents_v2


# ── STATE ───────────────────────────────────────────────────
# This dict flows through every node. Nodes read it and return
# partial updates, which LangGraph merges in.

class SwarmState(TypedDict):
    task_id: str
    task_description: str
    agent_name: str                 # which specialist handles this task
    output: str                     # current best answer
    critique: str                   # critic's feedback on the last attempt
    iterations: int                 # how many attempts so far
    passed: bool                    # did the critic accept the output
    tools_called: List[str]         # accumulated across attempts
    models_used: List[str]          # which models participated
    history: List[str]              # short trace, for debugging and logging


# ── CRITIC MODEL ────────────────────────────────────────────
_critic = None

def _get_critic():
    """
    The critic uses the shared generalist model, not a specialist.
    Judging output quality is a general reasoning task, and using one
    consistent critic keeps the loop comparable across conditions.
    """
    global _critic
    if _critic is None:
        _critic = ChatOllama(model=config.V2_SHARED_MODEL, temperature=0)
    return _critic


def reset_critic():
    """Clear the cached critic when model config changes."""
    global _critic
    _critic = None


# ── NODE 1: SUPERVISOR ──────────────────────────────────────
def supervisor_node(state: SwarmState) -> dict:
    """
    Entry point. For single-agent tasks the routing is already known
    from the benchmark definition, so this node simply initialises
    the run. It exists as a distinct node so that multi-agent
    decomposition can be added here later without reshaping the graph.
    """
    return {
        "iterations": 0,
        "critique": "",
        "passed": False,
        "tools_called": [],
        "models_used": [],
        "history": [f"supervisor -> routing to {state['agent_name']}"],
    }


# ── NODE 2: SPECIALIST ──────────────────────────────────────
def specialist_node(state: SwarmState) -> dict:
    """
    Runs the assigned specialist agent. On a retry, the critic's
    feedback is passed in as extra context so the agent can address
    what was wrong rather than repeating itself.
    """
    critique = state.get("critique", "")
    extra = ""
    if critique:
        extra = (
            "Your previous attempt was judged insufficient for this reason:\n"
            f"{critique}\n\n"
            "Produce a corrected and complete answer that addresses this."
        )

    result = agents_v2.run_agent(
        state["agent_name"],
        state["task_description"],
        extra_context=extra,
    )

    n = state.get("iterations", 0) + 1
    return {
        "output": result["output"],
        "iterations": n,
        "tools_called": state.get("tools_called", []) + result["tools_called"],
        "models_used": list(set(state.get("models_used", []) + [result["model"]])),
        "history": state.get("history", []) + [
            f"attempt {n}: {state['agent_name']} "
            f"({result['model']}) tools={result['tools_called'] or 'none'}"
        ],
    }


# ── NODE 3: CRITIC ──────────────────────────────────────────
CRITIC_PROMPT = """You are a strict quality reviewer.

Judge whether the ANSWER below adequately completes the TASK.

TASK:
{task}

ANSWER:
{output}

Reply in exactly this format and nothing else:

VERDICT: PASS
or
VERDICT: FAIL
REASON: <one sentence saying specifically what is missing or wrong>

Be harsh. Assume the answer is inadequate unless it clearly proves otherwise.
Reply PASS only if the answer is complete, specific, factually grounded in the
source material, and addresses every part of the task. If any requirement is
partially met, vague, or unverified, reply FAIL."""


def critic_node(state: SwarmState) -> dict:
    """
    Judges the specialist's output using a LOCAL model. Returns a
    pass/fail verdict and, on failure, a critique that is fed back
    into the next attempt.
    """
    output = state.get("output", "")

    # An empty answer always fails; no need to spend a critic call
    if not output or not output.strip():
        return {
            "passed": False,
            "critique": "The answer was empty. Produce an actual response to the task.",
            "history": state.get("history", []) + ["critic: FAIL (empty output)"],
        }

    prompt = CRITIC_PROMPT.format(
        task=state["task_description"],
        output=output[:3000],       # cap, so long answers don't blow context
    )

    try:
        reply = _get_critic().invoke(prompt).content.strip()
    except Exception as e:
        # If the critic fails, accept the output rather than looping forever
        return {
            "passed": True,
            "critique": "",
            "history": state.get("history", []) + [f"critic: error ({e}), accepting output"],
        }

    passed = "PASS" in reply.upper().split("REASON")[0]

    critique = ""
    if not passed:
        critique = reply.split("REASON:", 1)[1].strip() if "REASON:" in reply else reply

    return {
        "passed": passed,
        "critique": critique,
        "history": state.get("history", []) + [
            f"critic: {'PASS' if passed else 'FAIL'}"
            + (f" ({critique[:80]})" if critique else "")
        ],
    }


# ── ROUTING: the loop decision ──────────────────────────────
def should_retry(state: SwarmState) -> str:
    """
    Decides whether to loop back to the specialist or finish.

    Retry only if the critic failed the output AND we have attempts
    left. Exhausting attempts ends the graph — escalation to the
    cloud is handled outside, so the graph stays purely local.
    """
    if state.get("passed"):
        return "done"
    if state.get("iterations", 0) >= config.MAX_ITERATIONS:
        return "done"
    return "retry"


# ── GRAPH CONSTRUCTION ──────────────────────────────────────
_compiled = None

def build_graph():
    """Builds and compiles the workflow. Cached after first call."""
    global _compiled
    if _compiled is not None:
        return _compiled

    g = StateGraph(SwarmState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("specialist", specialist_node)
    g.add_node("critic", critic_node)

    g.set_entry_point("supervisor")
    g.add_edge("supervisor", "specialist")
    g.add_edge("specialist", "critic")

    # The cycle: critic can send work back to the specialist
    g.add_conditional_edges(
        "critic",
        should_retry,
        {"retry": "specialist", "done": END},
    )

    _compiled = g.compile()
    return _compiled


def reset_graph():
    """Clear the compiled graph, e.g. after a config change."""
    global _compiled
    _compiled = None


# ── PUBLIC ENTRY POINT ──────────────────────────────────────
def run_task(task_id: str, task_description: str, agent_name: str) -> dict:
    """
    Runs one benchmark task through the v2 graph.

    Returns a dict with the final output plus the v2-specific metrics
    (iterations used, tools called, models involved, and a trace).
    """
    graph = build_graph()

    initial: SwarmState = {
        "task_id": task_id,
        "task_description": task_description,
        "agent_name": agent_name,
        "output": "",
        "critique": "",
        "iterations": 0,
        "passed": False,
        "tools_called": [],
        "models_used": [],
        "history": [],
    }

    final = graph.invoke(
        initial,
        config={"recursion_limit": (config.MAX_ITERATIONS + 2) * 4},
    )

    return {
        "output": final.get("output", ""),
        "iterations_used": final.get("iterations", 0),
        "tools_called": final.get("tools_called", []),
        "models_used": final.get("models_used", []),
        "critic_passed": final.get("passed", False),
        "history": final.get("history", []),
    }