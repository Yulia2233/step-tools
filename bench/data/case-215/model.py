from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: rounded-grip-section (build, profile=geometry) ----
    section = scad.make_sketch_rsketch(name='rounded_grip', plane='XY')
    for point_id, x, y in [('a', -2.0, -2.0), ('b', 2.0, -2.0), ('c', 3.0, -1.0), ('d', 3.0, 1.0), ('e', 2.0, 2.0), ('f', -2.0, 2.0), ('g', -3.0, 1.0), ('h', -3.0, -1.0), ('br', 2.0, -1.0), ('tr', 2.0, 1.0), ('tl', -2.0, 1.0), ('bl', -2.0, -1.0)]:
        section = scad.add_point_rsketch(sketch=section, point_id=point_id, x=x, y=y)
    for entity_id, start, end in [('bottom', 'a', 'b'), ('right', 'c', 'd'), ('top', 'e', 'f'), ('left', 'g', 'h')]:
        section = scad.add_line_rsketch(sketch=section, entity_id=entity_id, start=start, end=end)
    for entity_id, start, end, center in [('lower_right', 'b', 'c', 'br'), ('upper_right', 'd', 'e', 'tr'), ('upper_left', 'f', 'g', 'tl'), ('lower_left', 'h', 'a', 'bl')]:
        section = scad.add_arc_rsketch(sketch=section, entity_id=entity_id, start=start, end=end, center=center)
    perimeter = scad.make_wire_from_sketch_rwire(sketch=section)
    profile = scad.make_face_from_wire_rface(wire=perimeter)

    # ---- feature: planar-s-rail (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[0.0, 0.0, 0.0], [0.0, 0.0, 7.0], [7.0, 0.0, 14.0], [-5.0, 0.0, 21.0], [0.0, 0.0, 28.0]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])

    # ---- feature: ergonomic-offset-grip (build, profile=geometry) ----
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=True)
    print('Sweep volume:', result.get_volume())

    # ---- feature: softened-entry-rim (modify, profile=geometry) ----
    rim = scad.ql.edges().where(predicate=scad.ql.prop(path='geom.length', op='>=', value_=1.9)).where(predicate=scad.ql.prop(path='geom.length', op='<=', value_=4.01)).where(predicate=scad.ql.prop(path='geom.center.z', op='>=', value_=-0.001)).where(predicate=scad.ql.prop(path='geom.center.z', op='<=', value_=0.001)).exactly(count=4)
    print('Selected rim edges:', len(rim.resolve(scope=result)))
    result = scad.fillet_rsolid(solid=result, edges=rim, radius=0.45)
    print('Finished volume:', result.get_volume())

    return scad.make_part_rpart(part_id='part', body=result, name='S-shaped ergonomic latch grip')

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
