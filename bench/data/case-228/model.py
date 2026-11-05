from pathlib import Path

import simplecadapi as scad
from simplecadapi import ql


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: mixed-straight-spline-rail (build, profile=geometry) ----
    lead = scad.make_line_redge(start=(0.0, 0.0, 0.0), end=(8.0, 0.0, 0.0))
    curve = scad.make_spline_redge(control_points=[[8.0, 0.0, 0.0], [12.0, 0.0, 0.0], [19.0, 0.0, 9.0], [26.0, 0.0, 9.0]], degree=3, knots=[0.0, 1.0], multiplicities=[4, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[lead, curve])
    profile = scad.make_rectangle_rface(width=6.0, height=4.0, center=(0.0, 0.0, 0.0), normal=(1.0, 0.0, 0.0))
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False, start_face_tag='cap.start', end_face_tag='cap.end', side_faces_tag='rail.wall')

    # ---- feature: lead-in-edge-chamfers (modify, profile=geometry) ----
    lead_edges = ql.edges().where(ql.and_(ql.prop('geom.center.x', '>=', -0.1), ql.prop('geom.center.x', '<=', 0.1), ql.prop('geom.length', '>=', 5.9), ql.prop('geom.length', '<=', 6.1))).exactly(2)
    result = scad.chamfer_rsolid(solid=result, edges=lead_edges, distance=0.35)

    return scad.make_part_rpart(part_id='part', body=result, name='Spline-railed handgrip')

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
