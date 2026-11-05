from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: contoured-nozzle-meridian (build, profile=geometry) ----
    meridian = scad.make_spline_redge(control_points=[[17, 0, 0], [17, 0, 3], [20, 0, 12], [10, 0, 24], [7, 0, 34], [8, 0, 42], [8, 0, 45]], degree=3, knots=[0.0, 0.25, 0.5, 0.75, 1.0], multiplicities=[4, 1, 1, 1, 4])
    outlet_end = scad.make_line_redge(start=(8, 0, 45), end=(0, 0, 45))
    axis_side = scad.make_line_redge(start=(0, 0, 45), end=(0, 0, 0))
    base_end = scad.make_line_redge(start=(0, 0, 0), end=(17, 0, 0))
    profile = scad.make_wire_from_edges_rwire(edges=[meridian, outlet_end, axis_side, base_end])
    result = scad.revolve_rsolid(profile=profile, axis=(0, 0, 1), angle=360, origin=(0, 0, 0))

    # ---- feature: axial-through-flow-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=3.0, height=49.0, bottom_face_center=(0, 0, -2), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Contoured spline-revolved nozzle sleeve')

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
