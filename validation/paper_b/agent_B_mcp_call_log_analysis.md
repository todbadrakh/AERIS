# Agent B MCP Call Log Analysis

Source file: `validation/paper_b/agent_B_mcp_call_log.json`

This file is an audit trail of per-composition model predictions used by `agent_paper_B.py`. Despite the `mcp` name, these entries were produced by direct Python calls in the validation script, not by an external MCP server process.

## Executive Summary

- Raw log entries: **318**
- Unique compositions: **49**
- Unique prediction states, counting model and structure context: **98**
- Model calls: **RF=159**, **NN=159**
- Entries with structural descriptors: **158**
- Entries without structural descriptors: **160**

The log is intentionally repetitive. Defect proxy compositions such as `U31N32`, `U32N31`, and `U32N33` are reused across many three-phase equilibria. The repeated entries reflect downstream thermodynamic contexts, not different raw ML predictions.

## What One Entry Means

Each JSON record has this shape:

```json
{
  "timestamp": "...",
  "model": "RF" or "NN",
  "composition": "Cr2N",
  "structure_info": { "spacegroup_number": 162, "CN_avg": 4.0 },
  "per_atom_eV": -0.3026609203029631
}
```

- `model`: which model produced the prediction.
- `composition`: formula or supercell proxy formula that was predicted.
- `structure_info`: structural descriptors used by RF. This is normally `null` for NN because the NN is composition-only.
- `per_atom_eV`: predicted formation energy per atom before reaction or defect formulas are applied.

## Model And Structure Usage

| Model | Entries | With structure | Without structure |
|---|---:|---:|---:|
| RF | 159 | 158 | 1 |
| NN | 159 | 0 | 159 |

Interpretation: RF is the structure-aware model, so almost every RF call has `structure_info`. NN is composition-only, so every NN call has `structure_info: null`.

## Entry Categories

| Category | Raw entries | Unique compositions | Meaning |
|---|---:|---:|---|
| pure element | 14 | 7 | Pure elements such as U, V, Nb, Ta, Cr, Mo, W. These predictions are logged, then formation energies are overridden to zero in thermodynamic calculations. |
| compound phase | 54 | 27 | Actual compound phases used in formation and reaction enthalpy tables. |
| UN vacancy/interstitial proxy | 150 | 3 | Supercell proxy formulas for U vacancy, N vacancy, and N interstitial. |
| substitution defect proxy | 100 | 12 | Supercell proxy formulas for metal substitution on U or N sites. |

## Energy Ranges By Model

| Model | Entries | Minimum eV/atom | Maximum eV/atom | Mean eV/atom |
|---|---:|---:|---:|---:|
| NN | 159 | -1.646 | +0.266 | -1.317 |
| RF | 159 | -1.715 | +0.998 | -1.402 |

## Energy Ranges By Category

| Category | Model | Entries | Minimum | Maximum | Mean |
|---|---|---:|---:|---:|---:|
| pure element | RF | 7 | +0.425 | +0.998 | +0.633 |
| pure element | NN | 7 | -0.245 | +0.266 | +0.003 |
| compound phase | RF | 27 | -1.715 | +0.787 | -0.772 |
| compound phase | NN | 27 | -1.646 | -0.199 | -0.814 |
| UN vacancy/interstitial proxy | RF | 75 | -1.699 | -1.687 | -1.695 |
| UN vacancy/interstitial proxy | NN | 75 | -1.589 | -1.457 | -1.545 |
| substitution defect proxy | RF | 50 | -1.611 | -1.550 | -1.587 |
| substitution defect proxy | NN | 50 | -1.565 | -1.228 | -1.430 |

## Most Common Repeated Compositions

| Composition | Raw entries | Why repeated |
|---|---:|---|
| `U31N32` | 50 | Shared defect proxy reused across all 25 equilibria, with RF and NN entries. |
| `U32N31` | 50 | Shared defect proxy reused across all 25 equilibria, with RF and NN entries. |
| `U32N33` | 50 | Shared defect proxy reused across all 25 equilibria, with RF and NN entries. |
| `U31V1N32` | 10 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U32V1N31` | 10 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U31Ta1N32` | 10 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U32Ta1N31` | 10 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U31Cr1N32` | 10 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U32Cr1N31` | 10 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U31Nb1N32` | 8 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U32Nb1N31` | 8 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U31Mo1N32` | 6 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U32Mo1N31` | 6 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U31W1N32` | 6 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |
| `U32W1N31` | 6 | Metal-specific substitution proxy reused across that metal's equilibria, with RF and NN entries. |

