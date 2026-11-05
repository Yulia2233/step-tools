from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: spline-meridian-pressure-body (build, profile=geometry) ----
    outer_meridian = scad.make_spline_redge(
        control_points=[[18.0, 0.0, 0.0], [29.0, 0.0, 8.0], [28.0, 0.0, 24.0], [18.0, 0.0, 39.0], [14.0, 0.0, 50.0]],
        degree=3,
        knots=[0.0, 0.5, 1.0],
        multiplicities=[4, 1, 4],
    )
    bottom_closure = scad.make_segment_redge(start=[0.0, 0.0, 0.0], end=[18.0, 0.0, 0.0])
    axis_closure = scad.make_segment_redge(start=[0.0, 0.0, 0.0], end=[0.0, 0.0, 50.0])
    top_closure = scad.make_segment_redge(start=[0.0, 0.0, 50.0], end=[14.0, 0.0, 50.0])
    profile = scad.make_wire_from_edges_rwire(edges=[bottom_closure, outer_meridian, top_closure, axis_closure])
    result = scad.revolve_rsolid(profile=profile, axis=(0.0, 0.0, 1.0), angle=360.0, origin=(0.0, 0.0, 0.0))

    # ---- feature: soften-end-rims (modify, profile=geometry) ----
    rim_edges = scad.ql.edges().where(scad.ql.and_(
        scad.ql.prop('geom.type', '==', 'CIRCLE'),
        scad.ql.prop('geom.length', '>=', 80.0),
        scad.ql.or_(
            scad.ql.and_(scad.ql.prop('geom.center.z', '>=', -0.1), scad.ql.prop('geom.center.z', '<=', 0.1)),
            scad.ql.and_(scad.ql.prop('geom.center.z', '>=', 49.9), scad.ql.prop('geom.center.z', '<=', 50.1)),
        ),
    )).exactly(2)
    result = scad.fillet_rsolid(solid=result, edges=rim_edges, radius=0.8)

    return scad.make_part_rpart(part_id='part', body=result, name='Spline-bodied rotary pressure housing')

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
