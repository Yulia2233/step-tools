from pathlib import Path

import simplecadapi as scad
from simplecadapi import ql


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: contoured-handle-with-blind-socket (build, profile=geometry) ----
    meridian = scad.make_spline_redge(control_points=[[16, 0, 0], [16, 0, 12], [29, 0, 30], [11, 0, 65], [18, 0, 88], [18, 0, 100]], degree=3, knots=[0.0, 0.33, 0.67, 1.0], multiplicities=[4, 1, 1, 4])
    top = scad.make_line_redge(start=(18, 0, 100), end=(0, 0, 100))
    axis = scad.make_line_redge(start=(0, 0, 100), end=(0, 0, 30))
    socket_roof = scad.make_line_redge(start=(0, 0, 30), end=(6, 0, 30))
    socket_wall = scad.make_line_redge(start=(6, 0, 30), end=(6, 0, 0))
    base = scad.make_line_redge(start=(6, 0, 0), end=(16, 0, 0))
    profile = scad.make_wire_from_edges_rwire(edges=[meridian, top, axis, socket_roof, socket_wall, base])
    result = scad.revolve_rsolid(profile=profile, axis=(0, 0, 1), angle=360, origin=(0, 0, 0))

    # ---- feature: rounded-grip-and-socket-rims (modify, profile=geometry) ----
    rims = ql.edges().where(ql.and_(ql.prop('geom.type', '==', 'CIRCLE'), ql.or_(ql.prop('geom.center.z', '<=', 0.01), ql.prop('geom.center.z', '>=', 99.99)))).exactly(3)
    result = scad.fillet_rsolid(solid=result, edges=rims, radius=1.2)

    return scad.make_part_rpart(part_id='part', body=result, name='Contoured lever handle with blind mounting socket')

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
