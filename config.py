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
# "hybrid"      -> local agents, escalate to cloud when scoring low (Edge-Cloud Swarm)
# "local_only"  -> local agents only, NO escalation, no cloud safety net
# "cloud_only"  -> every task goes straight to the cloud model (baseline)
#SYSTEM_MODE = "hybrid"
SYSTEM_MODE = os.environ.get("ECS_SYSTEM_MODE", "hybrid")

# Model used when running in cloud_only mode
CLOUD_ONLY_MODEL = "gpt-4o-mini"

# ── DYNAMIC ROUTING (A: score-based escalation) ──────
ENABLE_ESCALATION      = (SYSTEM_MODE == "hybrid")   # if True, low-scoring local tasks escalate to cloud
ESCALATION_THRESHOLD   = 0.5    # local score below this triggers escalation to cloud
CLOUD_ESCALATION_MODEL = "gpt-4o-mini"  # model used when a task escalates

# ── LOCAL VISION MODEL ──────────────────────────────────────
# Set via env var in sweeps, same pattern as LOCAL_MODEL
LOCAL_VISION_MODEL = os.environ.get("ECS_VISION_MODEL", "qwen2.5vl:3b")

# Ollama's chat endpoint (vision needs this, not /api/generate)
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"

# Whether Category E attempts locally first. False = always cloud (old behaviour).
USE_LOCAL_VISION = os.environ.get("ECS_USE_LOCAL_VISION", "true").lower() == "true"