## Structural Context

Top space groups appearing in `structure_info`:

| Space group | Entries | Typical use in this log |
|---:|---:|---|
| 225 | 78 | UN rocksalt and related vacancy/interstitial defect context. |
| 229 | 56 | BCC metal structural context for pure metals and substitution defects. |
| 162 | 4 | Compound phase structural descriptor. |
| 62 | 4 | Compound phase structural descriptor. |
| 193 | 2 | Compound phase structural descriptor. |
| 187 | 2 | Compound phase structural descriptor. |
| 167 | 1 | Compound phase structural descriptor. |
| 176 | 1 | Compound phase structural descriptor. |
| 9 | 1 | Compound phase structural descriptor. |
| 141 | 1 | Compound phase structural descriptor. |
| 2 | 1 | Compound phase structural descriptor. |
| 186 | 1 | Compound phase structural descriptor. |

## Largest RF vs NN Differences

The table below compares the first logged RF and NN prediction for each composition. Large gaps indicate cases where structure-aware and composition-only models disagree strongly on the raw formation-energy prediction.

| Composition | Category | RF eV/atom | NN eV/atom | RF - NN |
|---|---|---:|---:|---:|
| `WN2` | compound phase | +0.787 | -0.199 | +0.986 |
| `W` | pure element | +0.998 | +0.091 | +0.907 |
| `Nb` | pure element | +0.526 | -0.245 | +0.771 |
| `U` | pure element | +0.896 | +0.137 | +0.759 |
| `Mo` | pure element | +0.576 | -0.064 | +0.639 |
| `Ta` | pure element | +0.515 | -0.082 | +0.597 |
| `V` | pure element | +0.425 | -0.083 | +0.509 |
| `W2N3` | compound phase | +0.246 | -0.243 | +0.489 |
| `V2N3` | compound phase | -1.191 | -0.845 | -0.346 |
| `WN` | compound phase | +0.124 | -0.209 | +0.333 |
| `U32W1N31` | substitution defect proxy | -1.550 | -1.228 | -0.322 |
| `Mo2N` | compound phase | -0.095 | -0.389 | +0.294 |
| `U32Ta1N31` | substitution defect proxy | -1.561 | -1.292 | -0.269 |
| `Cr3N2` | compound phase | -0.612 | -0.349 | -0.264 |
| `CrN` | compound phase | -0.694 | -0.440 | -0.254 |

Notable pattern: the largest disagreements are W-containing phases and pure elements. Pure-element predictions are not used directly as formation enthalpies in the reaction calculations because the script resets pure elements to `0.0` by definition.

## Phase Prediction Table

This table lists non-defect compositions. These values feed formation enthalpy and reaction enthalpy calculations before pure-element correction.

