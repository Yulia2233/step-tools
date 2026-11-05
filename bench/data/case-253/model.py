from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: waisted-ergonomic-grip (build, profile=geometry) ----
    meridian = scad.make_spline_redge(
        control_points=[[12.0, 0.0, 0.0], [19.0, 0.0, 3.0],
                        [23.0, 0.0, 17.0], [12.0, 0.0, 42.0],
                        [14.0, 0.0, 67.0], [25.0, 0.0, 86.0],
                        [21.0, 0.0, 97.0], [15.0, 0.0, 100.0]],
        degree=3, knots=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        multiplicities=[4, 1, 1, 1, 1, 4])
    top_closure = scad.make_line_redge(start=(15.0, 0.0, 100.0), end=(0.0, 0.0, 100.0))
    axis_closure = scad.make_line_redge(start=(0.0, 0.0, 100.0), end=(0.0, 0.0, 0.0))
    bottom_closure = scad.make_line_redge(start=(0.0, 0.0, 0.0), end=(12.0, 0.0, 0.0))
    profile = scad.make_wire_from_edges_rwire(edges=[meridian, top_closure, axis_closure, bottom_closure])
    result = scad.revolve_rsolid(profile=profile, axis=(0.0, 0.0, 1.0), angle=360.0, origin=(0.0, 0.0, 0.0))

    return scad.make_part_rpart(part_id='part', body=result, name='Waisted ergonomic tool grip')

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
