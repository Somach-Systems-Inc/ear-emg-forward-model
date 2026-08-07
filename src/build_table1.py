#!/usr/bin/env python3
"""
Build Table 1: a conductivity for every one of MIDA's 116 mesh tags.

SOURCES, AND WHY THEY ARE MIXED ON PURPOSE

Primary head tissues keep their **SimNIBS defaults**. They are not converted to
IT'IS, because those values are the head-modelling convention, they are already
baked into results computed with them, and changing them would break
comparability with the literature this paper sits in. IT'IS LF differs
materially for several of them -- grey matter 0.419 vs 0.275, cartilage 0.739
vs 0.170 -- so the choice is consequential and is stated in Methods rather than
buried.

Everything else comes from **IT'IS Tissue Properties Database V4.2, the LF
(low-frequency) sub-database**, DOI 10.13099/VIP21000-04-2, released
2024-06-04, downloaded 2026-08-02. Values are read from the shipped SQLite
database, never transcribed from memory.

FREQUENCY. One frequency is pinned for the whole table: 100 Hz, the logarithmic
centre of the 20-500 Hz sEMG band. The IT'IS LF sub-database quotes
low-frequency conductivities as frequency-independent below ~1 MHz, so 100 Hz
sits inside their stated validity and is not an interpolation. This is
consistent with the quasi-static assumption already declared in Limitations:
at 100 Hz in head-sized geometry, capacitive and inductive terms are negligible.

NO KEYWORD HEURISTICS. Every row below is written out deliberately. `Teeth` is
the standing example of why: a keyword match sends it to compact bone, and
dentine is not compact bone -- IT'IS carries `Tooth` as its own entry.

    python src/build_table1.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

ITIS_CSV = config.DATA / "itis/itis_lf_v4.2_conductivity.csv"
ITIS_SRC = ("IT'IS LF v4.2, DOI 10.13099/VIP21000-04-2, "
            "released 2024-06-04, downloaded 2026-08-02")
SIMNIBS_SRC = "SimNIBS 4.6 default (head-modelling convention)"
FREQ_HZ = 100.0

# (simnibs_key) -- keeps the existing config.SIGMA value, NOT converted
S = "simnibs"
# (itis_tissue, assignment, note) -- looked up from the IT'IS LF database
def L(t):
    return ("itis", t, "lookup", "")
def J(t, why):
    return ("itis", t, "judgement", why)

MAP: dict[int, object] = {
    # ---- primary head tissues: SimNIBS defaults, deliberately not converted
    50:  (S, "air", "lookup", "background, outside the head"),
    51:  (S, "skin", "lookup", ""),
    43:  (S, "fat", "lookup", ""),
    62:  (S, "fat", "lookup", ""),
    40:  (S, "bone_compact", "lookup", ""),
    53:  (S, "bone_compact", "lookup", "skull inner table is cortical bone"),
    54:  (S, "bone_compact", "lookup", "skull outer table is cortical bone"),
    52:  (S, "bone_cancellous", "lookup", "diploe is cancellous bone"),
    32:  (S, "csf", "lookup", ""),
    6:   (S, "csf", "lookup", ""),
    10:  (S, "grey_matter", "lookup", ""),
    12:  (S, "white_matter", "lookup", ""),
    24:  (S, "blood", "lookup", ""),
    25:  (S, "blood", "lookup", ""),
    35:  (S, "cartilage", "lookup", ""),
    39:  (S, "cartilage", "lookup", ""),
    55:  (S, "eye", "lookup", ""), 56: (S, "eye", "lookup", ""),
    57:  (S, "eye", "lookup", ""), 58: (S, "eye", "lookup", ""),
    59:  (S, "eye", "lookup", ""),
    26:  (S, "air", "lookup", ""), 27: (S, "air", "lookup", ""),
    28:  (S, "air", "lookup", ""), 29: (S, "air", "lookup", ""),
    30:  (S, "air", "lookup", ""), 31: (S, "air", "lookup", ""),
    97:  (S, "air", "lookup", ""),
    # every muscle compartment, incl. the pooled ones and the extraocular six
    **{k: (S, "muscle_iso", "lookup", "") for k in
       (38, 42, 60, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76,
        77, 78, 79, 80, 81, 82, 83, 84, 91, 92, 93, 94, 95, 96)},

    # ---- everything else: IT'IS LF v4.2
    1:   L("Dura"),
    3:   L("Pineal Body"),
    5:   L("Hippocampus"),
    11:  L("Midbrain"),
    13:  L("Spinal Cord"),
    14:  L("Pons"),
    15:  L("Medulla Oblongata"),
    19:  L("Hypophysis"),
    21:  L("Hypothalamus"),
    22:  L("Commissura Anterior"),
    23:  L("Commissura Posterior"),
    36:  L("Mandible"),
    37:  L("Mucous Membrane"),
    41:  L("Tooth"),
    49:  L("Intervertebral Disc"),
    61:  L("Tendon\\Ligament"),
    98:  L("Tendon\\Ligament"),
    88:  L("Salivary Gland"),
    89:  L("Salivary Gland"),
    90:  L("Salivary Gland"),
    116: L("Thalamus"),
    **{k: L("Vertebrae") for k in (44, 45, 46, 47, 48)},
    **{k: L("Nerve") for k in range(102, 116)},

    # ---- judgement calls, every one justified
    2:   J("Cerebellum", "IT'IS carries one Cerebellum entry, not split into "
                         "grey and white matter"),
    9:   J("Cerebellum", "same single Cerebellum entry; MIDA splits it, IT'IS "
                         "does not"),
    4:   J("Brain (Grey Matter)", "deep grey nucleus, no IT'IS entry"),
    7:   J("Brain (Grey Matter)", "deep grey nucleus, no IT'IS entry"),
    8:   J("Brain (Grey Matter)", "deep grey nucleus, no IT'IS entry"),
    16:  J("Brain (Grey Matter)", "deep grey nucleus, no IT'IS entry"),
    17:  J("Brain (Grey Matter)", "deep grey nucleus, no IT'IS entry"),
    20:  J("Brain (Grey Matter)", "deep grey nucleus, no IT'IS entry"),
    99:  J("Brain (Grey Matter)", "deep grey nucleus, no IT'IS entry"),
    18:  J("Brain (White Matter)", "myelinated tract"),
    100: J("Brain (White Matter)", "myelinated tract"),
    101: J("Brain (White Matter)", "myelinated decussation"),
    33:  J("Cerebrospinal Fluid", "cochlear perilymph is CSF-like; IT'IS has no "
                                  "inner-ear fluid entry"),
    34:  J("Cerebrospinal Fluid", "semicircular canal endolymph, as above"),
    # NOT IT'IS "Air": that entry is exactly 0 S/m, which makes the FEM system
    # singular. config.SIGMA["air"] (currently 1e-6) exists to avoid that, so
    # air lumens take the SimNIBS value even though the tissue identification
    # itself is a judgement.
    # The two air lumens are NOT the same case, and treating them alike was an
    # error: the collapsed-mucosa argument holds for the tube and not for the
    # canal. The canal is the judgement row closest to an electrode (7.76 mm),
    # so an unphysical upper end there would have inflated the worst-case
    # envelope through the single most influential row.
    #
    # External auditory canal: air-filled in a healthy ear, and it does not
    # collapse. Degenerate range on purpose. The only realistic alternative is
    # partial cerumen occlusion, and there is no sourced cerumen conductivity
    # in IT'IS v4.2, so it is declared unmodelled rather than invented.
    85:  (S, "air", "judgement", "external auditory canal, air-filled and "
                                 "non-collapsing in a healthy ear. Uses 1e-15 "
                                 "rather than IT'IS Air = 0 S/m, which would "
                                 "make the system singular. No range: cerumen "
                                 "occlusion has no sourced conductivity and is "
                                 "not modelled.",
          ("air", "air")),
    # Pharyngotympanic tube: normally collapsed and mucosa-lined, so air and
    # mucous membrane are both real states and the range is physical.
    86:  (S, "air", "judgement", "pharyngotympanic tube, normally collapsed "
                                 "and mucosa-lined, so the range spans an open "
                                 "air lumen to a collapsed mucosal one. 1e-15 "
                                 "for the same singularity reason.",
          ("air", "Mucous Membrane")),
    87:  J("Bone (Cortical)", "IT'IS has no hyoid entry; hyoid is a small "
                              "cortical-shelled bone"),
}


def main() -> int:
    if not ITIS_CSV.exists():
        print(f"ERROR: {ITIS_CSV} missing. Export it from the IT'IS SQLite "
              f"database first.", file=sys.stderr)
        return 1
    # NOT pinned to utf-8, deliberately. Every other read in this repo now is,
    # because every tracked text file is utf-8. This one is not ours: it is an
    # export from the IT'IS SQLite database and its encoding is whatever the
    # exporter chose. Assuming utf-8 would raise on a latin-1 export; assuming
    # the platform default is what corrupted "Skull Diplo-e-umlaut" in the first
    # place. So: try utf-8 strictly, fall back to latin-1, which is total and
    # therefore cannot silently drop a byte. Same strategy as parse_lut().
    _raw = ITIS_CSV.read_bytes()
    for _enc in ("utf-8", "latin-1"):
        try:
            _text = _raw.decode(_enc)
            break
        except UnicodeDecodeError:
            continue
    itis = {r["tissue"]: r for r in csv.DictReader(_text.splitlines())}
    inv = {int(r["label"]): r for r in
           csv.DictReader((config.RESULTS / "01_label_inventory.csv").open(encoding="utf-8"))}

    pos = [np.array([float(r["R"]), float(r["A"]), float(r["S"])])
           for r in csv.DictReader(
               (config.RESULTS / "02_electrode_positions.csv").open(encoding="utf-8"))
           if r.get("verified") != "held" and r["R"] != ""]
    P = np.array(pos)

    import nibabel as nib
    img = nib.load(str(config.DATA / "MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii"))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine
    total_vox = int((arr != 50).sum())

    missing = set(inv) - set(MAP)
    if missing:
        print(f"ERROR: {len(missing)} labels unmapped: {sorted(missing)}",
              file=sys.stderr)
        return 1

    rows = []
    rng = np.random.default_rng(0)
    for lab in sorted(inv):
        entry = MAP[lab]
        kind, key, assign, note = entry[:4]
        explicit_range = entry[4] if len(entry) > 4 else None
        name = inv[lab]["name"]
        vox = int(inv[lab]["voxels"])

        if kind == S:
            sigma = config.SIGMA[key]
            lo = hi = ""
            if explicit_range is not None:
                def _resolve(x):
                    return (config.SIGMA[x] if x in config.SIGMA
                            else float(itis[x]["sigma_S_per_m"]))
                lo, hi = (_resolve(explicit_range[0]),
                          _resolve(explicit_range[1]))
            src = SIMNIBS_SRC
            tissue = key
        else:
            if key not in itis:
                print(f"ERROR: '{key}' not in the IT'IS table (label {lab})",
                      file=sys.stderr)
                return 1
            r = itis[key]
            sigma = float(r["sigma_S_per_m"])
            lo = r["sigma_min"] or ""
            hi = r["sigma_max"] or ""
            src = ITIS_SRC
            tissue = key

        # distance from this compartment to the nearest electrode
        idx = np.argwhere(arr == lab)
        if len(idx) and lab != 50:
            if len(idx) > 40000:
                idx = idx[rng.choice(len(idx), 40000, replace=False)]
            ras = idx @ aff[:3, :3].T + aff[:3, 3]
            d = float(np.min(np.linalg.norm(
                ras[:, None, :] - P[None, :, :], axis=-1)))
        else:
            d = float("nan")

        rows.append(dict(
            mida_label=lab, mida_name=name, assigned_tissue=tissue,
            sigma_S_per_m=sigma, frequency_Hz=FREQ_HZ, source=src,
            assignment=assign, sigma_low=lo, sigma_high=hi,
            volume_fraction=round(vox / total_vox, 6) if lab != 50 else 0.0,
            min_dist_to_electrode_mm=round(d, 2) if np.isfinite(d) else "",
            note=note))

    # sort by volume_fraction * proximity, so the table itself shows that the
    # uncertain rows are the ones that cannot matter
    def influence(r):
        d = r["min_dist_to_electrode_mm"]
        d = float(d) if d != "" else 1e6
        return r["volume_fraction"] / max(d, 1.0) ** 2
    rows.sort(key=influence, reverse=True)

    out = config.RESULTS / "01_table1_conductivities.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n_j = sum(1 for r in rows if r["assignment"] == "judgement")
    n_i = sum(1 for r in rows if r["source"].startswith("IT'IS"))
    print(f"116 tags written to {out}")
    print(f"  SimNIBS defaults (unconverted) : {len(rows)-n_i}")
    print(f"  IT'IS LF v4.2 lookups          : {n_i - n_j}")
    print(f"  judgement calls (flagged)      : {n_j}")
    print(f"  frequency pinned               : {FREQ_HZ:.0f} Hz")

    jr = [r for r in rows if r["assignment"] == "judgement"]
    jv = sum(r["volume_fraction"] for r in jr)
    print(f"\njudgement rows are {100*jv:.2f}% of head tissue volume")
    print(f"{'label':>5} {'name':<32} {'sigma':>8} {'vol%':>7} {'dist mm':>8}")
    print("-" * 70)
    for r in sorted(jr, key=influence, reverse=True):
        print(f"{r['mida_label']:>5} {r['mida_name'][:31]:<32} "
              f"{r['sigma_S_per_m']:>8.4g} {100*r['volume_fraction']:>6.3f}% "
              f"{r['min_dist_to_electrode_mm']:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
