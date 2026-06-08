# Formation Energy DFT Scaffold Report

No RF or NN model predictions are used in this workflow.

## Formation Reactions

| Formula | Formation reaction | Formation energy formula |
|---|---|---|
| UO2 | `0.25U4(s) + O2(g) -> UO2(s)` | `E_form(UO2) = [E(UO2) - 0.25E(U4) - E(O2)] / 3` |

## Phase Inventory

| Phase | Role | Formula | Structure source | nsites | Space group | QE geometry |
|---|---|---|---|---:|---:|---|
| O2 | reference | O2 | generated:diatomic-reference | 2 |  | cell + positions |
| U | reference | U | generated:elemental-orthorhombic-alpha | 4 |  | cell + positions |
| UO2 | compound | UO2 | AERIS dataset:primary | 3 | 225 | cell + positions |

## QE Input Artifacts

| Phase | QE input | Submit script | Geometry block | Structured JSON | Notes |
|---|---|---|---|---|---|
| O2 | `qe_geometry/O2/vc-relax.in` | `qe_geometry/O2/submit.sh` | `qe_geometry/O2/geometry.in` | `qe_geometry/O2/geometry.json` | Generated O2 molecule in 15 A cubic box; initial bond length 1.2075 A; spin-polarized triplet reference recommended. |
| U | `qe_geometry/U/vc-relax.in` | `qe_geometry/U/submit.sh` | `qe_geometry/U/geometry.in` | `qe_geometry/U/geometry.json` | Generated orthorhombic-alpha starting geometry for elemental reference. Relax and confirm this is the intended reference phase. |
| UO2 | `qe_geometry/UO2/vc-relax.in` | `qe_geometry/UO2/submit.sh` | `qe_geometry/UO2/geometry.in` | `qe_geometry/UO2/geometry.json` |  |

## QE Run Files

Run each job from its phase directory so the submit script can find `vc-relax.in`.

| Phase | Input file | Submit script | Submit command |
|---|---|---|---|
| O2 | `qe_geometry/O2/vc-relax.in` | `qe_geometry/O2/submit.sh` | `cd qe_geometry/O2 && sbatch submit.sh` |
| U | `qe_geometry/U/vc-relax.in` | `qe_geometry/U/submit.sh` | `cd qe_geometry/U && sbatch submit.sh` |
| UO2 | `qe_geometry/UO2/vc-relax.in` | `qe_geometry/UO2/submit.sh` | `cd qe_geometry/UO2 && sbatch submit.sh` |

## QE Input File Contents

### O2: vc-relax.in
```text
&CONTROL
  prefix = 'O2.vc-relax'
  pseudo_dir = '~/sample-pseudo-dir'
  calculation = 'vc-relax'
  forc_conv_thr = 1.0d-4
  nstep = 200
/

&SYSTEM
  ibrav = 0
  nat =  2
  ntyp = 1
  ecutwfc = 30
  ecutrho = 120
  occupations = 'smearing'
  smearing = 'mv'
  degauss = 0.01
  nspin = 2
  starting_magnetization(1) = 1.0
/

&ELECTRONS
  conv_thr = 1.0d-8
  mixing_beta = 0.2
/

&IONS
  ion_dynamics = 'bfgs'
/

&CELL
  cell_dynamics = 'bfgs'
  press_conv_thr = 0.5
/

CELL_PARAMETERS angstrom
   15.0000000000   0.0000000000   0.0000000000
   0.0000000000   15.0000000000   0.0000000000
   0.0000000000   0.0000000000   15.0000000000
ATOMIC_SPECIES
  O    15.999000  O.pbe-n-kjpaw_psl.1.0.0.UPF
ATOMIC_POSITIONS angstrom
  O    7.5000000000  7.5000000000  6.8962500000
  O    7.5000000000  7.5000000000  8.1037500000
K_POINTS gamma

! NOTE: Generated O2 molecule in 15 A cubic box; initial bond length 1.2075 A; spin-polarized triplet reference recommended.
```

### U: vc-relax.in
```text
&CONTROL
  prefix = 'U.vc-relax'
  pseudo_dir = '~/sample-pseudo-dir'
  calculation = 'vc-relax'
  forc_conv_thr = 1.0d-4
  nstep = 200
/

&SYSTEM
  ibrav = 0
  nat =  4
  ntyp = 1
  ecutwfc = 30
  ecutrho = 120
  occupations = 'smearing'
  smearing = 'mv'
  degauss = 0.01
/

&ELECTRONS
  conv_thr = 1.0d-8
  mixing_beta = 0.2
/

&IONS
  ion_dynamics = 'bfgs'
/

&CELL
  cell_dynamics = 'bfgs'
  press_conv_thr = 0.5
/

CELL_PARAMETERS angstrom
   2.8540000000   0.0000000000   0.0000000000
   0.0000000000   5.8690000000   0.0000000000
   0.0000000000   0.0000000000   4.9550000000
ATOMIC_SPECIES
  U    238.029000  U.pbe-spfn-kjpaw_psl.1.0.0.UPF
ATOMIC_POSITIONS crystal
  U    0.0000000000  0.1020000000  0.2500000000
  U    0.5000000000  0.3980000000  0.2500000000
  U    0.5000000000  0.6020000000  0.7500000000
  U    0.0000000000  0.8980000000  0.7500000000
K_POINTS gamma

! NOTE: Generated orthorhombic-alpha starting geometry for elemental reference. Relax and confirm this is the intended reference phase.
```

