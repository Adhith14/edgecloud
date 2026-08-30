# ============================================================
# main.py — Entry Point (Full Pipeline + DeepEval)
# ============================================================
# Run with:
#   python main.py
#
# Flow:
#   1. Enter your OpenAI API key
#   2. Cloud CEO plans task delegation
#   3. Each agent runs (A,B,C,D local via Ollama; E cloud vision)
#   4. Outputs are scored:
#        - B1 by code execution
#        - A1,C1,D1,E1 by DeepEval GEval (LLM-as-judge)
#   5. Cloud CEO synthesizes a final summary
#   6. Full evaluation table prints (with DeepEval scores)
#
# Toggle USE_DEEPEVAL below to switch between DeepEval scoring
# and the simple keyword heuristic.
# ============================================================

import os
import openai
import config

from orchestrator import plan_tasks, synthesize_results
from agents.file_agent       import run as run_file_agent
from agents.code_agent       import run as run_code_agent
from agents.planning_agent   import run as run_planning_agent
from agents.document_agent   import run as run_document_agent
from agents.multimodal_agent import run as run_multimodal_agent
from evaluator import TaskResult, print_results_table, save_results_csv
from escalation import escalate_to_cloud
from evaluator import calculate_cost
from benchmark import TASKS
from cloud_agent import run as run_cloud_agent
from evaluator import TaskResult, print_results_table, save_results_csv, save_run_summary, calculate_cost
from agents.local_vision_agent import run as run_local_vision_agent
import graph as v2_graph
import graph_chain

def handle_escalation(r, task_description, task_input, client):
    """
    Checks whether a local task result should be escalated to the cloud.
    Called AFTER the local agent has run and been scored.

    Logic (Option A - score-based):
      - If escalation is enabled AND the task has a DeepEval score AND
        that score is below the escalation threshold → escalate to cloud.
      - The cloud's answer replaces the local output.
      - We keep a record of the original local output and score.

    Args:
        r: the TaskResult object (already scored)
        task_description: what the task asked for
        task_input: the data given to the task
        client: OpenAI client
    """
    # Only escalate if enabled in config
    if not config.ENABLE_ESCALATION:
        return

    # We can only score-escalate tasks that have a numeric DeepEval score.
    # (B1 code tasks use execution, not a score — skip those here.)
    # Decide whether this task needs escalation.
    # Two cases:
    #   1. Code tasks (no DeepEval score) → escalate if execution FAILED
    #   2. Scored tasks → escalate if score is below threshold
    needs_escalation = False

    if r.score is None:
        # Code task: it was scored by execution. r.success is True/False.
        # Escalate if the code did NOT pass execution.
        if r.success is False:
            needs_escalation = True
    else:
        # Scored task: escalate if below threshold
        if r.score < config.ESCALATION_THRESHOLD:
            needs_escalation = True

    if needs_escalation:
        reason = f"scored {r.score} < {config.ESCALATION_THRESHOLD}" if r.score is not None else "code execution failed"
        print(f"    [ESCALATION] {r.task_id} {reason} — escalating to cloud...")

        # Remember what the local model produced before we replace it
        r.local_output = r.output
        r.local_score  = r.score

        # Send the task to the cloud for a better answer
        is_code   = (r.scoring_mode == "execution")
        is_vision = ("multimodal" in r.agent)
        cloud_result = escalate_to_cloud(task_description, task_input, client,
                                         is_code_task=is_code, is_vision_task=is_vision)

        # Replace the output with the cloud's answer
        r.output = cloud_result["output"]

        # Record that this task was escalated, and log the cloud call.
        # Vision escalations use the vision model, which is priced differently.
        r.escalated = True
        model_used = config.CLOUD_VISION_MODEL if is_vision else config.CLOUD_ESCALATION_MODEL
        r.record_cloud_call(cloud_result["tokens_used"], task_input, model=model_used)

        # Re-score the new cloud output so the final score reflects the escalated answer
        r.finalise(use_deepeval=config.USE_DEEPEVAL)

        print(f"    [ESCALATION] {r.task_id} re-scored after cloud: {r.score}")
    else:
        status = f"scored {r.score}" if r.score is not None else "code passed"
        print(f"    [LOCAL OK] {r.task_id} {status} — kept local, no escalation.")


