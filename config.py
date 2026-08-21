# ============================================================
# config.py — Central Configuration
# ============================================================
# All the settings that might change live here in ONE place,
# so you don't have to hunt through multiple files to change them.
# ============================================================
import os
from dotenv import load_dotenv
load_dotenv()

# ── LOCAL MODEL (Ollama) ────────────────────────────────────
# Options: qwen2.5:0.5b, qwen2.5:1.5b, qwen2.5:3b, qwen2.5:7b
#LOCAL_MODEL = "qwen2.5:3b"
LOCAL_MODEL = os.environ.get("ECS_LOCAL_MODEL", "qwen2.5:3b")

# The address where Ollama is running (local server)
OLLAMA_URL = "http://localhost:11434/api/generate"

# ── CLOUD MODELS (OpenAI) ───────────────────────────────────
CLOUD_ORCHESTRATOR_MODEL = "gpt-4o-mini"  # for planning + synthesis
CLOUD_VISION_MODEL       = "gpt-4o"        # for multimodal (needs vision)

# ── EVALUATION SETTINGS ─────────────────────────────────────
USE_DEEPEVAL   = True   # True = DeepEval scoring, False = keyword heuristic
DEEPEVAL_MODEL = "gpt-4o-mini"  # the judge model for GEval
PASS_THRESHOLD = 0.5    # score >= this counts as a PASS

# ── TIMEOUTS ────────────────────────────────────────────────
LOCAL_TIMEOUT = 120  # seconds to wait for a local model response


# ── REPRODUCIBILITY ─────────────────────────────────────────
CLOUD_TEMPERATURE = 0.0   # 0 = deterministic, best for reproducible research results

# ── SYSTEM MODE (which of the three systems to run) ─────────
# "hybrid"      -> v1 local agents, escalate to cloud on low score
# "local_only"  -> v1 local agents, no escalation
# "cloud_only"  -> everything straight to cloud
# "v2_local"    -> v2 graph (tools + iteration), no escalation
# "v2_hybrid"   -> v2 graph, escalate to cloud after local iterations fail
SYSTEM_MODE = os.environ.get("ECS_SYSTEM_MODE", "hybrid")

# Model used when running in cloud_only mode
CLOUD_ONLY_MODEL = "gpt-4o-mini"

# ── DYNAMIC ROUTING (A: score-based escalation) ──────
ENABLE_ESCALATION = SYSTEM_MODE in ("hybrid", "v2_hybrid")   # if True, low-scoring local tasks escalate to cloud
ESCALATION_THRESHOLD   = 0.5    # local score below this triggers escalation to cloud
CLOUD_ESCALATION_MODEL = "gpt-4o-mini"  # model used when a task escalates

# ── LOCAL VISION MODEL ──────────────────────────────────────
# Set via env var in sweeps, same pattern as LOCAL_MODEL
LOCAL_VISION_MODEL = os.environ.get("ECS_VISION_MODEL", "qwen2.5vl:3b")

# Ollama's chat endpoint (vision needs this, not /api/generate)
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

# Whether Category E attempts locally first. False = always cloud (old behaviour).
USE_LOCAL_VISION = os.environ.get("ECS_USE_LOCAL_VISION", "true").lower() == "true"


# ── V2: MULTI-AGENT CONFIGURATION ───────────────────────────

# How models are assigned to agents. This is the variable that tests
# Jonny's H3 (does specialist routing beat a shared generalist?).
#   "specialist"        -> each agent gets its own purpose-built model
#   "shared_generalist" -> every agent uses V2_SHARED_MODEL
MODEL_ASSIGNMENT = os.environ.get("ECS_MODEL_ASSIGNMENT", "specialist")

# The single model used when MODEL_ASSIGNMENT is "shared_generalist".
# This is the control condition: same graph, same tools, one brain.
V2_SHARED_MODEL = os.environ.get("ECS_SHARED_MODEL", "qwen2.5:7b")

# Specialist model per agent. Tool use is unreliable below 3B, so
# nothing here goes smaller than 3B.
V2_SPECIALIST_MODELS = {
    "file_agent":       os.environ.get("ECS_FILE_MODEL",     "qwen2.5:7b"),
    "code_agent":       os.environ.get("ECS_CODE_MODEL",     "qwen2.5-coder:7b"),
    "planning_agent":   os.environ.get("ECS_PLAN_MODEL",     "qwen2.5:7b"),
    "document_agent":   os.environ.get("ECS_DOC_MODEL",      "qwen2.5:3b"),
    "multimodal_agent": os.environ.get("ECS_VISION_MODEL_V2", "qwen2.5vl:3b"),
}

# How many times an agent may retry with critique before escalating.
MAX_ITERATIONS = int(os.environ.get("ECS_MAX_ITERATIONS", "2"))

# Cap on tool calls per task, so a confused agent cannot loop forever.
MAX_TOOL_CALLS = int(os.environ.get("ECS_MAX_TOOL_CALLS", "8"))

# Wall-clock ceiling for a single task in the v2 graph, so one
# pathological task cannot stall an unattended sweep.
V2_TASK_TIMEOUT_S = int(os.environ.get("ECS_V2_TASK_TIMEOUT", "300"))