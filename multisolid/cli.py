#!/usr/bin/env python3
"""Inspect and split multi-solid STEP files into v6.3 single-part jobs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from sdk_adapter import (
    SUPPORTED_SDK_VERSION,
    canonical_hash,
    centered,
    export_solid,
    load_solids,
    metrics,
    principal_aligned,
    same_geometry,
    sha256_file,
)


SCHEMA_VERSION = "step-assembly-ir-v1"
PREPROCESS_VERSION = "step-multisolid-preprocess-v1"
IR_VERSION = "v6.3"


def _placement_from_transform(matrix: list[list[float]]) -> dict[str, list[float]]:
    return {
        "origin": [float(matrix[row][3]) for row in range(3)],
        "x_axis": [float(matrix[row][0]) for row in range(3)],
        "y_axis": [float(matrix[row][1]) for row in range(3)],
    }


def _relative_transform(rep: dict[str, Any], current: dict[str, Any]) -> list[list[float]]:
    """Return the source-world transform taking representative points to current points."""
    import numpy as np

    r_rep = np.asarray(rep["source_to_principal_rotation"], dtype=float)
    t_rep = np.asarray(rep["source_to_principal_translation"], dtype=float)
    r_current = np.asarray(current["source_to_principal_rotation"], dtype=float)
    t_current = np.asarray(current["source_to_principal_translation"], dtype=float)
    rotation = r_current.T @ r_rep
    translation = r_current.T @ (t_rep - t_current)
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = translation
    return [[float(value) for value in row] for row in matrix]


def _normalize_for_matching(solid: Any, geometry_metrics: dict[str, Any]) -> tuple[Any, str]:
    if geometry_metrics["principal_axes_resolved"]:
        try:
            return principal_aligned(solid, geometry_metrics), "principal_axes"
        except Exception as exc:
            geometry_metrics["principal_axes_resolved"] = False
            geometry_metrics["principal_axes_failure"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    return centered(solid, tuple(geometry_metrics["vertex_mean_mm"])), "translation_only"


def inspect_step(step_path: Path) -> dict[str, Any]:
    step_path = step_path.resolve(strict=True)
    solids = load_solids(step_path)
    return {
        "schema_version": "step-multisolid-inspect-v1",
        "source": {"path": str(step_path), "sha256": sha256_file(step_path)},
        "solid_count": len(solids),
        "solids": [
            {"source_solid_id": f"solid-{index:03d}", **metrics(solid)}
            for index, solid in enumerate(solids)
        ],
    }


def _coarse_match(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if any(a[key] != b[key] for key in ("face_count", "edge_count", "vertex_count")):
        return False
    ea = a["principal_moments_mm2"]
    eb = b["principal_moments_mm2"]
    scale = max(1.0, *(abs(value) for value in ea), *(abs(value) for value in eb))
    return all(abs(x - y) <= scale * 1e-8 for x, y in zip(ea, eb))


def _run_stepir(
    step_path: Path,
    ir_path: Path,
    *,
    python: Path,
    script: Path,
) -> dict[str, Any]:
    result = subprocess.run(
        [str(python), str(script), str(step_path), "--out", str(ir_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"STEPIR failed for {step_path.name} (exit {result.returncode}): "
            f"{result.stderr[-2000:]}"
        )
    records = [line for line in ir_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise RuntimeError(f"STEPIR produced empty IR for {step_path.name}")
    header = json.loads(records[0])
    if header.get("solids") != 1:
        raise RuntimeError(f"Expected single-solid v6.3 IR for {step_path.name}; header={header}")
    return {"header": header, "sha256": sha256_file(ir_path)}


def prepare_project(
    step_path: Path,
    out_dir: Path,
    *,
    python: Path,
    stepir_script: Path,
) -> dict[str, Any]:
    step_path = step_path.resolve(strict=True)
    out_dir = out_dir.resolve()
    if out_dir.exists():
        raise FileExistsError(f"Output already exists: {out_dir}")
    if not stepir_script.is_file():
        raise FileNotFoundError(f"STEPIR v6.3 script not found: {stepir_script}")
    if not python.is_file():
        raise FileNotFoundError(f"Python interpreter not found: {python}")

    solids = load_solids(step_path)
    source_hash = sha256_file(step_path)
    out_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f".{out_dir.name}.prepare-", dir=out_dir.parent) as raw_tmp:
        work_dir = Path(raw_tmp)
        (work_dir / "source").mkdir()
        (work_dir / "split").mkdir()
        (work_dir / "unique").mkdir()
        copied_source = work_dir / "source" / "source.step"
        shutil.copyfile(step_path, copied_source)

        instance_rows: list[dict[str, Any]] = []
        representative_indices: list[int] = []
        normalized_shapes: dict[int, Any] = {}
        alignment_modes: dict[int, str] = {}
        match_rows: list[dict[str, Any]] = []

        for index, solid in enumerate(solids):
            instance_id = f"instance-{index:03d}"
            source_solid_id = f"solid-{index:03d}"
            row_metrics = metrics(solid)
            normalized, alignment_mode = _normalize_for_matching(solid, row_metrics)

            split_path = work_dir / "split" / f"{instance_id}.step"
            export_solid(solid, split_path)
            split_solids = load_solids(split_path)
            if len(split_solids) != 1:
                raise RuntimeError(f"Split output is not one solid: {split_path.name}")
            split_metrics = metrics(split_solids[0])
            if alignment_mode == "principal_axes":
                normalized_split, split_mode = _normalize_for_matching(split_solids[0], split_metrics)
                if split_mode != alignment_mode:
                    raise RuntimeError(f"Rigid frame classification changed while writing {split_path.name}")
            else:
                normalized_split = centered(split_solids[0], tuple(split_metrics["vertex_mean_mm"]))
            preserved, _ = same_geometry(normalized, normalized_split)
            if not preserved:
                raise RuntimeError(f"Split STEP geometry does not match source solid: {split_path.name}")

            normalized_shapes[index] = normalized
            alignment_modes[index] = alignment_mode
            shape_hash = canonical_hash(normalized)

            match_index = None
            match_method = "unique"
            for candidate in representative_indices:
                if not _coarse_match(row_metrics, instance_rows[candidate]["metrics"]):
                    continue
                if alignment_mode != alignment_modes[candidate]:
                    continue
                identical, method = same_geometry(normalized, normalized_shapes[candidate])
                if identical:
                    match_index = candidate
                    match_method = method
                    break

            if match_index is None:
                representative_indices.append(index)
                unique_id = f"part-{len(representative_indices) - 1:03d}"
                representative = index
            else:
                unique_id = instance_rows[match_index]["part_id"]
                representative = instance_rows[match_index]["representative_index"]

            if alignment_mode == "principal_axes":
                if representative == index:
                    transform = [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ]
                else:
                    transform = _relative_transform(instance_rows[representative]["metrics"], row_metrics)
            else:
                center = row_metrics["vertex_mean_mm"]
                rep_center = instance_rows[representative]["metrics"]["vertex_mean_mm"] if representative != index else center
                origin_delta = [center[axis] - rep_center[axis] for axis in range(3)]
                transform = [
                    [1.0, 0.0, 0.0, origin_delta[0]],
                    [0.0, 1.0, 0.0, origin_delta[1]],
                    [0.0, 0.0, 1.0, origin_delta[2]],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            instance_rows.append({
                "id": instance_id,
                "source_solid_id": source_solid_id,
                "split_step": f"split/{instance_id}.step",
                "split_step_sha256": sha256_file(split_path),
                "part_id": unique_id,
                "representative_index": representative,
                "placement": _placement_from_transform(transform),
                "transform_from_representative": transform,
                "metrics": row_metrics,
                "centered_geometry_sha256": shape_hash,
                "alignment_mode": alignment_mode,
            })
            match_rows.append({
                "instance_id": instance_id,
                "part_id": unique_id,
                "representative_instance": f"instance-{representative:03d}",
                "deduplicated": match_index is not None,
                "method": match_method,
                "alignment_mode": alignment_mode,
                "rotation_candidate_status": (
                    "resolved"
                    if row_metrics["principal_axes_resolved"]
                    else row_metrics.get("principal_axes_failure", "ambiguous_or_degenerate_principal_frame")
                ),
                "nonmatch_reason": (
                    None
                    if match_index is not None or match_method != "unique"
                    else row_metrics.get("principal_axes_failure", "no_strict_geometry_match")
                ),
            })

        unique_parts = []
        for part_index, representative in enumerate(representative_indices):
            unique_id = f"part-{part_index:03d}"
            representative_row = instance_rows[representative]
            part_dir = work_dir / "unique" / unique_id
            part_dir.mkdir(parents=True)
            target_step = part_dir / "target.step"
            shutil.copyfile(work_dir / representative_row["split_step"], target_step)
            ir_path = part_dir / "target.ir.jsonl"
            ir_result = _run_stepir(target_step, ir_path, python=python, script=stepir_script)
            (part_dir / "ir_version.txt").write_text(IR_VERSION + "\n", encoding="ascii")
            reloaded = load_solids(target_step)
            if len(reloaded) != 1:
                raise RuntimeError(f"Unique target is not one solid: {target_step}")
            target_metrics = metrics(reloaded[0])
            if any(
                target_metrics[key] != representative_row["metrics"][key]
                for key in ("face_count", "edge_count", "vertex_count")
            ):
                raise RuntimeError(f"Topology changed while writing {target_step}")
            if representative_row["alignment_mode"] == "principal_axes":
                target_normalized, target_alignment_mode = _normalize_for_matching(reloaded[0], target_metrics)
                if target_alignment_mode != "principal_axes":
                    raise RuntimeError(f"Rigid frame classification changed while writing {target_step}")
            else:
                target_normalized = centered(reloaded[0], tuple(target_metrics["vertex_mean_mm"]))
            preserved, _ = same_geometry(normalized_shapes[representative], target_normalized)
            if not preserved:
                raise RuntimeError(f"Unique STEP geometry does not match its source solid: {target_step}")
            unique_parts.append({
                "id": unique_id,
                "representative_instance": representative_row["id"],
                "source_solid_id": representative_row["source_solid_id"],
                "target_step": f"unique/{unique_id}/target.step",
                "target_step_sha256": sha256_file(target_step),
                "stepir": f"unique/{unique_id}/target.ir.jsonl",
                "stepir_sha256": ir_result["sha256"],
                "stepir_version": IR_VERSION,
                "dedup_method": next(
                    row["method"] for row in match_rows if row["instance_id"] == representative_row["id"]
                ),
                "metrics": representative_row["metrics"],
            })

        split_manifest = {
            "schema_version": "step-multisolid-split-manifest-v1",
            "source": {"step_path": "source/source.step", "sha256": source_hash},
            "hierarchy": {
                "status": "flat_solid_enumeration",
                "source_preserved": False,
                "reason": "SimpleCADAPI 2.2.7 import_step exposes the flattened root shape through QL solid selection; original occurrence paths and labels are not available through this adapter.",
            },
            "solid_count": len(instance_rows),
            "instances": [
                {key: value for key, value in row.items() if key != "representative_index"}
                for row in instance_rows
            ],
        }
        dedup_report = {
            "schema_version": "step-multisolid-dedup-report-v1",
            "input_solid_count": len(instance_rows),
            "unique_part_count": len(unique_parts),
            "deduplicated_count": len(instance_rows) - len(unique_parts),
            "policy": {
                "kind": "conservative_verified_rigid_candidates",
                "match": "principal-axis aligned canonical BREP equality, or empty bidirectional SimpleCADAPI symmetric difference with matching topology",
                "rotation_equivalence": "candidate rotations use distinct vertex-covariance principal axes with deterministic third-moment signs; ambiguous frames fall back to translation-only matching",
                "sdk": f"simplecadapi=={SUPPORTED_SDK_VERSION}",
            },
            "matches": match_rows,
        }

        # Source-world geometry is preserved in every unique target. A repeated occurrence gets
        # the rigid transform from its representative in the original source coordinates.
        unresolved = [
            {
                "instances": [row["id"]],
                "reason": "engineering_mate_not_inferred_by_preprocessor",
                "fallback": "source_placement",
            }
            for row in instance_rows
        ]
        assembly_ir = {
            "schema_version": SCHEMA_VERSION,
            "units": "mm",
            "coordinate_convention": "representative_source_world_to_instance_source_world",
            "source": {
                "step_path": "source/source.step",
                "sha256": source_hash,
                "solid_occurrences": len(instance_rows),
                "unique_parts": len(unique_parts),
            },
            "hierarchy": {
                "status": "flat_solid_enumeration",
                "source_preserved": False,
                "reason": "SimpleCADAPI 2.2.7 import_step exposes the flattened root shape through QL solid selection; original occurrence paths and labels are not available through this adapter.",
            },
            "unique_parts": unique_parts,
            "instances": [
                {key: value for key, value in row.items() if key not in {"representative_index", "metrics", "centered_geometry_sha256", "split_step", "split_step_sha256"}}
                for row in instance_rows
            ],
            "relations": [],
            "suggested_mates": [],
            "unresolved": unresolved,
            "tolerances": {
                "dedup_volume_mm3": "zero symmetric difference required; no metric-only merge",
                "placement_length_mm": 1e-9,
            },
            "provenance": {
                "preprocessor_version": PREPROCESS_VERSION,
                "simplecadapi_version": SUPPORTED_SDK_VERSION,
                "stepir_version": IR_VERSION,
                "source_sha256": source_hash,
            },
        }

        (work_dir / "preprocess").mkdir()
        (work_dir / "preprocess" / "split-manifest.json").write_text(
            json.dumps(split_manifest, indent=2) + "\n", encoding="utf-8"
        )
        (work_dir / "preprocess" / "dedup-report.json").write_text(
            json.dumps(dedup_report, indent=2) + "\n", encoding="utf-8"
        )
        (work_dir / "assembly.ir.json").write_text(
            json.dumps(assembly_ir, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(work_dir, out_dir)

    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(out_dir),
        "solid_count": len(solids),
        "unique_part_count": len(unique_parts),
        "assembly_ir": "assembly.ir.json",
        "split_manifest": "preprocess/split-manifest.json",
        "dedup_report": "preprocess/dedup-report.json",
        "unique_parts": unique_parts,
    }


def _defaults() -> tuple[Path, Path | None]:
    python = Path(os.environ.get("MULTISOLID_PYTHON", sys.executable))
    configured_stepir = os.environ.get("MULTISOLID_STEPIR_SCRIPT")
    return python, Path(configured_stepir) if configured_stepir else None


def main(argv: list[str] | None = None) -> int:
    default_python, default_stepir = _defaults()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_parser = sub.add_parser("inspect", help="inspect solid count and source geometry")
    inspect_parser.add_argument("step", type=Path)
    prepare_parser = sub.add_parser("prepare", help="split solids, conservatively deduplicate, and write v6.3 IR")
    prepare_parser.add_argument("step", type=Path)
    prepare_parser.add_argument("--out", type=Path, required=True)
    prepare_parser.add_argument("--python", type=Path, default=default_python,
                                help="v6.3 subprocess interpreter (default: MULTISOLID_PYTHON or this interpreter)")
    prepare_parser.add_argument("--stepir-script", type=Path, default=default_stepir,
                                help="frozen v6.3 bundled script (default: MULTISOLID_STEPIR_SCRIPT)")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_step(args.step)
        else:
            if args.stepir_script is None:
                raise ValueError("Set --stepir-script or MULTISOLID_STEPIR_SCRIPT to the frozen STEPIR v6.3 bundled script")
            result = prepare_project(
                args.step,
                args.out,
                python=args.python.resolve(),
                stepir_script=args.stepir_script.resolve(),
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