def load_task_input(task):
    """
    Loads the input for a task based on its input_type.
    Returns the input as a string (or the image path for multimodal).

    - "log" / "document"  -> read the single file, return its text
    - "text" / "none"     -> the input is already inline, return it as-is
    - "image"             -> return the image file path (not the contents)
    - "multi"             -> read all files in the list, combine into one
                             labelled string
    """
    itype = task["input_type"]
    ref   = task["input_ref"]

    if itype in ("log", "document"):
        # Single text file — read and return its contents
        with open(ref, "r", encoding="utf-8") as f:
            return f.read()

    elif itype in ("text", "none"):
        # Inline text — already in input_ref
        return ref

    elif itype == "image":
        # For images we return the PATH; the multimodal agent reads it
        return ref

    elif itype == "multi":
        # Multiple files — read each, label it, combine
        combined = []
        for path in ref:
            with open(path, "r", encoding="utf-8") as f:
                combined.append(f"=== FILE: {path} ===\n{f.read()}")
        return "\n\n".join(combined)

    else:
        raise ValueError(f"Unknown input_type: {itype}")

    
def run_agent_for_task(task, task_input, client):
    """
    Routes a task to the correct agent and runs it.

    Args:
        task:       the task dict from benchmark.py
        task_input: the loaded input (text, or an image path for multimodal)
        client:     the OpenAI client (only used by the multimodal agent)

    Returns:
        dict with:
          "output"      - the agent's text output
          "tokens_used" - cloud tokens consumed (0 for local agents)
          "is_cloud"    - True if this agent ran in the cloud
    """
    # CLOUD-ONLY MODE: bypass all local agents, send everything to the cloud.
    # Exception: multimodal tasks already use the cloud vision model, so they
    # follow their normal path below.
    if config.SYSTEM_MODE == "cloud_only" and task["agent"] != "multimodal_agent":
        is_code = task.get("scoring_mode") == "execution"
        result = run_cloud_agent(task["description"], task_input, client, is_code_task=is_code)
        return {"output": result["output"], "tokens_used": result["tokens_used"], "is_cloud": True}
    
     # V2 MODES: route through the LangGraph workflow instead of calling
    # a single agent directly. The graph handles tool use and the local
    # retry loop internally.
     # V2 MODES: route through the LangGraph workflow instead of calling

    # a single agent directly. The graph handles tool use and the local

    # retry loop internally.

    if config.SYSTEM_MODE in ("v2_local", "v2_hybrid"):
        # Vision tasks bypass the graph — the vision agent has no tools
        # and needs the image path passed directly.
        if task["agent"] == "multimodal_agent":
            output = run_local_vision_agent(task["description"], task_input)
            return {"output": output, "tokens_used": 0, "is_cloud": False,
                    "v2": {"iterations_used": 1, "tools_called": [],
                           "models_used": [config.V2_SPECIALIST_MODELS["multimodal_agent"]]}}
            
        # Chained tasks go through the decomposition graph instead of the
        # single-agent graph. Flagged per-task in benchmark.py.
        if config.ENABLE_CHAINING and task.get("chain"):
            result = graph_chain.run_chained_task(
                task["id"], task["description"], client
            )
            return {"output": result["output"],
                    "tokens_used": result.get("cloud_tokens", 0),
                    "is_cloud": (config.MODEL_ASSIGNMENT == "cloud_swarm"),
                    "v2": result}



        # Name the input file(s) so the agent knows what to read, without
        # giving it the contents — it must still call read_file itself.

        desc = task["description"]
        ref = task.get("input_ref")
        if task["input_type"] in ("log", "document") and isinstance(ref, str):
            fname = ref.split("/")[-1]
            desc = f"{desc}\n\nThe relevant file is: {fname}"
        elif task["input_type"] == "multi" and isinstance(ref, list):
            names = ", ".join(r.split("/")[-1] for r in ref)
            desc = f"{desc}\n\nThe relevant files are: {names}"
        elif task["input_type"] == "text":
            desc = f"{desc}\n\nCONTEXT:\n{ref}"

        # result = v2_graph.run_task(task["id"], desc, task["agent"])
        # return {"output": result["output"], "tokens_used": 0, "is_cloud": False,
        #         "v2": result}
        import signal

        class _TaskTimeout(Exception):
            pass

        def _on_timeout(signum, frame):
            raise _TaskTimeout()

        signal.signal(signal.SIGALRM, _on_timeout)
        signal.alarm(config.V2_TASK_TIMEOUT_S)
        try:
            result = v2_graph.run_task(task["id"], desc, task["agent"])
        except _TaskTimeout:
            result = {"output": "[TIMEOUT] Task exceeded time limit.",
                      "iterations_used": 0, "tools_called": [],
                      "models_used": [], "critic_passed": False}
        finally:
            signal.alarm(0)

        # In the cloud swarm condition every agent call and every tool
        # result crosses the network, so the task counts as cloud-executed
        # and its inputs count towards data egress.
        is_cloud_swarm = (config.MODEL_ASSIGNMENT == "cloud_swarm")
        return {"output": result["output"],
                "tokens_used": result.get("cloud_tokens", 0),
                "is_cloud": is_cloud_swarm,
                "v2": result}
    
    agent_name = task["agent"]

    
    # ── LOCAL AGENTS (Ollama — no cloud cost) ───────────────
    if agent_name == "file_agent":
        return {"output": run_file_agent(task["description"], task_input), "tokens_used": 0, "is_cloud": False}
    
    elif agent_name == "code_agent":
        return {"output": run_code_agent(task["description"]), "tokens_used": 0, "is_cloud": False}

    elif agent_name == "planning_agent":
        return {"output": run_planning_agent(task["description"], task_input), "tokens_used": 0, "is_cloud": False}

    elif agent_name == "document_agent":
        return {"output": run_document_agent(task["description"], task_input), "tokens_used": 0, "is_cloud": False}

    elif agent_name == "multimodal_agent":
        # task_input is the image PATH, not file contents.
        # In cloud_only mode, or when local vision is disabled, use the
        # cloud vision model. Otherwise attempt locally first — this is
        # what allows Category E to stay on-device.
        if config.SYSTEM_MODE == "cloud_only" or not config.USE_LOCAL_VISION:
            result = run_multimodal_agent(task_input, client, task["description"])
            return {"output": result["response"], "tokens_used": result["tokens_used"], "is_cloud": True}
        else:
            output = run_local_vision_agent(task["description"], task_input)
            return {"output": output, "tokens_used": 0, "is_cloud": False}

    else:
        raise ValueError(f"Unknown agent: {agent_name}")
    

