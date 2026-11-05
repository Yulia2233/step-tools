from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: closed-oval-sweep-profile (sketch, profile=geometry) ----
    profile_wire = scad.make_periodic_spline_rwire(points=[[6.0, 0, 0], [5.19615, 2.0, 0], [3.0, 3.4641, 0], [0, 4.0, 0], [-3.0, 3.4641, 0], [-5.19615, 2.0, 0], [-6.0, 0, 0], [-5.19615, -2.0, 0], [-3.0, -3.4641, 0], [0, -4.0, 0], [3.0, -3.4641, 0], [5.19615, -2.0, 0]], tolerance=0.000001)
    profile = scad.make_face_from_wires_rface(outer_wire=profile_wire, inner_wires=[], normal=(0, 0, 1))

    # ---- feature: six-pole-freeform-rail (path, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[0, 0, 0], [0, 0, 18], [8, 4, 36], [4, 9, 54], [-7, 5, 70], [0, 0, 84]], degree=3, knots=[0.0, 0.3333333333, 0.6666666667, 1.0], multiplicities=[4, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: square-end-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=30.0, height=30.0, depth=8.0, bottom_face_center=(0, 0, -4))
    result = scad.union_rsolid(result, flange)

    # ---- feature: two-through-bolt-holes (subtract, profile=geometry) ----
    hole_a = scad.make_cylinder_rsolid(radius=2.0, height=10.0, bottom_face_center=(-10.0, 0, -5.0), axis=(0, 0, 1))
    hole_b = scad.make_cylinder_rsolid(radius=2.0, height=10.0, bottom_face_center=(10.0, 0, -5.0), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, hole_a, hole_b, skip_non_intersecting=False)
    return scad.make_part_rpart(part_id='part', body=result, name='Freeform swept duct mount')

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
