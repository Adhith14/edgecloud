# ============================================================
# agents_v2.py — Specialist Agents (v2)
# ============================================================
# Each agent is a local model bound to its own toolset. Unlike v1,
# agents are NOT given file contents in the prompt — they call
# tools to fetch what they need themselves.
#
# MODEL_ASSIGNMENT controls the key experimental variable:
#   "specialist"        -> a purpose-built model per agent
#   "shared_generalist" -> one model for all agents (control)
# Everything else is identical between the two, so any difference
# in results is attributable to specialisation alone.
# ============================================================

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

import config
from tools import get_tools


# Role instructions. These describe the agent's job, NOT the specific
# task — the task arrives at invocation time. This is what makes the
# agents reusable across all 40 benchmark tasks.
ROLE_PROMPTS = {
    "file_agent": (
        "You are a file and log analysis specialist.\n"
        "You have tools to list, read, and write files. When a task refers to "
        "a file, USE THE TOOLS to read it — never guess or invent contents. "
        "If you do not know the exact filename, call list_files first.\n"
        "Base your answer only on what the tools actually return."
    ),
    "code_agent": (
        "You are a code generation and debugging specialist.\n"
        "You have tools to run Python, read files, and write files. "
        "ALWAYS test code you write by calling run_python before giving your "
        "final answer. Remember to print() results so you can see them.\n"
        "If execution fails, read the error, fix the code, and run it again. "
        "If the output contradicts what you expected, trust the output and "
        "fix your code — do not explain away a wrong result.\n"
        "CRITICAL: your FINAL message must contain ONLY the working code "
        "itself — the complete, runnable program you verified. No commentary, "
        "no explanation, no markdown fences, no description of what you did. "
        "Just the code."
    ),
    "planning_agent": (
        "You are a planning and task decomposition specialist.\n"
        "You have no tools; work from the information given in the task.\n"
        "Produce clear, ordered, practical steps. Be specific rather than "
        "generic, and state dependencies between steps where they matter."
    ),
    "document_agent": (
        "You are a document processing specialist.\n"
        "You have tools to list, read, and write files. When a task refers to "
        "a document, USE THE TOOLS to read it rather than assuming its "
        "contents.\n"
        "Answer only from what the document actually says."
    ),
    "multimodal_agent": (
        "You are a visual analysis specialist.\n"
        "Describe and reason about what is actually visible in the image. "
        "If you cannot read something clearly, say so rather than guessing."
    ),
}


def get_model_for(agent_name: str) -> str:
    """
    Returns the model name for an agent, honouring MODEL_ASSIGNMENT.

    In shared_generalist mode every text agent uses the same local model.
    In cloud_swarm mode every text agent uses the cloud model. The vision
    agent is always exempt: text models cannot process images, so forcing
    it would break the condition rather than test it.
    """
    if agent_name == "multimodal_agent":
        return config.V2_SPECIALIST_MODELS["multimodal_agent"]

    if config.MODEL_ASSIGNMENT == "cloud_swarm":
        return config.CLOUD_AGENT_MODEL

    if config.MODEL_ASSIGNMENT == "shared_generalist":
        return config.V2_SHARED_MODEL

    return config.V2_SPECIALIST_MODELS.get(agent_name, config.V2_SHARED_MODEL)


def build_agent(agent_name: str):
    """
    Builds one specialist agent: a model bound to its tools and role prompt.

    Returns a compiled LangGraph agent that internally loops
    think -> call tool -> observe -> think, until it produces an answer.
    """
    model_name = get_model_for(agent_name)

    # Cloud swarm agents call the remote API; all other conditions run
    # locally through Ollama. Tools execute on this machine either way.
    if config.MODEL_ASSIGNMENT == "cloud_swarm":
        llm = ChatOpenAI(model=model_name, temperature=0)
    else:
        llm = ChatOllama(model=model_name, temperature=0)

    return create_react_agent(
        llm,
        tools=get_tools(agent_name),
        prompt=ROLE_PROMPTS.get(agent_name, "You are a helpful assistant."),
    )


# Agents are built lazily and cached — constructing them is cheap, but
# rebuilding per task would reload model handles unnecessarily.
_AGENT_CACHE = {}


def get_agent(agent_name: str):
    """Returns a cached agent, building it on first use."""
    key = (agent_name, get_model_for(agent_name))
    if key not in _AGENT_CACHE:
        _AGENT_CACHE[key] = build_agent(agent_name)
    return _AGENT_CACHE[key]


def clear_cache():
    """Clears cached agents. Call when model configuration changes."""
    _AGENT_CACHE.clear()


def run_agent(agent_name: str, task_description: str, extra_context: str = "") -> dict:
    """
    Runs one agent on one task.

    Args:
        agent_name:       which specialist to use
        task_description: what to do (the agent fetches its own inputs)
        extra_context:    optional prior agent output, or a critique on retry

    Returns:
        dict with 'output', 'tools_called' (list), 'model' (name used)
    """
    agent = get_agent(agent_name)

    message = task_description
    if extra_context:
        message = f"{task_description}\n\nADDITIONAL CONTEXT:\n{extra_context}"

    result = agent.invoke(
        {"messages": [("user", message)]},
        config={"recursion_limit": config.MAX_TOOL_CALLS * 2},
    )

    # Walk the message history to record which tools were actually used
    # Walk the message history to record which tools were used and how
    # many tokens the agent consumed. Token counts are only present when
    # the model is cloud-hosted; local models report nothing, which is
    # correct since they incur no API charge.
    tools_called = []
    tokens = 0
    for msg in result["messages"]:
        for call in (getattr(msg, "tool_calls", None) or []):
            tools_called.append(call.get("name", "?"))

        meta = getattr(msg, "usage_metadata", None) or {}
        if meta:
            tokens += meta.get("total_tokens", 0)
        else:
            rmeta = getattr(msg, "response_metadata", None) or {}
            usage = rmeta.get("token_usage") or rmeta.get("usage") or {}
            tokens += usage.get("total_tokens", 0)

    # The final message holds the agent's answer
    output = ""
    for msg in reversed(result["messages"]):
        content = getattr(msg, "content", "")
        if content and isinstance(content, str) and content.strip():
            output = content.strip()
            break

    return {
        "output": output,
        "tools_called": tools_called,
        "model": get_model_for(agent_name),
        "tokens": tokens,
    }