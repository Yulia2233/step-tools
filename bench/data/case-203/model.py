from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: spatial-spline-mounting-arm (build, profile=geometry) ----
    edges = []
    edges.append(scad.make_line_redge(start=(-4, -4, 0), end=(4, -4, 0)))
    edges.append(scad.make_three_point_arc_redge(start=(4, -4, 0), middle=(5.414213562373095, -3.414213562373095, 0), end=(6, -2, 0)))
    edges.append(scad.make_line_redge(start=(6, -2, 0), end=(6, 2, 0)))
    edges.append(scad.make_three_point_arc_redge(start=(6, 2, 0), middle=(5.414213562373095, 3.414213562373095, 0), end=(4, 4, 0)))
    edges.append(scad.make_line_redge(start=(4, 4, 0), end=(-4, 4, 0)))
    edges.append(scad.make_three_point_arc_redge(start=(-4, 4, 0), middle=(-5.414213562373095, 3.414213562373095, 0), end=(-6, 2, 0)))
    edges.append(scad.make_line_redge(start=(-6, 2, 0), end=(-6, -2, 0)))
    edges.append(scad.make_three_point_arc_redge(start=(-6, -2, 0), middle=(-5.414213562373095, -3.414213562373095, 0), end=(-4, -4, 0)))
    outline = scad.make_wire_from_edges_rwire(edges=edges)
    profile = scad.make_face_from_wire_rface(wire=outline, normal=(0, 0, 1))
    rail_edge = scad.make_spline_redge(control_points=[[0, 0, 0], [0, 0, 14], [15, -8, 30], [23, 9, 43], [33, 12, 50]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    # ---- feature: rectangular-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=32.0, height=20.0, depth=5.0, bottom_face_center=(0, 0, -3))
    result = scad.union_rsolid(*[result, flange])

    # ---- feature: two-through-bolt-holes (subtract, profile=geometry) ----
    bolt_left = scad.make_cylinder_rsolid(radius=2.2, height=7.0, bottom_face_center=(-11, 0, -4), axis=(0, 0, 1))
    bolt_right = scad.make_cylinder_rsolid(radius=2.2, height=7.0, bottom_face_center=(11, 0, -4), axis=(0, 0, 1))
    result = scad.cut_rsolid(*[result, bolt_left, bolt_right], skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Spatial curved instrument mounting arm')

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
