# The Edge–Cloud Swarm

**Evaluating hierarchical multi-agent systems with local small language models**

MSc Artificial Intelligence — ECS8056 Themed Research Project
Queen's University Belfast, School of Electronics, Electrical Engineering and Computer Science

Author: Adhith Kuruthukulangara Lijo (40494229)
Supervisor: Dr. Yujian Gan

---

## Overview

This repository contains the implementation, benchmark and analysis pipeline for
the Edge–Cloud Swarm: a hierarchical multi-agent architecture in which a
cloud-hosted language model orchestrates while small language models execute on
local hardware.

Six system configurations are implemented and evaluated on a purpose-built
benchmark of 44 tasks across eight capability categories, measuring task
success, monetary cost, latency and data egress jointly. Model scale,
quantisation level, vision model, agent specialisation and model location are
varied as controlled independent variables.

The reported results derive from 72 experimental runs (24 conditions × 3
repetitions) comprising 3,168 individual task evaluations.

---

## System configurations

| Configuration | Description |
|---|---|
| `cloud_only` | Every task routed to the cloud model in a single call |
| `local_only` (v1) | Local agents receiving task inputs in the prompt |
| `hybrid` (v1) | As above, escalating to the cloud when a task scores below threshold |
| `v2_local` | Local agents with tool access, per-agent model specialisation and a local critic |
| `v2_hybrid` | As above, with cloud escalation after local retries are exhausted |
| cloud swarm | The v2 design with every agent backed by the cloud model |

Hybrid configurations escalate on an evaluation score that a deployed system
would not possess. Their results are reported as an evaluator-assisted upper
bound rather than as directly comparable conditions.

---

## Repository structure

```
config.py               Central configuration; every parameter overridable by environment variable
benchmark.py            All 44 task definitions with criteria and reference answers
main.py                 Execution entry point; routing, escalation, metric recording
orchestrator.py         Cloud orchestration: task planning and delegation

agents/                 v1 agent implementations (one module per specialist role)
agents_v2.py            v2 agent layer: models bound to toolsets and role instructions
tools.py                Sandboxed tool definitions (list_files, read_file, write_file, run_python)
graph.py                v2 execution graph: orchestrator, specialist, critic with retry cycle
graph_chain.py          Composite task path: decomposition, sequential routing, synthesis
escalation.py           Cloud escalation for text, code and vision tasks

evaluator.py            Result representation, cost accounting, CSV persistence
deepeval_scorer.py      G-Eval scoring with recorded justifications
run_experiments.py      Sweep orchestration; each condition runs as an isolated subprocess
analyse.py              Aggregation and figure generation
verify.py               Cross-checks reported figures against source data

tasks/                  Benchmark input artefacts (logs, documents, configs, images)
results/                Task-level and run-level CSV output, with archived schema versions
figures/                Generated figures
tables/                 Generated tables
```

---

## Requirements

- Python 3.12
- [Ollama](https://ollama.com) for local model serving
- An OpenAI API key, supplied through the environment

```bash
pip install -r requirements.txt
```

### Models used

Pull the following through Ollama before running:

```bash
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:1.5b
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
ollama pull qwen2.5:7b-instruct-q8_0
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5vl:3b
ollama pull llava:7b
ollama pull llama3.2:3b
```

### Environment

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your-key-here
```

Ollama should be started with model eviction relaxed, otherwise multi-model
configurations thrash between specialists and runs exceed their time limits:

```bash
export OLLAMA_KEEP_ALIVE=60m
export OLLAMA_MAX_LOADED_MODELS=6
ollama serve
```

---

## Running

### A single benchmark run

```bash
ECS_SYSTEM_MODE=v2_local \
ECS_MODEL_ASSIGNMENT=specialist \
ECS_LOCAL_MODEL=qwen2.5:7b \
python main.py
```

### The full experimental sweep

```bash
python run_experiments.py
```

A full sweep runs for several hours, so it should be started inside a detachable
terminal session:

```bash
tmux new -s sweep
python run_experiments.py
# Ctrl+B then D to detach
```

Results append to the existing CSV files, so an interrupted sweep loses progress
but not data; remaining conditions can be run separately.

### Regenerating figures and tables

```bash
python analyse.py
```

Every figure and table in the research paper and supporting materials is
produced by this script from the raw result files.

---

## Configuration

All parameters that vary between conditions are set through environment
variables, with the value in `config.py` as the default. This allows the sweep
runner to vary configuration without modifying source, so the repository state
always corresponds to what was executed.

| Variable | Values | Default |
|---|---|---|
| `ECS_SYSTEM_MODE` | `cloud_only`, `local_only`, `hybrid`, `v2_local`, `v2_hybrid` | `hybrid` |
| `ECS_MODEL_ASSIGNMENT` | `specialist`, `shared_generalist`, `cloud_swarm` | `specialist` |
| `ECS_LOCAL_MODEL` | any Ollama tag | `qwen2.5:3b` |
| `ECS_VISION_MODEL` | any vision-capable tag | `qwen2.5vl:3b` |
| `ECS_SHARED_MODEL` | any Ollama tag | `qwen2.5:7b` |
| `ECS_CHAINING` | `true`, `false` | `true` |
| `ECS_MAX_ITERATIONS` | integer | `2` |

See `config.py` for the complete set, including per-agent specialist model
assignment and execution timeouts.

---

## Output

Two CSV files are written per run:

- **`results/results.csv`** — one row per task: score, latency, cost, tool calls,
  iterations, and the evaluator's written justification
- **`results/runs.csv`** — one row per run: aggregate totals and run-level
  quantities such as orchestration cost

Cost is decomposed into orchestration cost (the cloud planner and synthesiser,
incurred by every configuration), task execution cost (cloud-executed and
escalated tasks), and evaluation overhead (the judge, excluded from system
totals since a deployed system would not score its own output).

---

## Safety note

Agents in the v2 configurations can execute code. Execution is confined to a
whitelisted task directory with path traversal rejected, runs in a separate
process under a ten-second timeout, and benchmark inputs are protected against
modification. This is directory-scoped isolation rather than container-level
sandboxing: adequate for controlled evaluation with authored inputs, but not
sufficient for any deployment processing untrusted input.

---

## Development history

Continuous development history is maintained at
<https://github.com/Adhith14/edgecloud>. This repository holds the submitted
version of the code.

---

## Academic integrity

This work was produced for ECS8056 at Queen's University Belfast. AI assistance
used during development is acknowledged in the submitted Declaration of Academic
Integrity.
