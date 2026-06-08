#!/usr/bin/env python3
"""DFT formation-energy scaffold using Quantum ESPRESSO total energies.

No RF/NN models are used. The script:
  1. builds compound/reference phase records,
  2. finds or generates QE geometries,
  3. writes pw.x input files,
  4. reads QE total energies when available,
  5. computes formation energies.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

warnings.filterwarnings("ignore")

import pandas as pd

try:
    from pymatgen.analysis.local_env import CrystalNN
    from pymatgen.core.structure import Structure
except Exception:
    CrystalNN = None
    Structure = None


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

RY_TO_EV = 13.605693122994
BOX = 15.0
DEFAULT_PSEUDO_DIR = "/lustre/orion/nfu107/proj-shared/todbadrakh/pseudopotentials"
DEFAULT_QE_ROOT = SCRIPT_DIR / "qe"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results" / "formation_energy"
CIF_DIR = PROJECT_ROOT / "data" / "cif"
DB_PATHS = [
    ("primary", PROJECT_ROOT / "data" / "Dataset_feature+CN.csv"),
    ("extended", PROJECT_ROOT / "data" / "Dataset_feture+CN_exp.csv"),
]

MASSES = {
    "H": 1.008, "N": 14.007, "O": 15.999, "F": 18.998, "Cl": 35.45,
    "Ti": 47.867, "Zr": 91.224, "Hf": 178.49, "V": 50.942,
    "Nb": 92.906, "Ta": 180.948, "Cr": 51.996, "Mo": 95.95,
    "W": 183.84, "Fe": 55.845, "Ni": 58.693, "Cu": 63.546,
    "Al": 26.982, "U": 238.029,
}

PSEUDOS = {
    "N": "N.pbe-n-kjpaw_psl.1.0.0.UPF",
    "O": "O.pbe-n-kjpaw_psl.1.0.0.UPF",
    "Ti": "Ti.pbe-spn-kjpaw_psl.1.0.0.UPF",
    "U": "U.pbe-spfn-kjpaw_psl.1.0.0.UPF",
    "Zr": "Zr.pbe-spn-kjpaw_psl.1.0.0.UPF",
    "V": "V.pbe-spnl-kjpaw_psl.1.0.0.UPF",
    "Nb": "Nb.pbe-spn-kjpaw_psl.1.0.0.UPF",
    "Ta": "Ta.pbe-spfn-kjpaw_psl.1.0.0.UPF",
    "Cr": "Cr.pbe-spn-kjpaw_psl.1.0.0.UPF",
    "Mo": "Mo.pbe-spn-kjpaw_psl.1.0.0.UPF",
    "W": "W.pbe-spn-kjpaw_psl.1.0.0.UPF",
}

DIATOMIC = {
    "H2": ("H", 0.7414, "closed-shell singlet"),
    "N2": ("N", 1.0977, "closed-shell singlet"),
    "O2": ("O", 1.2075, "spin-polarized triplet reference recommended"),
    "F2": ("F", 1.4119, "closed-shell singlet"),
    "Cl2": ("Cl", 1.9878, "closed-shell singlet"),
}

ELEMENTAL = {
    "Ti": ("hcp", {"a": 2.951, "c": 4.684}),
    "Zr": ("hcp", {"a": 3.232, "c": 5.147}),
    "Hf": ("hcp", {"a": 3.195, "c": 5.051}),
    "V": ("bcc", {"a": 3.03}),
    "Nb": ("bcc", {"a": 3.30}),
    "Ta": ("bcc", {"a": 3.30}),
    "Cr": ("bcc", {"a": 2.88}),
    "Mo": ("bcc", {"a": 3.15}),
    "W": ("bcc", {"a": 3.16}),
    "Fe": ("bcc", {"a": 2.87}),
    "Ni": ("fcc", {"a": 3.52}),
    "Cu": ("fcc", {"a": 3.61}),
    "Al": ("fcc", {"a": 4.05}),
    "U": ("orthorhombic-alpha", {"a": 2.854, "b": 5.869, "c": 4.955, "y": 0.102}),
}

STRUCT_KEYS = [
    "spacegroup_number", "density_atomic", "CN_avg", "CN_min", "CN_max",
    "nsites", "volume", "density", "lattice_a", "lattice_b", "lattice_c",
    "lattice_alpha", "lattice_beta", "lattice_gamma",
]


@dataclass
class Phase:
    name: str
    formula: str
    role: str
    composition: Dict[str, float]
    n_atoms_formula: float
    structure_source: str = "missing"
    structure: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


@dataclass
class Pos:
    element: str
    x: float
    y: float
    z: float
    coordinate_type: str = "crystal"


@dataclass
class Geometry:
    phase: str
    source: str
    cell_units: str
    cell_parameters: List[List[float]]
    atomic_position_units: str
    atomic_positions: List[Pos]
    notes: Optional[str] = None


@dataclass
class Energy:
    phase: str
    total_energy_ev: float
    n_atoms_cell: float
    source: str
    total_energy_ry: Optional[float] = None

    @property
    def ev_per_atom(self) -> float:
        return self.total_energy_ev / self.n_atoms_cell


@dataclass
class QE:
    pseudo_dir: str = DEFAULT_PSEUDO_DIR
    calculation: str = "vc-relax"
    ecutwfc: float = 30.0
    ecutrho: float = 120.0
    occupations: str = "smearing"
    smearing: str = "mv"
    degauss: float = 0.01
    forc_conv_thr: str = "1.0d-4"
    nstep: int = 200
    conv_thr: str = "1.0d-8"
    mixing_beta: float = 0.2
    ion_dynamics: str = "bfgs"
    cell_dynamics: str = "bfgs"
    press_conv_thr: float = 0.5
    k_points: str = "gamma"


@dataclass
class Submit:
    account: str = "stf243"
    nodes: int = 1
    walltime: str = "1:00:00"
    ntasks: int = 8
    cpus_per_task: int = 7
    gpus_per_task: int = 1
    modules: Tuple[str, ...] = (
        "gcc-native/14.2",
        "cray-mpich/9.1.0",
        "rocm/7.0.2",
        "q-e-sirius/1.0.2-mpi-omp",
    )


def parse_formula(formula: str) -> Dict[str, float]:
    parts = re.findall(r"([A-Z][a-z]?)([0-9]*\.?[0-9]*)", str(formula).strip())
    if not parts:
        raise ValueError(f"Could not parse formula: {formula}")
    out: Dict[str, float] = {}
    for el, num in parts:
        out[el] = out.get(el, 0.0) + (float(num) if num else 1.0)
    return out


def fmt(x: float) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-10 else f"{x:g}"


def coeff(x: float) -> str:
    return "" if abs(x - 1.0) < 1e-10 else fmt(x)


def ref_phase(element: str) -> str:
    return {"H": "H2", "N": "N2", "O": "O2", "F": "F2", "Cl": "Cl2"}.get(element, element)


def canon(formula: str) -> str:
    return "".join(f"{el}{fmt(n)}" for el, n in sorted(parse_formula(formula).items()))


def counts(geom: Geometry) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for p in geom.atomic_positions:
        out[p.element] = out.get(p.element, 0.0) + 1.0
    return out


def formula_from_counts(c: Dict[str, float], order: Iterable[str] = ()) -> str:
    elems = [e for e in order if e in c] + [e for e in c if e not in order]
    return "".join(f"{e}{'' if abs(c[e]-1) < 1e-10 else fmt(c[e])}" for e in elems)


def cell_formula(phase: Phase, geom: Optional[Geometry]) -> str:
    return formula_from_counts(counts(geom), parse_formula(phase.formula).keys()) if geom else phase.formula


def cell_label(phase: Phase, geom: Optional[Geometry]) -> str:
    state = "g" if geom and geom.source == "generated:diatomic-reference" else "s"
    return f"{cell_formula(phase, geom)}({state})"


def cell_reaction(formula: str, phases: Dict[str, Phase], geoms: Dict[str, Geometry]) -> str:
    target = phases[formula]
    tg = geoms.get(formula)
    tcounts = counts(tg) if tg else parse_formula(formula)
    lhs = []
    for el, n in tcounts.items():
        rname = ref_phase(el)
        rg = geoms.get(rname)
        rcounts = counts(rg) if rg else parse_formula(rname)
        lhs.append(f"{coeff(n / rcounts[el])}{cell_label(phases[rname], rg)}")
    return " + ".join(lhs) + f" -> {cell_label(target, tg)}"


def cell_formula_expr(formula: str, phases: Dict[str, Phase], geoms: Dict[str, Geometry]) -> str:
    tg = geoms.get(formula)
    tcounts = counts(tg) if tg else parse_formula(formula)
    tlabel = cell_formula(phases[formula], tg)
    refs = []
    for el, n in tcounts.items():
        rname = ref_phase(el)
        rg = geoms.get(rname)
        rcounts = counts(rg) if rg else parse_formula(rname)
        refs.append(f"{coeff(n / rcounts[el])}E({cell_formula(phases[rname], rg)})")
    return f"E_form({tlabel}) = [E({tlabel}) - " + " - ".join(refs) + f"] / {fmt(sum(tcounts.values()))}"


def lattice(a: float, b: float, c: float, alpha: float, beta: float, gamma: float) -> List[List[float]]:
    al, be, ga = map(math.radians, [alpha, beta, gamma])
    bx, by = b * math.cos(ga), b * math.sin(ga)
    cx = c * math.cos(be)
    cy = c * (math.cos(al) - math.cos(be) * math.cos(ga)) / math.sin(ga)
    cz = math.sqrt(max(c * c - cx * cx - cy * cy, 0.0))
    return [[a, 0, 0], [bx, by, 0], [cx, cy, cz]]


def geom_from_cif(path: Path) -> Dict[str, Any]:
    if Structure is None:
        raise RuntimeError("pymatgen is required for CIF parsing")
    s = Structure.from_file(str(path))
    sym, sg = s.get_space_group_info()
    lat = s.lattice
    d: Dict[str, Any] = {
        "formula": s.composition.reduced_formula,
        "spacegroup_symbol": sym,
        "spacegroup_number": int(sg),
        "nsites": len(s),
        "volume": float(lat.volume),
        "density": float(s.density),
        "lattice_a": float(lat.a),
        "lattice_b": float(lat.b),
        "lattice_c": float(lat.c),
        "lattice_alpha": float(lat.alpha),
        "lattice_beta": float(lat.beta),
        "lattice_gamma": float(lat.gamma),
        "cell_parameters_angstrom": [[float(v) for v in row] for row in lat.matrix],
        "atomic_positions_crystal": [
            {"element": str(site.specie), "x": float(site.frac_coords[0]),
             "y": float(site.frac_coords[1]), "z": float(site.frac_coords[2])}
            for site in s
        ],
    }
    if CrystalNN:
        try:
            cn = [float(CrystalNN().get_cn(s, i)) for i in range(len(s))]
            d.update(CN_avg=sum(cn) / len(cn), CN_min=min(cn), CN_max=max(cn))
        except Exception:
            pass
    return d


def parse_structure_text(text: str) -> Optional[Dict[str, Any]]:
    abc = re.search(r"abc\s*:\s*([-+\d.]+)\s+([-+\d.]+)\s+([-+\d.]+)", str(text))
    ang = re.search(r"angles\s*:\s*([-+\d.]+)\s+([-+\d.]+)\s+([-+\d.]+)", str(text))
    if not abc or not ang:
        return None
    pos = []
    for line in str(text).splitlines():
        m = re.match(r"\s*\d+\s+([A-Z][a-z]?)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)", line)
        if m:
            pos.append({"element": m.group(1), "x": float(m.group(2)), "y": float(m.group(3)), "z": float(m.group(4))})
    if not pos:
        return None
    return {
        "cell_parameters_angstrom": lattice(*(float(x) for x in (*abc.groups(), *ang.groups()))),
        "atomic_positions_crystal": pos,
    }


def generated_molecule(phase: Phase) -> Optional[Geometry]:
    if phase.formula not in DIATOMIC:
        return None
    el, bond, spin = DIATOMIC[phase.formula]
    z0, z1 = BOX / 2 - bond / 2, BOX / 2 + bond / 2
    return Geometry(
        phase.name, "generated:diatomic-reference", "angstrom",
        [[BOX, 0, 0], [0, BOX, 0], [0, 0, BOX]], "angstrom",
        [Pos(el, BOX / 2, BOX / 2, z0, "angstrom"), Pos(el, BOX / 2, BOX / 2, z1, "angstrom")],
        f"Generated {phase.formula} molecule in {BOX:g} A cubic box; initial bond length {bond:g} A; {spin}.",
    )


def generated_element(phase: Phase) -> Optional[Geometry]:
    if phase.formula not in ELEMENTAL or len(phase.composition) != 1:
        return None
    el = next(iter(phase.composition))
    proto, p = ELEMENTAL[phase.formula]
    if proto == "bcc":
        a = p["a"]; cell = [[a, 0, 0], [0, a, 0], [0, 0, a]]
        pos = [Pos(el, 0, 0, 0), Pos(el, .5, .5, .5)]
    elif proto == "fcc":
        a = p["a"]; cell = [[a, 0, 0], [0, a, 0], [0, 0, a]]
        pos = [Pos(el, 0, 0, 0), Pos(el, 0, .5, .5), Pos(el, .5, 0, .5), Pos(el, .5, .5, 0)]
    elif proto == "hcp":
        a, c = p["a"], p["c"]
        cell = [[a, 0, 0], [-.5 * a, math.sqrt(3) * a / 2, 0], [0, 0, c]]
        pos = [Pos(el, 1/3, 2/3, .25), Pos(el, 2/3, 1/3, .75)]
    elif proto == "orthorhombic-alpha":
        y = p["y"]; cell = [[p["a"], 0, 0], [0, p["b"], 0], [0, 0, p["c"]]]
        pos = [Pos(el, 0, y, .25), Pos(el, .5, .5-y, .25), Pos(el, .5, .5+y, .75), Pos(el, 0, 1-y, .75)]
    else:
        return None
    return Geometry(
        phase.name, f"generated:elemental-{proto}", "angstrom", cell, "crystal", pos,
        f"Generated {proto} starting geometry for elemental reference. Relax and confirm this is the intended reference phase.",
    )


def geometry_for(phase: Phase) -> Optional[Geometry]:
    s = dict(phase.structure or {})
    if "raw_structure_string" in s:
        s.update(parse_structure_text(s["raw_structure_string"]) or {})
    cell, raw_pos = s.get("cell_parameters_angstrom"), s.get("atomic_positions_crystal")
    if cell and raw_pos:
        return Geometry(
            phase.name, phase.structure_source, "angstrom", cell, "crystal",
            [Pos(str(p["element"]), float(p["x"]), float(p["y"]), float(p["z"])) for p in raw_pos],
        )
    keys = ["lattice_a", "lattice_b", "lattice_c", "lattice_alpha", "lattice_beta", "lattice_gamma"]
    if all(k in s for k in keys):
        return Geometry(
            phase.name, phase.structure_source, "angstrom",
            lattice(*(float(s[k]) for k in keys)), "crystal", [],
            "Cell parameters generated from lattice constants; atomic positions are unavailable.",
        )
    return generated_molecule(phase) or generated_element(phase)


def geometry_block(g: Geometry) -> str:
    lines = cell_lines(g) + ["", f"ATOMIC_POSITIONS {g.atomic_position_units}"]
    lines += [f"  {p.element:<3} {p.x: .10f} {p.y: .10f} {p.z: .10f}" for p in g.atomic_positions] or [
        "  # TODO: atomic positions unavailable from current structure source"
    ]
    if g.notes:
        lines += ["", f"# NOTE: {g.notes}"]
    return "\n".join(lines) + "\n"


def cell_lines(g: Geometry) -> List[str]:
    return [f"CELL_PARAMETERS {g.cell_units}"] + [
        "  " + "  ".join(f"{v: .10f}" for v in row) for row in g.cell_parameters
    ]


def position_lines(g: Geometry) -> List[str]:
    return [f"ATOMIC_POSITIONS {g.atomic_position_units}"] + [
        f"  {p.element:<3} {p.x: .10f} {p.y: .10f} {p.z: .10f}" for p in g.atomic_positions
    ]


def qe_input(phase: str, g: Geometry, q: QE) -> str:
    elems = list(dict.fromkeys(p.element for p in g.atomic_positions))
    lines = [
        "&CONTROL",
        f"  prefix = '{phase}.{q.calculation}'",
        f"  pseudo_dir = '{q.pseudo_dir}'",
        f"  calculation = '{q.calculation}'",
        f"  forc_conv_thr = {q.forc_conv_thr}",
        f"  nstep = {q.nstep}",
        "/\n",
        "&SYSTEM",
        "  ibrav = 0",
        f"  nat = {len(g.atomic_positions):2d}",
        f"  ntyp = {len(elems)}",
        f"  ecutwfc = {q.ecutwfc:g}",
        f"  ecutrho = {q.ecutrho:g}",
        f"  occupations = '{q.occupations}'",
        f"  smearing = '{q.smearing}'",
        f"  degauss = {q.degauss:g}",
    ]
    if phase == "O2":
        lines += ["  nspin = 2", "  starting_magnetization(1) = 1.0"]
    lines += [
        "/\n", "&ELECTRONS", f"  conv_thr = {q.conv_thr}", f"  mixing_beta = {q.mixing_beta:g}", "/\n",
        "&IONS", f"  ion_dynamics = '{q.ion_dynamics}'", "/\n",
        "&CELL", f"  cell_dynamics = '{q.cell_dynamics}'", f"  press_conv_thr = {q.press_conv_thr:g}", "/\n",
        *cell_lines(g), "ATOMIC_SPECIES",
    ]
    lines += [f"  {e:<3} {MASSES.get(e, 0.0): .6f}  {PSEUDOS.get(e, e + '.UPF')}" for e in elems]
    lines += position_lines(g)
    lines += ["K_POINTS gamma" if q.k_points == "gamma" else f"K_POINTS automatic\n  {q.k_points}"]
    if g.notes:
        lines += ["", f"! NOTE: {g.notes}"]
    return "\n".join(lines) + "\n"


def submit_script(phase: str, q: QE, s: Submit, input_file: str = "vc-relax.in") -> str:
    prefix = f"{phase}.{q.calculation}"
    lines = [
        "#!/bin/bash",
        "",
        f"#SBATCH -A {s.account}",
        f"#SBATCH -N {s.nodes}",
        f"#SBATCH -t {s.walltime}",
        f"#SBATCH -J {prefix}",
        "#SBATCH --output=%x-%j.out",
        "",
        f"prefix={prefix}",
        f"input={input_file}",
        "",
    ]
    lines += [f"module load {m}" for m in s.modules]
    lines += [
        "",
        "export HDF5_USE_FILE_LOCKING=FALSE",
        "export SIRIUS_VERBOSITY=1",
        "",
        (
            f"srun -N {s.nodes} -n {s.ntasks} -c {s.cpus_per_task} "
            f"--gpus-per-task={s.gpus_per_task} --gpu-bind=closest "
            "pw.x -in ${input} > ${prefix}.log"
        ),
        "",
    ]
    return "\n".join(lines)


def load_cifs() -> Dict[str, Dict[str, Any]]:
    if not CIF_DIR.is_dir():
        return {}
    out = {}
    for path in sorted(CIF_DIR.glob("*.cif")):
        try:
            out[path.stem] = geom_from_cif(path)
            print(f"  [CIF] {path.stem}: SG={out[path.stem].get('spacegroup_number')}, nsites={out[path.stem].get('nsites')}")
        except Exception as exc:
            print(f"  [CIF] {path.stem}: FAILED ({exc})")
    return out


def safe_canon(x: str) -> Optional[str]:
    try:
        return canon(x)
    except Exception:
        return None


def load_dbs() -> List[Tuple[str, pd.DataFrame]]:
    dbs = []
    for label, path in DB_PATHS:
        if not path.exists():
            continue
        try:
            db = pd.read_csv(path, low_memory=False)
        except Exception:
            continue
        if "composition_reduced" in db.columns:
            db = db.copy()
            db["_norm"] = db["composition_reduced"].apply(lambda v: safe_canon(str(v).replace(" ", "")))
            dbs.append((label, db))
    return dbs


def db_structure(phase: str, dbs: List[Tuple[str, pd.DataFrame]]) -> Optional[Dict[str, Any]]:
    target = canon(phase)
    for label, db in dbs:
        m = db[db["_norm"] == target]
        if m.empty:
            continue
        row = m.iloc[0]
        out: Dict[str, Any] = {"database": label}
        if "structure" in db.columns and pd.notna(row.get("structure")):
            out["raw_structure_string"] = str(row.get("structure"))
        for col in STRUCT_KEYS:
            if col not in db.columns:
                continue
            try:
                val = float(row[col])
                if not math.isnan(val):
                    out[col] = int(val) if col in ("spacegroup_number", "nsites") else val
            except Exception:
                pass
        return out
    return None


def build_phases(formulas: Iterable[str]) -> Dict[str, Phase]:
    phases: Dict[str, Phase] = {}
    for formula in formulas:
        comp = parse_formula(formula)
        phases[formula] = Phase(formula, formula, "compound", comp, sum(comp.values()))
        for el in comp:
            ref = ref_phase(el)
            if ref not in phases:
                rc = parse_formula(ref)
                phases[ref] = Phase(ref, ref, "reference", rc, sum(rc.values()), notes=f"default reference for {el}")
    return phases


def attach_structures(phases: Dict[str, Phase]) -> None:
    print("\nPhase 0a: Loading CIF structural data...")
    cifs, dbs = load_cifs(), load_dbs()
    print("\nPhase 0b: Attaching structure metadata...")
    for name, phase in phases.items():
        if name in cifs:
            phase.structure, phase.structure_source = cifs[name], f"CIF:{CIF_DIR / (name + '.cif')}"
            print(f"  [STRUCT] {name}: from CIF")
        elif (hit := db_structure(name, dbs)):
            phase.structure, phase.structure_source = hit, f"AERIS dataset:{hit.get('database')}"
            print(f"  [STRUCT] {name}: from dataset ({hit.get('database')})")
        else:
            print(f"  [STRUCT] {name}: missing")


def build_geometries(phases: Dict[str, Phase]) -> Dict[str, Geometry]:
    print("\nPhase 0c: Generating QE geometry data...")
    geoms: Dict[str, Geometry] = {}
    for name, phase in phases.items():
        g = geometry_for(phase)
        if not g:
            print(f"  [QE-GEOM] {name}: missing cell/position data")
            continue
        geoms[name] = g
        if phase.structure_source == "missing" and g.source.startswith("generated:"):
            phase.structure_source = g.source
            phase.structure = {"nsites": len(g.atomic_positions), "cell_parameters_angstrom": g.cell_parameters}
            phase.notes = g.notes or phase.notes
        print(f"  [QE-GEOM] {name}: cell + {len(g.atomic_positions)} atomic positions" if g.atomic_positions else f"  [QE-GEOM] {name}: cell only")
    return geoms


def qe_outputs(root: Path, phase: str) -> List[Path]:
    d = root / phase
    paths = [d / "scf.out", d / "relax.out", d / "vc-relax.out", d / f"{phase}.out"]
    return list(dict.fromkeys(paths + (sorted(d.glob("*.out")) if d.is_dir() else [])))


def read_qe_energy(path: Path) -> Optional[Tuple[float, float]]:
    if not path.exists():
        return None
    m = re.findall(r"!\s+total energy\s+=\s+([-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s+Ry", path.read_text(errors="replace"))
    if not m:
        return None
    ry = float(m[-1])
    return ry, ry * RY_TO_EV


def manual_energies(path: Optional[Path]) -> Dict[str, Energy]:
    if not path or not path.exists():
        return {}
    out = {}
    for phase, x in json.loads(path.read_text()).items():
        n = float(x["n_atoms_cell"])
        ry = x.get("total_energy_ry")
        ev = float(x["total_energy_ev"]) if "total_energy_ev" in x else float(ry) * RY_TO_EV
        out[phase] = Energy(phase, ev, n, x.get("source", f"manual:{path}"), float(ry) if ry is not None else None)
    return out


def collect_energies(phases: Dict[str, Phase], geoms: Dict[str, Geometry], root: Path, manual: Optional[Path]) -> Dict[str, Energy]:
    energies = manual_energies(manual)
    print("\nPhase 1: Collecting total energies...")
    for name, phase in phases.items():
        if name in energies:
            print(f"  [ENERGY] {name}: manual {energies[name].total_energy_ev:+.6f} eV")
            continue
        found = [(p, e) for p in qe_outputs(root, name) if (e := read_qe_energy(p))]
        if not found:
            print(f"  [ENERGY] {name}: missing")
            continue
        path, (ry, ev) = found[-1]
        n = len(geoms[name].atomic_positions) if name in geoms and geoms[name].atomic_positions else phase.n_atoms_formula
        energies[name] = Energy(name, ev, float(n), str(path), ry)
        print(f"  [ENERGY] {name}: {ev:+.6f} eV from {path}")
    return energies


def formation_energy(formula: str, energies: Dict[str, Energy]) -> Dict[str, Any]:
    ce = energies[formula]
    comp = parse_formula(formula)
    fu = ce.n_atoms_cell / sum(comp.values())
    refs, ref_ev = {}, 0.0
    for el, n in comp.items():
        r = ref_phase(el)
        mu = energies[r].ev_per_atom
        atoms = n * fu
        ref_ev += atoms * mu
        refs[el] = {"reference_phase": r, "mu_ev_per_atom": mu, "atoms_in_compound_cell": atoms, "source": energies[r].source}
    return {
        "formula": formula,
        "total_energy_ev": ce.total_energy_ev,
        "n_atoms_cell": ce.n_atoms_cell,
        "reference_energy_ev": ref_ev,
        "formation_energy_ev_per_cell": ce.total_energy_ev - ref_ev,
        "formation_energy_ev_per_atom": (ce.total_energy_ev - ref_ev) / ce.n_atoms_cell,
        "references": refs,
    }


def write_artifacts(outdir: Path, geoms: Dict[str, Geometry], qe: QE, submit: Submit) -> None:
    for phase, g in sorted(geoms.items()):
        d = outdir / "qe_geometry" / phase
        d.mkdir(parents=True, exist_ok=True)
        (d / "geometry.json").write_text(json.dumps(asdict(g), indent=2))
        (d / "geometry.in").write_text(geometry_block(g))
        (d / "vc-relax.in").write_text(qe_input(phase, g, qe))
        script = d / "submit.sh"
        script.write_text(submit_script(phase, qe, submit))
        script.chmod(0o755)


def write_outputs(outdir: Path, phases: Dict[str, Phase], geoms: Dict[str, Geometry], qe: QE,
                  submit: Submit,
                  energies: Dict[str, Energy], results: Dict[str, Dict[str, Any]], missing: Dict[str, List[str]],
                  runtime: float) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    write_artifacts(outdir, geoms, qe, submit)
    manifest = {
        "runtime_sec": runtime,
        "phase_records": {k: asdict(v) for k, v in phases.items()},
        "qe_geometries": {k: asdict(v) for k, v in geoms.items()},
        "qe_input_settings": asdict(qe),
        "submit_settings": asdict(submit),
        "energies": {k: asdict(v) for k, v in energies.items()},
        "formation_results": results,
        "missing": missing,
    }
    (outdir / "formation_energy_results.json").write_text(json.dumps(manifest, indent=2))

    lines = [
        "# Formation Energy DFT Scaffold Report\n",
        "No RF or NN model predictions are used in this workflow.\n",
        "## Formation Reactions\n",
        "| Formula | Formation reaction | Formation energy formula |",
        "|---|---|---|",
    ]
    for f in sorted(k for k, v in phases.items() if v.role == "compound"):
        lines.append(f"| {f} | `{cell_reaction(f, phases, geoms)}` | `{cell_formula_expr(f, phases, geoms)}` |")
    lines += [
        "\n## Phase Inventory\n",
        "| Phase | Role | Formula | Structure source | nsites | Space group | QE geometry |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for name, p in sorted(phases.items()):
        s = p.structure or {}
        g = geoms.get(name)
        status = "missing" if not g else ("cell + positions" if g.atomic_positions else "cell only")
        lines.append(f"| {name} | {p.role} | {p.formula} | {p.structure_source} | {s.get('nsites', '')} | {s.get('spacegroup_number', '')} | {status} |")
    lines += [
        "\n## QE Input Artifacts\n",
        "| Phase | QE input | Submit script | Geometry block | Structured JSON | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for phase, g in sorted(geoms.items()):
        lines.append(f"| {phase} | `qe_geometry/{phase}/vc-relax.in` | `qe_geometry/{phase}/submit.sh` | `qe_geometry/{phase}/geometry.in` | `qe_geometry/{phase}/geometry.json` | {g.notes or ''} |")
    lines += [
        "\n## QE Run Files\n",
        "Run each job from its phase directory so the submit script can find `vc-relax.in`.\n",
        "| Phase | Input file | Submit script | Submit command |",
        "|---|---|---|---|",
    ]
    for phase in sorted(geoms):
        lines.append(
            f"| {phase} | `qe_geometry/{phase}/vc-relax.in` | "
            f"`qe_geometry/{phase}/submit.sh` | `cd qe_geometry/{phase} && sbatch submit.sh` |"
        )
    lines += [
        "\n## Total Energies\n",
        "| Phase | Total energy (eV) | eV/atom | n atoms | Source |",
        "|---|---:|---:|---:|---|",
    ]
    for phase, e in sorted(energies.items()):
        lines.append(f"| {phase} | {e.total_energy_ev:+.8f} | {e.ev_per_atom:+.8f} | {e.n_atoms_cell:g} | {e.source} |")
    lines += ["\n## Formation Energies\n"]
    if results:
        lines += ["| Formula | E_total cell (eV) | E_refs cell (eV) | E_form cell (eV) | E_form (eV/atom) |", "|---|---:|---:|---:|---:|"]
        for f, r in sorted(results.items()):
            lines.append(f"| {f} | {r['total_energy_ev']:+.8f} | {r['reference_energy_ev']:+.8f} | {r['formation_energy_ev_per_cell']:+.8f} | {r['formation_energy_ev_per_atom']:+.8f} |")
    else:
        lines.append("No formation energies were computed because required QE total energies are missing.")
    lines += ["\n## Missing Inputs\n"]
    any_missing = False
    for f, items in sorted(missing.items()):
        if items:
            any_missing = True
            lines.append(f"- {f}: {', '.join(items)}")
    if not any_missing:
        lines.append("- None")
    lines += [
        "\n## Notes\n",
        "- Confirm elemental reference phases before using values scientifically.",
        "- QE calculations must use consistent pseudopotentials, functionals, cutoffs, k-points, smearing, and spin settings.",
        "- Negative formation energy means stable relative to selected elemental references, not necessarily stable on the convex hull.",
        "",
    ]
    (outdir / "formation_energy_report.md").write_text("\n".join(lines))
    print(f"\nWrote JSON:   {outdir / 'formation_energy_results.json'}")
    print(f"Wrote report: {outdir / 'formation_energy_report.md'}")


def run(args: argparse.Namespace) -> None:
    t0 = time.time()
    formulas = [x.strip() for x in args.formulas.split(",") if x.strip()]
    qe = QE(pseudo_dir=args.pseudo_dir, calculation=args.calculation, ecutwfc=args.ecutwfc,
            ecutrho=args.ecutrho, k_points=args.k_points)
    submit = Submit(account=args.slurm_account, nodes=args.slurm_nodes, walltime=args.slurm_time,
                    ntasks=args.slurm_tasks, cpus_per_task=args.slurm_cpus_per_task,
                    gpus_per_task=args.slurm_gpus_per_task)
    print("=" * 72)
    print("Formation-energy DFT scaffold")
    print("  Backend: Quantum ESPRESSO total-energy bookkeeping")
    print("  Models:  none")
    print(f"  Targets: {', '.join(formulas)}")
    print("=" * 72)

    phases = build_phases(formulas)
    attach_structures(phases)
    geoms = build_geometries(phases)

    print("\nFormation reactions using computed QE cells:")
    for f in formulas:
        print(f"  {f}: {cell_reaction(f, phases, geoms)}")
        print(f"    {cell_formula_expr(f, phases, geoms)}")

    energies = collect_energies(phases, geoms, Path(args.qe_root), args.energy_json)
    print("\nPhase 2: Computing formation energies...")
    results, missing = {}, {}
    for f in formulas:
        miss = []
        if f not in energies:
            miss.append(f"compound total energy for {f}")
        for el in parse_formula(f):
            r = ref_phase(el)
            if r not in energies:
                miss.append(f"reference total energy for {el} ({r})")
        missing[f] = miss
        if miss:
            print(f"  [FORM] {f}: missing {', '.join(miss)}")
        else:
            results[f] = formation_energy(f, energies)
            print(f"  [FORM] {f}: {results[f]['formation_energy_ev_per_atom']:+.8f} eV/atom")

    runtime = time.time() - t0
    write_outputs(Path(args.output_dir), phases, geoms, qe, submit, energies, results, missing, runtime)
    print("\nExecution summary")
    print(f"  Phases tracked:     {len(phases)}")
    print(f"  QE geometries:      {len(geoms)}")
    print(f"  Energies available: {len(energies)}")
    print(f"  Formation results:  {len(results)}")
    print(f"  Runtime:            {runtime:.2f} s")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate QE inputs and compute DFT formation energies from QE outputs.")
    p.add_argument("--formulas", default="UN", help="Comma-separated target formulas, e.g. UN,UO2,ZrO2")
    p.add_argument("--qe-root", default=str(DEFAULT_QE_ROOT), help="Root containing per-phase QE outputs.")
    p.add_argument("--energy-json", type=Path, default=None, help="Optional manual total-energy JSON.")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory.")
    p.add_argument("--pseudo-dir", default=DEFAULT_PSEUDO_DIR, help="QE pseudopotential directory.")
    p.add_argument("--calculation", default="vc-relax", choices=["scf", "relax", "vc-relax"])
    p.add_argument("--ecutwfc", type=float, default=30.0)
    p.add_argument("--ecutrho", type=float, default=120.0)
    p.add_argument("--k-points", default="gamma", help="'gamma' or automatic grid string, e.g. '6 6 6 0 0 0'.")
    p.add_argument("--slurm-account", default="stf243")
    p.add_argument("--slurm-nodes", type=int, default=1)
    p.add_argument("--slurm-time", default="1:00:00")
    p.add_argument("--slurm-tasks", type=int, default=8)
    p.add_argument("--slurm-cpus-per-task", type=int, default=7)
    p.add_argument("--slurm-gpus-per-task", type=int, default=1)
    return p


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run(parser().parse_args())
