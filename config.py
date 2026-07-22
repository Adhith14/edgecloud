# ============================================================
# config.py — Central Configuration
# ============================================================
# All the settings that might change live here in ONE place,
# so you don't have to hunt through multiple files to change them.
# ============================================================

from dotenv import load_dotenv
load_dotenv()

# ── LOCAL MODEL (Ollama) ────────────────────────────────────
# Change this ONE line to switch local models everywhere.
# Options you might use: qwen2.5:0.5b, qwen2.5:1.5b, qwen2.5:3b, qwen2.5:7b
LOCAL_MODEL = "qwen2.5:0.5b"

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

# ── DYNAMIC ROUTING (A: score-based escalation) ──────
ENABLE_ESCALATION      = True   # if True, low-scoring local tasks escalate to cloud
ESCALATION_THRESHOLD   = 0.5    # local score below this triggers escalation to cloud
CLOUD_ESCALATION_MODEL = "gpt-4o-mini"  # model used when a task escalates


# ── REPRODUCIBILITY ─────────────────────────────────────────
CLOUD_TEMPERATURE = 0.0   # 0 = deterministic, best for reproducible research results