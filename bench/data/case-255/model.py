from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: spline-revolved-nozzle-body (build, profile=geometry) ----
    meridian = scad.make_spline_redge(control_points=[[21, 0, 0], [21, 0, 16], [25, 0, 35], [10, 0, 63], [10, 0, 82], [12, 0, 90]], degree=3, knots=[0.0, 0.35, 0.7, 1.0], multiplicities=[4, 1, 1, 4])
    top = scad.make_line_redge(start=(12, 0, 90), end=(0, 0, 90))
    axis_edge = scad.make_line_redge(start=(0, 0, 90), end=(0, 0, 0))
    bottom = scad.make_line_redge(start=(0, 0, 0), end=(21, 0, 0))
    profile = scad.make_wire_from_edges_rwire(edges=[meridian, top, axis_edge, bottom])
    result = scad.revolve_rsolid(profile=profile, axis=(0, 0, 1), angle=360, origin=(0, 0, 0))

    # ---- feature: rectangular-mounting-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=70.0, height=46.0, depth=8.0, bottom_face_center=(0, 0, -6))
    result = scad.union_rsolid(result, flange)

    # ---- feature: axial-flow-passage (subtract, profile=geometry) ----
    passage = scad.make_cylinder_rsolid(radius=7.0, height=100.0, bottom_face_center=(0, 0, -8), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, passage, skip_non_intersecting=False)

    # ---- feature: flange-two-bolt-pattern (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=3.3, height=12.0, bottom_face_center=(-28, 0, -8), axis=(0, 0, 1))
    bolt_1 = scad.make_cylinder_rsolid(radius=3.3, height=12.0, bottom_face_center=(28, 0, -8), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_0, bolt_1, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Spline-contoured two-bolt process nozzle')

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
