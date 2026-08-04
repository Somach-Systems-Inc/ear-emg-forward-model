#!/usr/bin/env python3
"""Standalone tet-patch flux integral, for simnibs/simnibs discussions/666.

Current crossing OUT of a patch of tetrahedra through its INTERIOR cut, using
the mesh's own faces as the quadrature. No project imports; needs only numpy
and a SimNIBS result mesh.

    from tet_patch_standalone import patch_flux
    from simnibs import mesh_io
    m = mesh_io.read_msh("<solve>_scalar.msh")
    cut, ext, n = patch_flux(m, electrode_centre_xyz, 45.0, sigma_by_tag)

`sigma_by_tag` must cover EVERY tag in the mesh, including SimNIBS's electrode
volumes (rubber 100-499 at 29.4 S/m, saline 500-899 at 1.0 S/m). A missing tag
raises rather than being silently zeroed.

Scan several radii and require a stationary plateau before using the value: a
patch must be large enough to contain the whole injection surface before the
cut flux means anything.
"""
import numpy as np


def patch_flux(m, centre, radius_mm, sigma_by_tag):
    """Current crossing OUT of the tet patch through its INTERIOR cut, in A.

    THE PREMISE THAT HAD TO BE FIXED. SimNIBS injects current as a Dirichlet
    condition on the electrode's EXTERIOR surface, not as a volumetric source.
    A patch around the electrode therefore contains no source at all: current
    enters through the mesh's outer face and leaves through the cut, and the
    NET flux is exactly zero. Measured: +0.968 out through the cut, -0.938 in
    through the exterior, total +0.030.

    So the quantity that equals the injected current is the flux through the
    interior cut ONLY. Boundary faces are split by their multiplicity in the
    FULL mesh: 2 means an interior face (part of the cut), 1 means it lies on
    the mesh exterior (where the current is imposed).

    Enclosure and orientation are exact by construction -- the patch surface
    closes to 1.2e-16 of its own area -- and there is no inside/outside test.

    Returns (cut_flux_A, exterior_flux_A, n_cut_faces).
    """
    centre = np.asarray(centre, dtype=np.float64)
    nodes = m.nodes.node_coord.astype(np.float64)
    tets = m.elm.elm_type == 4
    nl = m.elm.node_number_list[tets][:, :4] - 1
    tags = m.elm.tag1[tets]
    E = np.asarray(m.field["E"].value)
    if E.ndim != 2 or E.shape[1] != 3:
        raise RuntimeError(f"E must be (n,3), got {E.shape}")
    E = E[tets]

    FACES = ((0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 3, 1), (1, 2, 3, 0))
    n_t = len(nl)
    all_faces = np.sort(np.concatenate(
        [nl[:, list(f[:3])] for f in FACES]), axis=1)
    _, inv_all, cnt_all = np.unique(all_faces, axis=0,
                                    return_inverse=True, return_counts=True)

    sel = np.linalg.norm(nodes[nl].mean(axis=1) - centre, axis=1) <= radius_mm
    if not sel.any():
        raise RuntimeError(f"no tetrahedra within {radius_mm} mm of {centre}")
    idx = np.flatnonzero(sel)
    own = np.tile(idx, 4)
    slot = np.concatenate([idx + k * n_t for k in range(4)])
    tri = np.concatenate([nl[sel][:, list(f[:3])] for f in FACES])
    opp = np.concatenate([nl[sel][:, f[3]] for f in FACES])

    _, iv, cv = np.unique(np.sort(tri, axis=1), axis=0,
                          return_inverse=True, return_counts=True)
    bnd = cv[iv] == 1

    a = nodes[tri[bnd][:, 0]]
    b = nodes[tri[bnd][:, 1]]
    c = nodes[tri[bnd][:, 2]]
    nrm = np.cross(b - a, c - a)
    two_area = np.linalg.norm(nrm, axis=1)
    nhat = nrm / np.maximum(two_area, 1e-30)[:, None]
    nhat[np.einsum("ij,ij->i", nhat, nodes[opp[bnd]] - a) > 0] *= -1.0
    area_m2 = 0.5 * two_area * 1e-6

    sig = np.array([sigma_by_tag.get(int(t), np.nan) for t in tags[own[bnd]]])
    if not np.isfinite(sig).all():
        missing = sorted({int(t) for t, s in zip(tags[own[bnd]], sig)
                          if not np.isfinite(s)})
        raise RuntimeError(f"tags on the patch boundary have no conductivity: "
                           f"{missing}")
    Jn = sig * np.einsum("ij,ij->i", E[own[bnd]], nhat) * area_m2
    is_cut = cnt_all[inv_all[slot[bnd]]] == 2
    return (float(Jn[is_cut].sum()), float(Jn[~is_cut].sum()),
            int(is_cut.sum()))
