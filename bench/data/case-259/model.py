from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: ergonomic-thumb-pad (build, profile=geometry) ----
    upper_left = scad.make_spline_redge(control_points=[[-22.5, 0.0, 0.0], [-22.5, 7.0, 0.0], [-10.0, 11.0, 0.0], [0.0, 11.0, 0.0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    upper_right = scad.make_spline_redge(control_points=[[0.0, 11.0, 0.0], [12.0, 11.0, 0.0], [22.5, 5.0, 0.0], [22.5, 0.0, 0.0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    lower_right = scad.make_spline_redge(control_points=[[22.5, 0.0, 0.0], [22.5, -5.0, 0.0], [8.0, -9.0, 0.0], [0.0, -9.0, 0.0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    lower_left = scad.make_spline_redge(control_points=[[0.0, -9.0, 0.0], [-8.0, -9.0, 0.0], [-22.5, -7.0, 0.0], [-22.5, 0.0, 0.0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    profile = scad.make_wire_from_edges_rwire(edges=[upper_left, upper_right, lower_right, lower_left])
    result = scad.extrude_rsolid(profile=profile, direction=(0.0, 0.0, 1.0), distance=12.0)

    return scad.make_part_rpart(part_id='part', body=result, name='Ergonomic spline thumb pad')

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
