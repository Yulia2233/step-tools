from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: mixed-rail-support-arm (build, profile=geometry) ----
    profile = scad.make_rectangle_rface(width=8.0, height=5.0, center=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0))
    straight = scad.make_line_redge(start=(0.0, 0.0, 0.0), end=(0.0, 0.0, 12.0))
    curve = scad.make_spline_redge(control_points=[(0.0, 0.0, 12.0), (0.0, 0.0, 22.0), (12.0, 0.0, 34.0), (18.0, 0.0, 42.0)], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[straight, curve])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)

    # ---- feature: mounting-end-edge-rounds (modify, profile=geometry) ----
    rims = scad.ql.edges().where(scad.ql.and_(scad.ql.prop('geom.center.z', '>=', -0.001), scad.ql.prop('geom.center.z', '<=', 0.001))).exactly(4)
    result = scad.fillet_rsolid(solid=result, edges=rims, radius=0.8)

    return scad.make_part_rpart(part_id='part', body=result, name='Curved rectangular support arm')

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
