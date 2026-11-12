from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import simplecadapi as scad

from cli import inspect_step, prepare_project
from sdk_adapter import centered, load_solids, metrics, same_geometry


STEPIR_SCRIPT = Path(os.environ["MULTISOLID_STEPIR_SCRIPT"]) if os.environ.get("MULTISOLID_STEPIR_SCRIPT") else None
PYTHON = Path(os.environ.get("MULTISOLID_PYTHON", sys.executable))


class MultiSolidPreprocessTests(unittest.TestCase):
    def test_split_translation_dedup_and_v63_ir(self) -> None:
        if STEPIR_SCRIPT is None:
            self.fail("Set MULTISOLID_STEPIR_SCRIPT to the frozen STEPIR v6.3 bundled script")
        with tempfile.TemporaryDirectory(prefix="multisolid-test-") as tmp:
            temp = Path(tmp)
            main = scad.make_box_rsolid(width=10.0, height=8.0, depth=4.0)
            spur = scad.translate_shape(
                scad.make_box_rsolid(width=3.0, height=2.0, depth=4.0),
                (6.0, 2.0, 0.0),
            )
            base = scad.union_rsolid(main, spur)
            repeated = scad.translate_shape(base, (25.0, -3.0, 2.0))
            base_metrics = metrics(base)
            x, y, _ = base_metrics["vertex_mean_mm"]
            rotated = scad.transform_rsolid(
                base,
                [
                    [0.0, -1.0, 0.0, x + y],
                    [1.0, 0.0, 0.0, y - x],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
            )
            different = scad.translate_shape(
                scad.make_box_rsolid(width=3.0, height=4.0, depth=5.0),
                (-12.0, 0.0, 0.0),
            )
            sphere = scad.make_sphere_rsolid(radius=2.0)
            repeated_sphere = scad.translate_shape(sphere, (30.0, 0.0, 0.0))
            source = temp / "source.step"
            scad._cpp._native.export_step([base, repeated, rotated, different, sphere, repeated_sphere], str(source))

            inspected = inspect_step(source)
            self.assertEqual(inspected["solid_count"], 6)

            output = temp / "prepared"
            result = prepare_project(source, output, python=PYTHON, stepir_script=STEPIR_SCRIPT)
            self.assertEqual(result["solid_count"], 6)
            self.assertEqual(result["unique_part_count"], 3)

            assembly = json.loads((output / "assembly.ir.json").read_text())
            self.assertEqual(assembly["source"]["solid_occurrences"], 6)
            self.assertEqual(len(assembly["unique_parts"]), 3)
            self.assertEqual(assembly["instances"][0]["part_id"], assembly["instances"][1]["part_id"])
            self.assertEqual(assembly["instances"][2]["part_id"], assembly["instances"][0]["part_id"])
            self.assertEqual(assembly["instances"][3]["part_id"], "part-001")
            self.assertEqual(assembly["instances"][4]["part_id"], assembly["instances"][5]["part_id"])
            self.assertEqual(assembly["instances"][4]["alignment_mode"], "translation_only")
            self.assertEqual(assembly["instances"][5]["alignment_mode"], "translation_only")
            self.assertAlmostEqual(assembly["instances"][1]["placement"]["origin"][0], 25.0, places=6)
            self.assertAlmostEqual(assembly["instances"][1]["placement"]["origin"][1], -3.0, places=6)
            self.assertAlmostEqual(assembly["instances"][1]["placement"]["origin"][2], 2.0, places=6)
            self.assertAlmostEqual(assembly["instances"][5]["placement"]["origin"][0], 30.0, places=6)

            source_shapes = load_solids(source)
            rotated_transform = assembly["instances"][2]["transform_from_representative"]
            rebuilt_rotated = scad.transform_rsolid(source_shapes[0], rotated_transform)
            moved_center = tuple(metrics(rebuilt_rotated)["vertex_mean_mm"])
            target_center = tuple(metrics(source_shapes[2])["vertex_mean_mm"])
            self.assertTrue(
                same_geometry(centered(rebuilt_rotated, moved_center), centered(source_shapes[2], target_center))[0]
            )

            for part in assembly["unique_parts"]:
                target = output / part["target_step"]
                ir = output / part["stepir"]
                self.assertEqual(len(load_solids(target)), 1)
                self.assertEqual((target.parent / "ir_version.txt").read_text().strip(), "v6.3")
                header = json.loads(ir.read_text().splitlines()[0])
                self.assertEqual(header["solids"], 1)
                self.assertGreater(header["vol"], 0)


if __name__ == "__main__":
    unittest.main()
