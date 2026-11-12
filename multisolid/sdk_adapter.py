"""Version-pinned SimpleCADAPI adapter for STEP solid extraction."""

from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path
from typing import Any


SUPPORTED_SDK_VERSION = "2.2.7"


def _sdk():
    try:
        version = importlib.metadata.version("simplecadapi")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("simplecadapi==2.2.7 is required") from exc
    if version != SUPPORTED_SDK_VERSION:
        raise RuntimeError(f"simplecadapi=={SUPPORTED_SDK_VERSION} is required; found {version}")

    import simplecadapi as scad

    return scad


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_solids(step_path: Path) -> list[Any]:
    """Read STEP through SimpleCADAPI and enumerate solids with its QL selector."""
    scad = _sdk()
    native = scad._cpp._native
    try:
        shape = native.import_step(str(step_path), require_valid=True)
        solids = scad.ql.solids().resolve(shape)
    except Exception as exc:
        raise RuntimeError(f"SimpleCADAPI could not read STEP: {exc}") from exc
    if not solids:
        raise RuntimeError("STEP contains no solids")
    return solids


def metrics(solid: Any) -> dict[str, Any]:
    scad = _sdk()
    import numpy as np

    # _bounds is the SDK 2.2.7 native geometry adapter; keep this use isolated here.
    bounds = tuple(float(v) for v in solid._bounds())
    vertices = scad.ql.vertices().resolve(solid)
    points = np.asarray([vertex.get_center().to_tuple() for vertex in vertices], dtype=float)
    if len(points) >= 4:
        center = points.mean(axis=0)
        centered_points = points - center
        covariance = centered_points.T @ centered_points
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[order]
        eigenvectors = eigenvectors[:, order]
        scale = max(1.0, float(eigenvalues[0]))
        gaps = [float(abs(eigenvalues[i] - eigenvalues[i + 1]) / scale) for i in range(2)]

        # Fix two PCA-axis signs by their third moments, then derive the last axis
        # with a cross product so the canonical frame is always right-handed.
        sign_ambiguous = False
        for axis in (0, 1):
            projections = centered_points @ eigenvectors[:, axis]
            third_moment = float(np.sum(projections ** 3))
            moment_scale = max(1.0, float(np.sum(np.abs(projections) ** 3)))
            if abs(third_moment) <= 1e-10 * moment_scale:
                sign_ambiguous = True
            elif third_moment < 0:
                eigenvectors[:, axis] *= -1
        eigenvectors[:, 2] = np.cross(eigenvectors[:, 0], eigenvectors[:, 1])
        eigenvectors[:, 2] /= np.linalg.norm(eigenvectors[:, 2])
        rotation_to_principal = eigenvectors.T
        translation_to_principal = -(rotation_to_principal @ center)
        principal_axes_resolved = min(gaps) > 1e-7 and not sign_ambiguous
        anchor_kind = "vertex_mean"
        eigenvalues_out = [float(v) for v in eigenvalues]
    else:
        # Analytic balls and other low-vertex solids have no usable PCA frame.
        center = np.asarray([(bounds[i] + bounds[i + 3]) / 2 for i in range(3)], dtype=float)
        bbox_size = np.asarray([bounds[i + 3] - bounds[i] for i in range(3)], dtype=float)
        rotation_to_principal = np.eye(3)
        translation_to_principal = -center
        principal_axes_resolved = False
        anchor_kind = "bbox_center_fallback"
        eigenvalues_out = sorted((bbox_size ** 2).tolist(), reverse=True)
        gaps = []

    faces = len(scad.ql.faces().resolve(solid))
    edges = len(scad.ql.edges().resolve(solid))
    bbox_center = [(bounds[i] + bounds[i + 3]) / 2 for i in range(3)]
    return {
        "vertex_mean_mm": [float(v) for v in center],
        "placement_anchor": anchor_kind,
        "bbox_center_mm": bbox_center,
        "bbox_mm": {"min": list(bounds[:3]), "max": list(bounds[3:])},
        "bbox_size_mm": [bounds[i + 3] - bounds[i] for i in range(3)],
        "face_count": faces,
        "edge_count": edges,
        "vertex_count": len(vertices),
        "principal_moments_mm2": eigenvalues_out,
        "principal_axes_resolved": principal_axes_resolved,
        "principal_axis_relative_gaps": gaps,
        "source_to_principal_rotation": rotation_to_principal.tolist(),
        "source_to_principal_translation": translation_to_principal.tolist(),
    }


def centered(solid: Any, center: tuple[float, float, float]) -> Any:
    scad = _sdk()
    return scad._cpp._native.translate_shape(solid, tuple(-value for value in center))


def principal_aligned(solid: Any, geometry_metrics: dict[str, Any]) -> Any:
    scad = _sdk()
    rotation = geometry_metrics["source_to_principal_rotation"]
    translation = geometry_metrics["source_to_principal_translation"]
    matrix = [
        [*rotation[0], translation[0]],
        [*rotation[1], translation[1]],
        [*rotation[2], translation[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]
    return scad.transform_rsolid(solid, matrix)


def canonical_hash(solid: Any) -> str:
    scad = _sdk()
    return hashlib.sha256(scad._cpp._native.canonical_brep_bytes(solid)).hexdigest()


def same_geometry(a: Any, b: Any) -> tuple[bool, str]:
    """Confirm centered shape identity with exact BREP bytes or symmetric difference."""
    scad = _sdk()
    if canonical_hash(a) == canonical_hash(b):
        return True, "centered_canonical_brep_sha256"

    try:
        ab = scad.boolean_rsolidlist([a], [b], "cut")
        ba = scad.boolean_rsolidlist([b], [a], "cut")
        if not ab and not ba and a.same_topology(b):
            return True, "centered_symmetric_difference_empty"
    except Exception:
        pass
    return False, "not_proven_identical"


def export_solid(solid: Any, destination: Path) -> None:
    scad = _sdk()
    scad._cpp._native.export_step(solid, str(destination))
