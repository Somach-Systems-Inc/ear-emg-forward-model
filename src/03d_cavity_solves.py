"""Articulatory volume-conductor exposure vs distance to the oral cavity.

*** THE VERDICT THIS SCRIPT PRINTS IS SUPERSEDED. DO NOT QUOTE IT. ***

This script SOLVES. Read the verdict from `src/03c_cavity_analysis.py`, which
supersedes everything below the solve loop for three reasons:

  1. it decomposes the common-mode shift from the per-electrode residual, and
     criterion (b) is about the residual. Filling the oral cavity and
     nasopharynx lowers total head conductance and moves EVERY electrode,
     including ear sites 76 mm away, so a raw-shift test can pass while the
     hypothesis under test fails.
  2. the 0.43 dB floor hardcoded below is superseded twice over. It is now
     0.272 dB (10 mm, n=6, per-site, common mode removed) and is READ FROM
     `results/electrode_meshing_floor.txt` by 03c rather than hardcoded.
  3. 03c reads each solve's calibration line and recomputes the verdict with
     and without any warned solve. This script reads no calibration output.

The printed block below is left intact rather than deleted so that the
superseded numbers stay auditable, but it must not be quoted.


NOT a jaw-vs-ear test. That is a categorical claim of the same shape as the one
that killed Fig 7 -- it assumes the grouping it should be measuring. Electrodes
are chosen to SPAN electrode-to-cavity distance (14.5 to 75.5 mm), not to
represent two categories, and exposure is regressed on distance.

RE-REGISTERED CRITERION, fixed before any number is seen. BOTH must hold:
  (a) Spearman rho(distance, |dB change|) is NEGATIVE
  (b) max |dB change| across the montage EXCEEDS 0.43 dB
Failing either = FALSIFIED. A correlation entirely beneath the noise floor is
not a result.

Per-electrode statistic: MEDIAN |dB change| across the 10 segmented muscle
compartments (robust). The 0.43 dB test uses the montage-wide MAX.

UPPER-BOUND FRAMING: MIDA is static. Filling the cavity with muscle is the
EXTREME configuration, so this bounds articulatory volume-conductor variation
from above. It is not a simulation of speech; real variation lies inside the
filled/air envelope.
"""
import sys, csv, numpy as np
from pathlib import Path
from scipy.stats import spearmanr
from scipy.spatial import cKDTree
import nibabel as nib
ROOT=Path("/Users/carl/CODELocalProjects/ear-emg-forward-model")
sys.path.insert(0,str(ROOT/"src")); import config, solve_invariants as SI
from simnibs import sim_struct, run_simnibs, mesh_io

CAVITY={31:"Air Internal - Nasal/Pharynx", 97:"Air Internal - Oral Cavity"}
# span distance, not categories. buccal required (oral vestibule wall);
# three ear sites at the far end.
ELECS=["hyoid","buccal","submental_lat","midjaw","cg10","pre_tragus",
       "mastoid","above_ear"]
REF="earlobe_contra"

rows=list(csv.DictReader((ROOT/"results/01_table1_conductivities.csv").open()))
base={int(r["mida_label"]):float(r["sigma_S_per_m"]) for r in rows}
missing=[l for l in CAVITY if l not in base]
assert not missing, f"cavity labels absent from Table 1: {missing}"
filled=dict(base)
for l in CAVITY: filled[l]=config.SIGMA["muscle_iso"]

pos={r["name"]:np.array([float(r["R"]),float(r["A"]),float(r["S"])])
     for r in csv.DictReader((ROOT/"results/02_electrode_positions.csv").open())
     if r.get("verified")!="held" and r["R"]!=""}
img=nib.load(str(ROOT/"data/MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii"))
arr=np.asanyarray(img.dataobj); aff=img.affine
# cast to float64 explicitly: the int argwhere @ float affine tripped
# divide-by-zero/overflow warnings under the SimNIBS interpreter
cav=np.vstack([np.argwhere(arr==l).astype(np.float64)@aff[:3,:3].T.astype(np.float64)
               +aff[:3,3].astype(np.float64) for l in CAVITY])
