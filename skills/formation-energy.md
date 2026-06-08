---
name: formation-energy
description: Calculate formation energy from first-principles DFT using Quantum ESPRESSO total energies.
argument-hint: "[composition, e.g. UN, UO2, ZrO2] [structure/source] [QE settings]"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Formation Energy From Quantum ESPRESSO

Calculate formation energy using first-principles DFT total energies from Quantum ESPRESSO.

For a compound `A_xB_y`, the formation energy per atom is:

```text
E_form = (E_total(A_xB_y) - x * mu_A - y * mu_B) / (x + y)
```

Where:

- `E_total(A_xB_y)` is the relaxed DFT total energy of the compound cell.
- `mu_A`, `mu_B` are DFT reference chemical potentials from elemental reference phases.
- The result is usually reported in `eV/atom`.

More complicated compounds are expected, like A_xB_yC_z or even larger.

## What This Skill Does

1. Parses the target formula, e.g. `UN`, `UO2`, `ZrO2`.
2. Identifies the required elemental reference phases.
3. Finds or requests crystal structures for:
   - the compound
   - each elemental reference phase
4. Prepares Quantum ESPRESSO input files.
5. Runs the following set of calculations:
   1. Variable-cell relaxation of target and required elemental reference phases.
   2. Use the variable-cell relaxation geometry and cell parameters in a more-accurate DFT calculation (ex. larger basis, tighter threshold)
6. Extracts converged total energies from QE outputs.
7. Computes formation energy per atom.

## Required Inputs

For a reliable calculation, the agent needs:

| Input | Example |
|-------|---------|
| Target composition | `UN`, `UO2`, `ZrO2` |
| Compound structure | CIF, POSCAR, QE input, or database entry |
| Elemental reference structures | alpha-U, N2 molecule, O2 molecule, bcc-Zr, etc. |
| Pseudopotentials | `.UPF` files compatible with QE |
| Exchange-correlation functional | usually PBE unless specified |
| Cutoffs | `ecutwfc`, `ecutrho` |
| k-point meshes | e.g. `8 8 8 0 0 0` |
| Spin/magnetism settings | needed for O2, transition metals, actinides |

If any required input is missing, ask for it or state the assumption used.

## Recommended Workflow

### 1. Parse Formula

For `UN`:

```text
U: 1
N: 1
```

Formation reaction:

```text
U(reference) + 1/2 N2(reference) -> UN
```

Formation energy:

```text
E_form(UN) = E_total(UN) - mu_U - mu_N
```

Since `UN` has two atoms per formula unit, report:

```text
E_form_per_atom = E_form(UN) / 2
```

### 2. Choose Reference States

Reference states must match the elements in their standard or intended DFT reference form.

Examples:

| Element | Common reference |
|---------|------------------|
| U | alpha-U metal, or specified uranium metal phase |
| N | isolated `N2` molecule |
| O | isolated `O2` molecule |
| Zr | hcp-Zr |
| V, Nb, Ta, Cr, Mo, W | usually stable metal phase, often bcc for these transition metals |

Do not silently choose ambiguous references. For actinides, oxides, nitrides, and magnetic molecules, state the reference assumptions explicitly.

### 3. Prepare QE Inputs

Generate separate QE calculations for:

```text
compound/
references/U/
references/N2/
```

For each solid:

- use periodic boundary conditions
- use a converged k-point grid
- relax atomic positions and cell shape

For gas phase molecules such as `N2` or `O2`:

- use a large cubic box, e.g. 15-20 Angstrom
- use `gamma`-point only
- enable spin polarization when needed

### 4. Run Quantum ESPRESSO

Generate input files using templates:

```bash
compound/input.in
references/U/input.in
references/N2/input.in
```

Generate submit scripts using templates:

```bash
compound/submit.slurm
references/U/submit.slurm
references/N2/submit.slurm
```

Submit the jobs:

