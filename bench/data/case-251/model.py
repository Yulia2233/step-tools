from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: ergonomic-grip-meridian (build, profile=geometry) ----
    bottom = scad.make_line_redge(start=(0, 0, 0), end=(16, 0, 0))
    collar = scad.make_line_redge(start=(16, 0, 0), end=(16, 0, 6))
    shoulder = scad.make_line_redge(start=(16, 0, 6), end=(12, 0, 6))
    grip = scad.make_spline_redge(control_points=[[12, 0, 6], [12, 0, 12], [8, 0, 24], [14, 0, 43], [19, 0, 60], [18, 0, 75], [12, 0, 80]], degree=3, knots=[0.0, 0.25, 0.5, 0.75, 1.0], multiplicities=[4, 1, 1, 1, 4])
    cap = scad.make_line_redge(start=(12, 0, 80), end=(0, 0, 80))
    axis_side = scad.make_line_redge(start=(0, 0, 80), end=(0, 0, 0))
    meridian = scad.make_wire_from_edges_rwire(edges=[bottom, collar, shoulder, grip, cap, axis_side])
    result = scad.revolve_rsolid(profile=meridian, axis=(0, 0, 1), angle=360, origin=(0, 0, 0))

    # ---- feature: collar-and-cap-comfort-rounds (modify, profile=geometry) ----
    rims = scad.ql.edges().where(scad.ql.prop('geom.type', '==', 'CIRCLE')).exactly(4)
    result = scad.fillet_rsolid(solid=result, edges=rims, radius=0.8)

    return scad.make_part_rpart(part_id='part', body=result, name='Ergonomic machine handle with mounting collar')

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
