from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: four-station-sensor-pedestal (build, profile=geometry) ----
    base_a = scad.make_line_redge(start=(-18, -12, 0), end=(18, -12, 0))
    base_b = scad.make_line_redge(start=(18, -12, 0), end=(18, 12, 0))
    base_c = scad.make_line_redge(start=(18, 12, 0), end=(-18, 12, 0))
    base_d = scad.make_line_redge(start=(-18, 12, 0), end=(-18, -12, 0))
    base = scad.make_wire_from_edges_rwire(edges=[base_a, base_b, base_c, base_d])
    shoulder_a = scad.make_line_redge(start=(-14, -12, 24), end=(20, -10, 24))
    shoulder_b = scad.make_line_redge(start=(20, -10, 24), end=(16, 14, 24))
    shoulder_c = scad.make_line_redge(start=(16, 14, 24), end=(-10, 14, 24))
    shoulder_d = scad.make_line_redge(start=(-10, 14, 24), end=(-14, -12, 24))
    shoulder = scad.make_wire_from_edges_rwire(edges=[shoulder_a, shoulder_b, shoulder_c, shoulder_d])
    neck_a = scad.make_line_redge(start=(-8, -10, 50), end=(16, -8, 50))
    neck_b = scad.make_line_redge(start=(16, -8, 50), end=(14, 13, 50))
    neck_c = scad.make_line_redge(start=(14, 13, 50), end=(-6, 16, 50))
    neck_d = scad.make_line_redge(start=(-6, 16, 50), end=(-8, -10, 50))
    neck = scad.make_wire_from_edges_rwire(edges=[neck_a, neck_b, neck_c, neck_d])
    tip_a = scad.make_line_redge(start=(-6, -13, 74), end=(16, -5, 74))
    tip_b = scad.make_line_redge(start=(16, -5, 74), end=(10, 16, 74))
    tip_c = scad.make_line_redge(start=(10, 16, 74), end=(-9, 9, 74))
    tip_d = scad.make_line_redge(start=(-9, 9, 74), end=(-6, -13, 74))
    tip = scad.make_wire_from_edges_rwire(edges=[tip_a, tip_b, tip_c, tip_d])
    result = scad.loft_rsolid(profiles=[base, shoulder, neck, tip], ruled=False)

    # ---- feature: rectangular-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=64, height=40, depth=6, bottom_face_center=(0, 0, -4))
    result = scad.union_rsolid(result, flange)

    # ---- feature: two-through-bolt-holes (subtract, profile=geometry) ----
    bolt_left = scad.make_cylinder_rsolid(radius=3.2, height=10, bottom_face_center=(-25, 0, -6), axis=(0, 0, 1))
    bolt_right = scad.make_cylinder_rsolid(radius=3.2, height=10, bottom_face_center=(25, 0, -6), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_left, bolt_right, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Offset lofted sensor pedestal')

if __name__ == "__main__":
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from simplecadapi.exporter.step import export_product_package_to_step
    with TemporaryDirectory(prefix="tail-solid-export-") as scratch:
        product = build()
        package = Path(scratch) / "product.scadpkg"
        scad.capture(product, package, include_scene=False)
        export_product_package_to_step(data=package,
            output_path=Path(__file__).with_suffix(".step"))
