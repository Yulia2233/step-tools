from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: planar-s-spline-rail (build, path=geometry, profile=geometry) ----
    rail = scad.make_spline_redge(control_points=[[0.0, -12.0, 0.0], [0.0, -8.0, 0.0], [0.0, -4.0, 5.0], [0.0, 4.0, 5.0], [0.0, 8.0, 0.0], [0.0, 12.0, 0.0]], degree=3, knots=[0.0, 1.0, 2.0, 3.0], multiplicities=[4, 1, 1, 4])
    section = scad.make_polyline_rwire(points=[(-3.0, -12.0, 0.0), (-1.5, -12.0, 2.6), (1.5, -12.0, 2.6), (3.0, -12.0, 0.0), (1.5, -12.0, -2.6), (-1.5, -12.0, -2.6)], closed=True)
    section_face = scad.make_face_from_wire_rface(wire=section, normal=(0.0, 1.0, 0.0))
    rail_wire = scad.make_wire_from_edges_rwire(edges=[rail])
    result = scad.sweep_rsolid(profile=section_face, path=rail_wire, is_frenet=False)

    # ---- feature: rectangular-end-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=12.0, height=9.0, depth=3.0, bottom_face_center=(0.0, -12.0, -1.5))
    result = scad.union_rsolid(result, flange)

    # ---- feature: flange-through-bolts (subtract, profile=geometry) ----
    hole_a = scad.make_cylinder_rsolid(radius=1.5, height=5.0, bottom_face_center=(-4.0, -12.0, -2.0), axis=(0.0, 0.0, 1.0))
    hole_b = scad.make_cylinder_rsolid(radius=1.5, height=5.0, bottom_face_center=(4.0, -12.0, -2.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(result, hole_a, hole_b, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Planar spline hex duct with mounting flange')

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
