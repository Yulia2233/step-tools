from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: hexagonal-grip-section (build, profile=geometry) ----
    section = scad.make_sketch_rsketch(name='hexagonal_grip', plane='XY')
    for point_id, x, y in [('a', 8.0, 0.0), ('b', 4.0, 6.928203), ('c', -4.0, 6.928203), ('d', -8.0, 0.0), ('e', -4.0, -6.928203), ('f', 4.0, -6.928203)]:
        section = scad.add_point_rsketch(sketch=section, point_id=point_id, x=x, y=y)
    for entity_id, start, end in [('ab', 'a', 'b'), ('bc', 'b', 'c'), ('cd', 'c', 'd'), ('de', 'd', 'e'), ('ef', 'e', 'f'), ('fa', 'f', 'a')]:
        section = scad.add_line_rsketch(sketch=section, entity_id=entity_id, start=start, end=end)
    perimeter = scad.make_wire_from_sketch_rwire(sketch=section)
    profile = scad.make_face_from_wire_rface(wire=perimeter)

    # ---- feature: spatial-offset-grip (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[0.0, 0.0, 0.0], [0.0, 0.0, 12.0], [8.0, -4.0, 26.0], [18.0, 8.0, 40.0], [8.0, 14.0, 54.0], [-4.0, 8.0, 68.0], [-4.0, 8.0, 80.0]], degree=3, knots=[0.0, 0.25, 0.5, 0.75, 1.0], multiplicities=[4, 1, 1, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    # ---- feature: grip-end-edge-break (modify, profile=geometry) ----
    end_edges = scad.ql.edges().where(scad.ql.and_(scad.ql.prop('geom.center.z', '>=', -0.01), scad.ql.prop('geom.center.z', '<=', 0.01))).exactly(6)
    result = scad.chamfer_rsolid(solid=result, edges=end_edges, distance=0.6)

    return scad.make_part_rpart(part_id='part', body=result, name='Spatial offset hexagonal equipment grip')

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