def main():
    print("\n" + "="*60)
    print("  The Edge-Cloud Swarm — Benchmark Run")
    print(f"  Local model : {config.LOCAL_MODEL}")
    print(f"  System mode : {config.SYSTEM_MODE}")
    print(f"  Scoring     : {'DeepEval' if config.USE_DEEPEVAL else 'heuristic'}")
    print(f"  Escalation  : {'ON' if config.ENABLE_ESCALATION else 'OFF'}")
    print(f"  Tasks       : {len(TASKS)}")
    print("="*60)

    # ── API KEY ──────────────────────────────────────────────
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Add it to your .env file.")
    client = openai.OpenAI(api_key=api_key)

    # ── STEP 1: CLOUD CEO PLANS DELEGATION ──────────────────
    print("\n[1/4] Cloud CEO planning task delegation...")
    plan_result = plan_tasks(TASKS, client)
    orchestration_tokens = plan_result["tokens_used"]
    for item in plan_result["plan"]:
        print(f"      -> {item.get('task_id','?')} -> {item.get('agent','?')}")

    # ── STEP 2: RUN EVERY TASK ──────────────────────────────
    print(f"\n[2/4] Running {len(TASKS)} tasks...")
    results = []
    
    # Remove files agents wrote in previous runs. Without this, agents see
    # prior runs' output when they call list_files, which pollutes the
    # benchmark and makes filename selection unreliable.
    import glob
    from tools import PROTECTED_FILES
    removed = 0
    for f in glob.glob("tasks/*"):
        if os.path.basename(f) not in PROTECTED_FILES:
            try:
                os.remove(f)
                removed += 1
            except Exception:
                pass
    if removed:
        print(f"      Cleaned {removed} file(s) left by previous runs")


    for task in TASKS:
        print(f"\n  {task['id']} — {task['category']} ({task['agent']})")

        # Create the result object and copy this task's scoring config onto it
        r = TaskResult(task["id"], task["category"], task["agent"])
        r.scoring_mode    = task["scoring_mode"]
        r.criteria        = task.get("deeval_criteria")
        r.expected_output = task.get("expected_output")
        r.input_text      = task["description"]

        # Load the input; skip the task gracefully if a file is missing
        try:
            task_input = load_task_input(task)
        except FileNotFoundError as e:
            print(f"    [SKIP] Missing input file: {e.filename}")
            r.output  = f"[SKIPPED] Missing input file: {e.filename}"
            r.success = None
            results.append(r)
            continue

        # Run the agent
        r.start()
        try:
            agent_result = run_agent_for_task(task, task_input, client)
            r.output = agent_result["output"]
            # Capture v2 metrics when the graph was used
            v2 = agent_result.get("v2")
            if v2:
                r.iterations_used = v2.get("iterations_used", 0)
                r.tools_called    = v2.get("tools_called", [])
                r.models_used     = v2.get("models_used", [])
                r.critic_passed   = v2.get("critic_passed")

            # Cloud-executed tasks incur token cost and data egress. This
            # covers cloud-only execution, cloud vision, and the cloud swarm
            # baseline, each priced against the model that actually ran.
            if agent_result.get("is_cloud") and agent_result.get("tokens_used"):
                if config.MODEL_ASSIGNMENT == "cloud_swarm" and agent_result.get("v2"):
                    charged_model = config.CLOUD_AGENT_MODEL
                elif task["agent"] == "multimodal_agent":
                    charged_model = config.CLOUD_VISION_MODEL
                else:
                    charged_model = config.CLOUD_ONLY_MODEL
                r.record_cloud_call(agent_result["tokens_used"],
                                    str(task_input),
                                    model=charged_model)
        except Exception as e:
            print(f"    [ERROR] Agent failed: {e}")
            r.output = ""
        r.stop()

        # Score it
        r.finalise(use_deepeval=config.USE_DEEPEVAL)

        # Escalate if needed — but only for LOCAL tasks.
        # Vision tasks can now escalate too, since they may run locally first.
        # Only skip when the task already ran on the cloud.
        already_cloud = (task["agent"] == "multimodal_agent" and
                         (config.SYSTEM_MODE == "cloud_only" or not config.USE_LOCAL_VISION))
        if not already_cloud:
            handle_escalation(r, task["description"], str(task_input), client)

        results.append(r)

    # ── STEP 3: CLOUD CEO SYNTHESIZES ───────────────────────
    print("\n[3/4] Cloud CEO synthesizing final results...")
    synthesis_input = [
        {"task_id": r.task_id, "agent": r.agent, "output": r.output}
        for r in results if r.output and "[SKIPPED]" not in r.output
    ]
    synthesis = synthesize_results(synthesis_input, client)
    orchestration_tokens += synthesis["tokens_used"]

    # ── STEP 4: OUTPUT ──────────────────────────────────────
    print("\n[4/4] Agent Outputs:")
    print("-"*60)
    for r in results:
        print(f"\n  [{r.task_id}] {r.category}  ({r.agent})")
        print(f"  {r.output[:300]}{'...' if len(r.output) > 300 else ''}")

    print("\n  FINAL SYNTHESIS (Cloud CEO):")
    print("-"*60)
    print(synthesis["summary"])

    orchestration_cost = calculate_cost(orchestration_tokens, config.CLOUD_ORCHESTRATOR_MODEL)
    print(f"\n  Orchestration overhead: {orchestration_tokens} tokens = ${orchestration_cost:.6f}")

    print_results_table(results)
    
    # In cloud_only mode the "local model" is irrelevant — record the cloud model instead
    model_label = config.CLOUD_ONLY_MODEL if config.SYSTEM_MODE == "cloud_only" else config.LOCAL_MODEL
    save_results_csv(results, model_name=model_label, system_name=config.SYSTEM_MODE)
    
    save_run_summary(results,
                     model_name=model_label,
                     system_name=config.SYSTEM_MODE,
                     orchestration_tokens=orchestration_tokens,
                     orchestration_cost=orchestration_cost)


if __name__ == "__main__":
    main()