### UO2: vc-relax.in
```text
&CONTROL
  prefix = 'UO2.vc-relax'
  pseudo_dir = '~/sample-pseudo-dir'
  calculation = 'vc-relax'
  forc_conv_thr = 1.0d-4
  nstep = 200
/

&SYSTEM
  ibrav = 0
  nat =  3
  ntyp = 2
  ecutwfc = 30
  ecutrho = 120
  occupations = 'smearing'
  smearing = 'mv'
  degauss = 0.01
/

&ELECTRONS
  conv_thr = 1.0d-8
  mixing_beta = 0.2
/

&IONS
  ion_dynamics = 'bfgs'
/

&CELL
  cell_dynamics = 'bfgs'
  press_conv_thr = 0.5
/

CELL_PARAMETERS angstrom
   3.8565670000   0.0000000000   0.0000000000
   1.9282835000   3.3398849934   0.0000000000
   1.9282835000   1.1132949978   3.1488737696
ATOMIC_SPECIES
  U    238.029000  U.pbe-spfn-kjpaw_psl.1.0.0.UPF
  O    15.999000  O.pbe-n-kjpaw_psl.1.0.0.UPF
ATOMIC_POSITIONS crystal
  U    0.5000000000  0.5000000000  0.5000000000
  O    0.2500000000  0.2500000000  0.2500000000
  O    0.7500000000  0.7500000000  0.7500000000
K_POINTS gamma
```


## Submit Script Contents

### O2: submit.sh
```bash
#!/bin/bash

#SBATCH -A stf243
#SBATCH -N 1
#SBATCH -t 1:00:00
#SBATCH -J O2.vc-relax
#SBATCH --output=%x-%j.out

prefix=O2.vc-relax
input=vc-relax.in

module load gcc-native/14.2
module load cray-mpich/9.1.0
module load rocm/7.0.2
module load q-e-sirius/1.0.2-mpi-omp

export HDF5_USE_FILE_LOCKING=FALSE
export SIRIUS_VERBOSITY=1

srun -N 1 -n 8 -c 7 --gpus-per-task=1 --gpu-bind=closest pw.x -in ${input} > ${prefix}.log
```

### U: submit.sh
```bash
#!/bin/bash

#SBATCH -A stf243
#SBATCH -N 1
#SBATCH -t 1:00:00
#SBATCH -J U.vc-relax
#SBATCH --output=%x-%j.out

prefix=U.vc-relax
input=vc-relax.in

module load gcc-native/14.2
module load cray-mpich/9.1.0
module load rocm/7.0.2
module load q-e-sirius/1.0.2-mpi-omp

export HDF5_USE_FILE_LOCKING=FALSE
export SIRIUS_VERBOSITY=1

srun -N 1 -n 8 -c 7 --gpus-per-task=1 --gpu-bind=closest pw.x -in ${input} > ${prefix}.log
```

### UO2: submit.sh
```bash
#!/bin/bash

#SBATCH -A stf243
#SBATCH -N 1
#SBATCH -t 1:00:00
#SBATCH -J UO2.vc-relax
#SBATCH --output=%x-%j.out

prefix=UO2.vc-relax
input=vc-relax.in

module load gcc-native/14.2
module load cray-mpich/9.1.0
module load rocm/7.0.2
module load q-e-sirius/1.0.2-mpi-omp

export HDF5_USE_FILE_LOCKING=FALSE
export SIRIUS_VERBOSITY=1

srun -N 1 -n 8 -c 7 --gpus-per-task=1 --gpu-bind=closest pw.x -in ${input} > ${prefix}.log
```


## Total Energies

| Phase | Total energy (eV) | eV/atom | n atoms | Source |
|---|---:|---:|---:|---|

## Formation Energies

No formation energies were computed because required QE total energies are missing.

## Missing Inputs

- UO2: compound total energy for UO2, reference total energy for U (U), reference total energy for O (O2)

## Notes

- Confirm elemental reference phases before using values scientifically.
- QE calculations must use consistent pseudopotentials, functionals, cutoffs, k-points, smearing, and spin settings.
- Negative formation energy means stable relative to selected elemental references, not necessarily stable on the convex hull.
