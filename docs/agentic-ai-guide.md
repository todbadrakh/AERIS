# Agentic AI Guide for AERIS

This guide explains how agentic AI, skills, MCP tools, and the AERIS codebase fit together.

The key idea: **AERIS is not itself an agentic AI model**. AERIS is a materials ML codebase. The agentic AI layer is added by giving an AI assistant instructions, tools, and workflows that let it use the AERIS code intelligently.

## The Big Picture

AERIS has four main layers:

| Layer | What it is | Where it lives |
|---|---|---|
| Core ML library | The actual scientific prediction code | `aeris.py` |
| Workflow scripts | End-to-end examples that reproduce papers | `validation/paper_a/`, `validation/paper_b/` |
| Skills | Written instructions that tell an AI agent how to perform a task | `skills/` |
| MCP tools | Tool servers that expose AERIS functions to an AI agent | `mcp/` |

An agentic AI assistant uses these layers together. It reads a skill, decides what workflow applies, calls MCP tools or Python scripts, inspects outputs, and explains the results.

## 1. Core AERIS Library

The core scientific code lives in:

```text
aeris.py
```

This file contains the reusable functions that do the actual work:

- parse chemical formulas, such as `UO2`
- compute material descriptors
- load trained ML models
- predict formation energies
- search datasets for known structures
- find compatible structure templates

This is the computational foundation. The agent does not replace this code; it uses this code.

## 2. Workflow Scripts

The validation scripts are complete examples of how AERIS is meant to be used.

Important examples:

```text
validation/paper_a/agent_paper_A_mcp.py
validation/paper_b/agent_paper_B.py
```

### Agent A: Structure Search

`validation/paper_a/agent_paper_A_mcp.py` performs a binary structure search. It:

- generates binary compositions
- screens structural templates
- predicts formation enthalpies
- builds convex hulls
- compares against reference DFT data
- produces plots and reports

This is validated on the U-Si system.

### Agent B: Reaction Energy

`validation/paper_b/agent_paper_B.py` evaluates reaction energies and defect energetics. It:

- predicts formation enthalpies for compounds
- computes reaction enthalpies using Hess's law
- evaluates UN/metal compatibility
- performs point-defect calculations
- compares results to literature data

This is validated on UN/metal compatibility.

## 3. Skills

Skills are instruction files for an AI agent.

They live in:

```text
skills/
```

Current skills:

```text
skills/structure-search.md
skills/reaction-energy.md
skills/point-defect.md
```

A skill is not executable code. It is a recipe that tells the agent:

- what task the skill handles
- what input to expect
- which scripts or functions to use
- what assumptions matter
- how to interpret the output
- what files contain reference implementations

For example, `skills/reaction-energy.md` tells the agent how to compute reaction enthalpies, where the reference script is, and how to interpret positive vs. negative reaction energy.

In practical terms:

- **Skill = task instructions**
- **Python script = implementation**
- **AERIS model = prediction engine**
- **Agent = coordinator**

## 4. MCP Tools

MCP stands for **Model Context Protocol**.

In this repository, MCP tools expose AERIS functions so an AI agent can call them programmatically.

They live in:

```text
mcp/
```

Current MCP tool servers:

| MCP script | Purpose |
|---|---|
| `mcp/mcp_aeris_predict.py` | Predict energy for a composition and structure |
| `mcp/mcp_aeris_best_structure.py` | Search compatible structures and predict energies |
| `mcp/mcp_structure_search.py` | Find exact structure matches in the dataset |
| `mcp/mcp_structure_templates.py` | Find structural templates compatible with a composition |

Each MCP script uses `FastMCP` to expose one or more Python functions as tools.

For example, instead of the agent manually writing Python every time it wants an energy prediction, it can call the MCP tool exposed by `mcp_aeris_predict.py`.

## How Skills and MCP Work Together

A useful way to think about it:

```text
User asks a question
        |
        v
AI agent selects a skill
        |
        v
Skill tells agent what workflow to follow
        |
        v
Agent calls MCP tools or runs Python scripts
        |
        v
AERIS library performs the scientific computation
        |
        v
Agent summarizes results for the user
```

Example:

```text
User: Is UN compatible with vanadium cladding?
```

The agent would:

1. Recognize this as a reaction-energy task.
2. Read `skills/reaction-energy.md`.
3. Use the logic from `validation/paper_b/agent_paper_B.py`.
4. Predict formation energies for the relevant phases.
5. Compute reaction enthalpies.
6. Explain whether the interface is thermodynamically compatible.

## What Makes This "Agentic"?

Traditional ML usage looks like this:

```text
Human chooses script -> human runs script -> human interprets output
```

Agentic usage looks like this:

```text
Human asks goal -> agent chooses workflow -> agent runs tools -> agent explains output
```

The agent is useful because it can:

- decide which workflow applies
- inspect files and outputs
- adapt scripts to a new material system
- call tools in sequence
- produce plots, JSON files, and reports
- explain the scientific meaning of the results

The agent is not inventing the physics. It is orchestrating the existing AERIS models and workflows.

## Current Repository Notes

There are a few practical inconsistencies to fix or keep in mind before running everything end to end.

### Skill Path Mismatch

`AGENTS.md` and `CLAUDE.md` refer to:

```text
.claude/skills/
```

But this checkout contains:

```text
skills/
```

The skill files exist, but the documented path is outdated or mismatched.

### Missing Expected Data/Model Directories

The scripts expect paths like:

```text
data/Dataset_feature+CN.csv
model/model_3.joblib
model/aeris_comp_only.pt
```

But the visible CSV files are currently under:

```text
ML-RF_Supplementary_material/
```

The trained model files were not visible in this checkout during inspection.

### Public Function Name Mismatch

The validation scripts import:

```python
from aeris import compute_magpie_df
```

But `aeris.py` currently defines:

```python
_compute_magpie_df
```

That private helper is not exported as `compute_magpie_df`. This likely needs a small compatibility fix before the validation scripts run cleanly.

## Recommended Learning Path

If you are new to agentic AI, start in this order:

1. Read `skills/reaction-energy.md`.
2. Read the top-level comments in `validation/paper_b/agent_paper_B.py`.
3. Look at how `agent_paper_B.py` loads models and batches predictions.
4. Open one MCP script, such as `mcp/mcp_aeris_predict.py`.
5. Compare the MCP tool to the underlying function in `aeris.py`.

The main thing to learn is the separation of responsibilities:

| Component | Responsibility |
|---|---|
| `aeris.py` | Scientific computation |
| `validation/*.py` | Full workflows |
| `skills/*.md` | Agent instructions |
| `mcp/*.py` | Tool interface for AI agents |
| AI agent | Chooses and coordinates workflows |

## Practical First Goal

A good first milestone is to make one validated workflow run locally:

```bash
python validation/paper_b/agent_paper_B.py
```

Before that works, the repository likely needs:

- expected model files under `model/`
- expected dataset files under `data/`
- the `compute_magpie_df` export mismatch fixed
- Python dependencies installed, including PyTorch, scikit-learn, pandas, pymatgen, matminer, and fastmcp

Once the workflow runs as a normal Python script, wiring it into an agent through skills and MCP becomes much easier.

