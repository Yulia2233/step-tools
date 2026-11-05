from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: mixed-rail-angle-guide (build, profile=geometry) ----
    profile_wire = scad.make_polyline_rwire(points=[(0, -8, -6), (0, 8, -6), (0, 8, -2), (0, -4, -2), (0, -4, 10), (0, -8, 10)], closed=True)
    profile = scad.make_face_from_wire_rface(wire=profile_wire, normal=(1, 0, 0))
    straight = scad.make_line_redge(start=(0, 0, 0), end=(28, 0, 0))
    curved = scad.make_spline_redge(control_points=[(28, 0, 0), (50, 0, 0), (68, 28, 0), (94, 28, 0)], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[straight, curved])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: integral-mounting-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=9.0, height=14.0, bottom_face_center=(14, 0, -7), axis=(0, 0, 1))
    result = scad.union_rsolid(result, boss)

    # ---- feature: blind-mounting-hole (subtract, profile=geometry) ----
    hole = scad.make_cylinder_rsolid(radius=3.0, height=8.0, bottom_face_center=(14, 0, 0), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, hole, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Curved angle guide with blind mounting boss')

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
