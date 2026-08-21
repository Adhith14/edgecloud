# ============================================================
# tools.py — Agent Tools (v2)
# ============================================================
# Tools that agents call themselves, rather than having inputs
# pasted into their prompts. This is the core difference between
# v1 (prompt wrappers) and v2 (agentic).
#
# All file operations are sandboxed to the tasks/ directory.
# Schemas follow MCP conventions (name, typed params, description)
# so they could be exposed over MCP without redesign.
#
# Each tool's docstring is what the model reads to decide whether
# and how to use it, so the wording matters.
# ============================================================

import os
import sys
import subprocess
from langchain_core.tools import tool

SANDBOX = "tasks"
EXEC_TIMEOUT_S = 10
MAX_OUTPUT_CHARS = 4000

# Benchmark inputs agents must never overwrite. Without this, an agent
# could corrupt a task input mid-sweep and silently invalidate every
# subsequent run.
PROTECTED_FILES = {
    "sample_log.txt", "sample_document.txt", "report_document.txt",
    "policy_document.txt", "crash_log.txt", "metrics.csv",
    "service_a.log", "service_b.log", "service_c.log",
    "app_config.yaml", "incident_error.txt", "broken_pipeline.txt",
    "hard_metrics.csv", "conflicting_docs.txt", "silent_failure.log",
    "error_screenshot.png", "chart.png", "diagram.png",
    "data_table.png", "complex_error.png",
}


def _safe_path(filename: str):
    """Validate a filename and return its full path, or an error string."""
    if not filename or not filename.strip():
        return None, "Error: no filename provided."

    filename = filename.strip()
    if "/" in filename or "\\" in filename or ".." in filename:
        return None, ("Error: only plain filenames inside the tasks directory "
                      "are allowed. Do not include paths.")

    path = os.path.join(SANDBOX, filename)
    if not os.path.exists(path):
        return None, (f"Error: '{filename}' does not exist. "
                      f"Use list_files to see what is available.")
    return path, None


@tool
def list_files() -> str:
    """List every file available to read in the tasks directory.

    Use this first when you do not already know the exact filename
    you need. Takes no arguments."""
    try:
        files = sorted(os.listdir(SANDBOX))
        return "Available files: " + ", ".join(files) if files else "The tasks directory is empty."
    except Exception as e:
        return f"Error listing files: {e}"


@tool
def read_file(filename: str) -> str:
    """Read the full contents of a file from the tasks directory.

    Pass ONLY the filename, never a path. Example: sample_log.txt
    If you are unsure of the filename, call list_files first."""
    path, err = _safe_path(filename)
    if err:
        return err
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > MAX_OUTPUT_CHARS * 4:
            content = content[:MAX_OUTPUT_CHARS * 4] + "\n...[truncated]"
        return content
    except UnicodeDecodeError:
        return f"Error: '{filename}' is not a readable text file."
    except Exception as e:
        return f"Error reading '{filename}': {e}"


@tool
def write_file(filename: str, content: str) -> str:
    """Write text content to a file in the tasks directory.

    Pass ONLY a filename, never a path. Use this to save output that
    another agent will need to read, or to record intermediate results.
    Overwrites the file if it already exists."""
    if not filename or not filename.strip():
        return "Error: no filename provided."

    filename = filename.strip()
    if "/" in filename or "\\" in filename or ".." in filename:
        return ("Error: only plain filenames inside the tasks directory "
                "are allowed. Do not include paths.")
    if filename in PROTECTED_FILES:
        return f"Error: '{filename}' is a protected benchmark input and cannot be overwritten."

    try:
        with open(os.path.join(SANDBOX, filename), "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} characters to '{filename}'."
    except Exception as e:
        return f"Error writing '{filename}': {e}"


@tool
def run_python(code: str) -> str:
    """Execute Python code and return whatever it prints, plus any errors.

    Use this to TEST code you have written before giving your final answer.
    The code runs in a fresh process with a 10 second timeout. You must
    print() anything you want to see — a bare expression produces no output.

    If the code fails, read the error, fix it, and run it again."""
    if not code or not code.strip():
        return "Error: no code provided."
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True,
            timeout=EXEC_TIMEOUT_S, cwd=os.getcwd(),
        )
        out = (result.stdout or "").strip()[:MAX_OUTPUT_CHARS]
        err = (result.stderr or "").strip()[:MAX_OUTPUT_CHARS]
        if err:
            return f"STDOUT:\n{out}\n\nSTDERR:\n{err}"
        return out or "(no output — did you forget to print()?)"
    except subprocess.TimeoutExpired:
        return f"Error: execution exceeded {EXEC_TIMEOUT_S}s and was stopped. Check for infinite loops."
    except Exception as e:
        return f"Error executing code: {e}"


# ── TOOL REGISTRY ───────────────────────────────────────────
# Small toolsets per agent improve tool-selection reliability,
# which matters at 3B scale.
TOOLSETS = {
    "file_agent":       [list_files, read_file, write_file],
    "code_agent":       [run_python, read_file, write_file],
    "planning_agent":   [],                      # pure reasoning
    "document_agent":   [list_files, read_file, write_file],
    "multimodal_agent": [],                      # images passed directly
}


def get_tools(agent_name: str):
    """Returns the tool list for a given agent."""
    return TOOLSETS.get(agent_name, [])