| Composition | Category | RF eV/atom | NN eV/atom | RF - NN |
|---|---|---:|---:|---:|
| `Cr2N` | compound phase | -0.303 | -0.222 | -0.081 |
| `Cr3N2` | compound phase | -0.612 | -0.349 | -0.264 |
| `Cr3N4` | compound phase | -0.505 | -0.311 | -0.194 |
| `CrN` | compound phase | -0.694 | -0.440 | -0.254 |
| `Mo15N16` | compound phase | -0.413 | -0.443 | +0.030 |
| `Mo2N` | compound phase | -0.095 | -0.389 | +0.294 |
| `Mo2N3` | compound phase | -0.124 | -0.355 | +0.231 |
| `MoN` | compound phase | -0.346 | -0.499 | +0.153 |
| `Nb2N` | compound phase | -0.814 | -1.009 | +0.196 |
| `Nb5N6` | compound phase | -1.062 | -1.240 | +0.178 |
| `NbN` | compound phase | -1.081 | -1.277 | +0.196 |
| `Ta2N` | compound phase | -0.977 | -0.733 | -0.244 |
| `Ta3N5` | compound phase | -1.163 | -1.291 | +0.128 |
| `Ta5N6` | compound phase | -1.176 | -1.252 | +0.075 |
| `TaN` | compound phase | -1.264 | -1.121 | -0.144 |
| `U2CrN3` | compound phase | -1.479 | -1.407 | -0.072 |
| `UN` | compound phase | -1.715 | -1.554 | -0.161 |
| `UNbN2` | compound phase | -1.451 | -1.646 | +0.195 |
| `UTaN2` | compound phase | -1.588 | -1.512 | -0.076 |
| `UVN2` | compound phase | -1.615 | -1.445 | -0.170 |
| `V2N` | compound phase | -0.930 | -0.802 | -0.128 |
| `V2N3` | compound phase | -1.191 | -0.845 | -0.346 |
| `V8N` | compound phase | -0.280 | -0.210 | -0.070 |
| `VN` | compound phase | -1.136 | -0.979 | -0.158 |
| `W2N3` | compound phase | +0.246 | -0.243 | +0.489 |
| `WN` | compound phase | +0.124 | -0.209 | +0.333 |
| `WN2` | compound phase | +0.787 | -0.199 | +0.986 |
| `Cr` | pure element | +0.498 | +0.266 | +0.232 |
| `Mo` | pure element | +0.576 | -0.064 | +0.639 |
| `Nb` | pure element | +0.526 | -0.245 | +0.771 |
| `Ta` | pure element | +0.515 | -0.082 | +0.597 |
| `U` | pure element | +0.896 | +0.137 | +0.759 |
| `V` | pure element | +0.425 | -0.083 | +0.509 |
| `W` | pure element | +0.998 | +0.091 | +0.907 |

## Defect Proxy Prediction Table

These are not literal relaxed defect structures. They are composition proxies for the defect-supercell formulas used in the script.

| Composition | Category | RF eV/atom | NN eV/atom | RF - NN | Raw entries |
|---|---|---:|---:|---:|---:|
| `U31Cr1N32` | substitution defect proxy | -1.599 | -1.541 | -0.059 | 10 |
| `U31Mo1N32` | substitution defect proxy | -1.609 | -1.528 | -0.081 | 6 |
| `U31N32` | UN vacancy/interstitial proxy | -1.699 | -1.589 | -0.110 | 50 |
| `U31Nb1N32` | substitution defect proxy | -1.611 | -1.565 | -0.046 | 8 |
| `U31Ta1N32` | substitution defect proxy | -1.592 | -1.502 | -0.089 | 10 |
| `U31V1N32` | substitution defect proxy | -1.608 | -1.510 | -0.097 | 10 |
| `U31W1N32` | substitution defect proxy | -1.594 | -1.461 | -0.133 | 6 |
| `U32Cr1N31` | substitution defect proxy | -1.576 | -1.386 | -0.190 | 10 |
| `U32Mo1N31` | substitution defect proxy | -1.579 | -1.356 | -0.223 | 6 |
| `U32N31` | UN vacancy/interstitial proxy | -1.687 | -1.457 | -0.229 | 50 |
| `U32N33` | UN vacancy/interstitial proxy | -1.699 | -1.589 | -0.110 | 50 |
| `U32Nb1N31` | substitution defect proxy | -1.584 | -1.403 | -0.181 | 8 |
| `U32Ta1N31` | substitution defect proxy | -1.561 | -1.292 | -0.269 | 10 |
| `U32V1N31` | substitution defect proxy | -1.581 | -1.347 | -0.234 | 10 |
| `U32W1N31` | substitution defect proxy | -1.550 | -1.228 | -0.322 | 6 |

## How To Use This Log

- Use this file to audit raw model predictions.
- Use `agent_B_results.json` for derived reaction enthalpies, defect formation energies, and validation metrics.
- Use `agent_B_report.md` for the scientific interpretation.
- Do not interpret repeated entries as independent model evaluations; many are reused defect proxies across multiple equilibria.