ctree=cKDTree(cav)
DIST={e:float(ctree.query(pos[e])[0]) for e in ELECS}

def solve(sig,e,tag):
    import preflight
    preflight.check_conductivity_range(sig.values(), label=f"{tag}__{e}")
    out=ROOT/f"results/cavity/{tag}__{e}"; out.parent.mkdir(parents=True,exist_ok=True)
    S=sim_struct.SESSION(); S.fnamehead=str(ROOT/"data/mida_headneck.msh")
    S.pathfem=str(out); S.fields="E"; S.open_in_gmsh=False; S.map_to_surf=False
    t=S.add_tdcslist(); t.currents=[1e-3,-1e-3]
    for lab,v in sig.items(): t.cond[lab-1].value=v; t.cond[lab-1].name=f"tag{lab}"
    for j,nm in enumerate((e,REF)):
        el=t.add_electrode(); el.channelnr=j+1; el.centre=list(pos[nm])
        el.shape="ellipse"; el.dimensions=[10,10]; el.thickness=2
    run_simnibs(S)
    # Record the solver's own calibration line. RECORDED ONLY -- it gates
    # nothing, and the 11-15% "benign band" that cg10's 11.90% was once waved
    # through on is RETIRED (the check is anti-correlated with true delivered
    # current: Spearman -0.425, p = 0.048, n = 22). Delivered current is the
    # tet-patch integral from check_solve_plateau, below.
    import preflight
    cal=preflight.read_calibration(out)
    if cal is not None:
        print(f"  {tag:<7} @ {e:<14} CALIBRATION WARNED {cal:.2f}%", flush=True)
    r=sorted(out.glob("*_scalar.msh"))[0]
    inv=SI.check_solve_plateau(r,pos[e],SI.with_electrode_tags(sig),verbose=False)
    st=f"plateau {inv['plateau']['radii'][0]:.0f}-{inv['plateau']['radii'][-1]:.0f}mm"
    m=mesh_io.read_msh(str(r)); E=np.asarray(m.field["E"].value)
    tets=m.elm.elm_type==4; tags=m.elm.tag1[tets]
    vols=m.elements_volumes_and_areas()[tets]; mag=np.linalg.norm(E[tets],axis=1)
    res={}
    for name,_,lab,_ in config.MUSCLES:
        if lab is None: continue
        k=tags==lab
        if not k.any(): continue
        v,w=mag[k],vols[k]; o=np.argsort(v); c=np.cumsum(w[o])
        res[name]=float(v[o][np.searchsorted(c,0.5*c[-1])])
    print(f"  {tag:<7} @ {e:<14} inv1 mean {inv['mean_ratio']:.4f} "
          f"CV {inv['cv']*100:4.2f}% [{st}]", flush=True)
    return res

R={}
for tag,sig in (("air",base),("filled",filled)):
    for e in ELECS: R[(tag,e)]=solve(sig,e,tag)

print(f"\n{'electrode':<16}{'dist mm':>9}{'median|dB|':>12}{'max|dB|':>10}")
print("-"*50)
D,Y,MX=[],[],[]
for e in sorted(ELECS,key=lambda x:DIST[x]):
    v=[abs(20*np.log10(R[("filled",e)][n]/R[("air",e)][n]))
       for n in R[("air",e)]]
    D.append(DIST[e]); Y.append(float(np.median(v))); MX.append(max(v))
    print(f"{e:<16}{DIST[e]:>9.1f}{np.median(v):>12.3f}{max(v):>10.3f}")
rho,p=spearmanr(D,Y)
mx=max(MX)
print(f"\nSpearman rho(distance, median|dB|) = {rho:+.3f}   p = {p:.3f}")
print(f"montage-wide max |dB|              = {mx:.3f}   (floor ~0.43 dB)")
a=rho<0; b=mx>0.43
print(f"\n  (a) rho negative              : {a}")
print(f"  (b) max |dB| exceeds 0.43 dB  : {b}")
print("\n  VERDICT:", "SURVIVES" if (a and b) else "FALSIFIED")
if not (a and b):
    print("  Sites over the oral cavity are NOT measurably more exposed to")
    print("  articulatory volume-conductor change than distant sites.")
