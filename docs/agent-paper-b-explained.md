# Agent B Script Explained

This document explains `validation/paper_b/agent_paper_B.py`.

The script is a full validation workflow for **Agent B: Reaction Energy Agent**. Its goal is to reproduce parts of Hua et al. 2022 for **uranium nitride (UN) compatibility with metal cladding materials**: V, Nb, Ta, Cr, Mo, and W.

It is "agentic" in the workflow sense: it does not make just one prediction. It loads models, gathers structural data, predicts many phases, computes reactions, evaluates point defects, compares to DFT references, and writes reports.

## What The Script Computes

### 1. Formation Enthalpies

The script predicts formation energies for U-X-N phases and compares them to DFT values from the reference paper.

Examples of phases include:

- `UN`
- `VN`
- `V2N`
- `NbN`
- `TaN`
- `CrN`
- `MoN`
- `WN`

### 2. Reaction Enthalpies

The script evaluates reactions such as:

```text
UN + 2V = V2N + U
```

It uses Hess's law:

```python
dH_rxn = (sum(products) - sum(reactants)) / total_atoms
```

Interpretation:

| Reaction energy | Meaning |
|---|---|
| Positive | Endothermic; interface is thermodynamically more stable |
| Negative | Exothermic; reaction is thermodynamically favorable |
| Near zero | Marginal; kinetics may matter |

### 3. Point-Defect Formation Energies

The script models defects in a 64-atom UN proxy cell.

Defect types:

| Defect | Meaning |
|---|---|
| `Vac. U` | Uranium vacancy |
| `Vac. N` | Nitrogen vacancy |
| `Inter. N` | Nitrogen interstitial |
| `X on U` | Metal atom substituted onto a uranium site |
| `X on N` | Metal atom substituted onto a nitrogen site |

### 4. Defect Ranking

The script compares which defect is predicted to be most favorable against the DFT ranking from the paper.

It reports:

- top-1 accuracy
- top-2 accuracy
- Kendall tau ranking agreement

## Main File Structure

The script is organized into several sections.

| Section | Purpose |
|---|---|
| Imports and setup | Sets project root and imports AERIS utilities |
| Model loading | Loads RF and NN models |
| CIF parsing | Extracts structural descriptors from CIF files |
| Database lookup | Searches CSV datasets for missing structures |
| Batch prediction | Predicts energies efficiently |
| Reference data | Stores DFT values, reactions, and defect equilibria |
| Main workflow | Runs formation, reaction, defect, and ranking calculations |
| Output writing | Writes JSON, markdown report, and call log |

## Model Loading

The script loads two models:

```python
MODEL_RF_PATH = "model/model_3.joblib"
MODEL_NN_PATH = "model/aeris_comp_only.pt"
```

| Model | Role |
|---|---|
| RF | Structure-aware model using composition and structural descriptors |
| NN | Composition-only neural network model |

The dual-model design is used for cross-checking. If the two models agree, confidence is higher. If they disagree, the result should be treated more cautiously.

## Structural Data

The RF model needs structural descriptors. The script gets them from three places:

1. Hardcoded entries in `STRUCT_DB`
2. CIF files in `data/cif/`
3. CSV datasets such as `data/Dataset_feature+CN.csv`

The function `parse_cif_structure()` extracts:

- space group
- number of sites
- volume
- density
- lattice constants
- coordination numbers

The function `lookup_phase_in_databases()` searches dataset CSV files for phases missing from `STRUCT_DB`.

## Batch Prediction

The central prediction helper is `_batch_predict()`.

It takes a list of pairs:

```python
(composition_string, structure_dict_or_None)
```

Then it:

1. Skips predictions that are already cached.
2. Computes Magpie composition features.
3. Adds structural features if available.
4. Builds the model feature matrix.
5. Applies the trained scaler.
6. Runs either the RF model or NN model.
7. Stores predictions in a cache.

This avoids repeatedly reloading models or recomputing features.

## Reaction Energy Calculation

Reaction enthalpy is computed by:

```python
def calc_dh(E, reactants, products, nr):
    e_r = sum(n * E[phase] for phase, n in reactants)
    e_p = sum(n * E[phase] for phase, n in products)
    return (e_p - e_r) / nr
```

Where:

- `E` is a dictionary of phase formation energies
- `reactants` is a list of reactant phases and coefficients
- `products` is a list of product phases and coefficients
- `nr` is the total atom count used for normalization

Pure elements are manually set to zero because elemental formation enthalpy is zero by definition.

## Defect Energy Calculation

The script solves chemical potentials for three-phase equilibria:

```python
solve_mu(E, phase1, phase2, phase3, elements)
```

Then it computes defect formation energy:

```python
E_f = E_defect - E_perfect - sum(delta_n_i * mu_i)
```

Where:

- `E_defect` is the predicted energy of the defective supercell
- `E_perfect` is the predicted energy of perfect UN
- `delta_n_i` is the atom count change for each element
- `mu_i` is the chemical potential

## Main Workflow

The main function is:

```python
run_agent_b()
```

It runs the workflow in this order:

1. Load CIF structural data.
2. Search databases for missing structural data.
3. Collect all phases needed for reactions and defects.
4. Build RF and NN prediction batches.
5. Predict all required energies.
6. Set pure element formation energies to zero.
7. Print formation enthalpy comparisons.
8. Compute all reaction enthalpies.
9. Compute point-defect formation energies.
10. Analyze defect ranking quality.
11. Write output files.

## Output Files

The script writes:

```text
results/agent_B_results.json
results/agent_B_report.md
results/agent_B_mcp_call_log.json
```

| Output | Purpose |
|---|---|
| `agent_B_results.json` | Machine-readable results |
| `agent_B_report.md` | Human-readable validation report |
| `agent_B_mcp_call_log.json` | Prediction call audit log |

## MCP Note

Despite the filename and the call log name, this script does **not** actually call the MCP servers in `mcp/`.

It uses direct Python calls into `aeris.py`:

```python
# Direct Python prediction (no MCP, no per-call reload)
```

This is faster for a large validation workflow because the models are loaded once and predictions are batched.

In a true MCP setup, an external AI agent would call tool servers such as:

```text
mcp/mcp_aeris_predict.py
mcp/mcp_structure_search.py
mcp/mcp_structure_templates.py
mcp/mcp_aeris_best_structure.py
```

## Practical Issue To Fix

The script imports:

```python
from aeris import load_structure_model, parse_formula, compute_magpie_df
```

But `aeris.py` currently defines:

```python
_compute_magpie_df
```

The public `compute_magpie_df` wrapper appears to be missing. Unless this has already been fixed elsewhere, the script will fail during import.

A small compatibility fix in `aeris.py` would be enough:

```python
def compute_magpie_df(compositions):
    return _compute_magpie_df(compositions)
```

## Summary

`agent_paper_B.py` is best understood as a complete scientific validation pipeline:

```text
Load models
  -> collect structures
  -> predict formation energies
  -> compute reaction energies
  -> compute defect energies
  -> compare against DFT
  -> write reports
```

The AI-agent part is the orchestration pattern. The scientific work is still done by AERIS model functions, structured data, and explicit thermodynamic equations.