```bash
cd compounds && sbatch submit.slurm
```

Use the relaxed structure for the final `scf` total energy.

### 5. Extract Total Energies

Quantum ESPRESSO reports total energy in Ry:

```text
!    total energy              =   -1234.567890 Ry
```

Convert to eV:

```text
1 Ry = 13.605693122994 eV
```

Use only converged final total energies.

### 6. Compute Formation Energy

For a formula `A_xB_yC_z`:

```text
E_form_total = E_compound - x * mu_A - y * mu_B - z * mu_C
E_form_per_atom = E_form_total / (x + y + z)
```

Where all energies must be in the same unit, preferably eV.

## Example: UN

Reaction:

```text
U(s) + 1/2 N2(g) -> UN(s)
```

Reference chemical potentials:

```text
mu_U = E_total(U metal per atom)
mu_N = 1/2 * E_total(N2 molecule)
```

Formation energy:

```text
E_form_total = E_total(UN formula unit) - mu_U - mu_N
E_form_per_atom = E_form_total / 2
```

If the QE cell contains `n` formula units of UN:

```text
E_form_per_atom = (E_total(UN cell) - n * mu_U - n * mu_N) / (2n)
```

## Output Format

Report results like this:

```text
Composition: UN
Compound structure: rocksalt UN, SG 225
Reference states:
  U: alpha-U metal, energy = ... eV/atom
  N: N2 molecule, energy = ... eV/atom
QE settings:
  functional: PBE
  pseudopotentials: ...
  ecutwfc: ... Ry
  ecutrho: ... Ry
  k-points: ...
Total energies:
  UN cell: ... eV
  U reference: ... eV/atom
  N reference: ... eV/atom
Formation energy:
  ... eV/formula unit
  ... eV/atom
Convergence notes:
  ...
```

## Project Resources

This repository does not currently provide a complete QE automation pipeline. Use these AERIS resources only as supporting context:

| Resource | Use |
|----------|-----|
| `aeris.py` | Formula parsing and dataset structure lookup if useful |
| `data/Dataset_feature+CN.csv` | Possible source of known structures or metadata |
| `mcp/mcp_structure_search.py` | Optional exact composition lookup |
| `mcp/mcp_structure_templates.py` | Optional template lookup |
| `validation/paper_b/agent_paper_B.py` | Reference thermodynamic bookkeeping pattern, not QE execution |

If QE automation scripts are later added, prefer those scripts over hand-written shell commands.

## Convergence Requirements

Before trusting a formation energy, check:

- total energy convergence with respect to `ecutwfc`
- charge density cutoff `ecutrho`
- k-point mesh convergence for solids
- vacuum size convergence for molecules
- smearing settings for metals
- spin polarization for magnetic references
- consistency of pseudopotentials and exchange-correlation functional

Formation energies are differences of large total energies, so inconsistent settings can produce large errors.

## Important Caveats

- DFT reference choices strongly affect formation energies.
- Molecules like `O2` and `N2` may require spin treatment and can have known PBE errors.
- Actinide systems may require DFT+U, spin-orbit coupling, magnetism, or specialized pseudopotentials.
- A negative formation energy means stable relative to the selected elemental references, not necessarily stable on the full convex hull.
- Convex-hull stability requires comparison against all competing phases.

## Arguments

Parse `$ARGUMENTS` as:

- a composition: `UN`
- a composition plus structure: `UN rocksalt CIF`
- a request with settings: `UO2 fluorite, PBE, ecutwfc 80 Ry`
- a request to compute from existing QE outputs: `formation energy from outputs in qe/UN/`

If the user does not provide structures, pseudopotentials, or QE settings, ask for the missing pieces before claiming a final DFT result.

## When To Use A Different Skill

- Use `reaction-energy` for interface reaction enthalpies from formation energies.
- Use `point-defect` for defect formation energies.
- Use `structure-search` for ML convex-hull screening over structural templates.

