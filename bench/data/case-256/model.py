from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: contoured-grip-revolution (build, profile=geometry) ----
    meridian = scad.make_spline_redge(
        control_points=[[14.0, 0.0, 0.0], [19.0, 0.0, 3.0],
                        [22.0, 0.0, 15.0], [16.0, 0.0, 30.0],
                        [15.0, 0.0, 49.0], [20.0, 0.0, 65.0],
                        [18.0, 0.0, 77.0], [12.0, 0.0, 80.0]],
        degree=3, knots=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        multiplicities=[4, 1, 1, 1, 1, 4])
    top = scad.make_line_redge(start=(12.0, 0.0, 80.0), end=(0.0, 0.0, 80.0))
    axis_side = scad.make_line_redge(start=(0.0, 0.0, 80.0), end=(0.0, 0.0, 0.0))
    bottom = scad.make_line_redge(start=(0.0, 0.0, 0.0), end=(14.0, 0.0, 0.0))
    profile = scad.make_wire_from_edges_rwire(edges=[meridian, top, axis_side, bottom])
    result = scad.revolve_rsolid(profile=profile, axis=(0.0, 0.0, 1.0),
                                 angle=360.0, origin=(0.0, 0.0, 0.0))

    # ---- feature: axial-shaft-through-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=5.0, height=84.0,
                                   bottom_face_center=(0.0, 0.0, -2.0), axis=(0.0, 0.0, 1.0))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Contoured instrument grip sleeve')

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
