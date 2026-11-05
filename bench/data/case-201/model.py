from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:

    # ---- feature: rectangular-grip-section (build, profile=geometry) ----
    section = scad.make_sketch_rsketch(name='grip_section', plane='XY')
    section = scad.add_point_rsketch(sketch=section, point_id='a', x=-8.0, y=-5.0)
    section = scad.add_point_rsketch(sketch=section, point_id='b', x=8.0, y=-5.0)
    section = scad.add_point_rsketch(sketch=section, point_id='c', x=8.0, y=5.0)
    section = scad.add_point_rsketch(sketch=section, point_id='d', x=-8.0, y=5.0)
    section = scad.add_line_rsketch(sketch=section, entity_id='ab', start='a', end='b')
    section = scad.add_line_rsketch(sketch=section, entity_id='bc', start='b', end='c')
    section = scad.add_line_rsketch(sketch=section, entity_id='cd', start='c', end='d')
    section = scad.add_line_rsketch(sketch=section, entity_id='da', start='d', end='a')
    section_wire = scad.make_wire_from_sketch_rwire(sketch=section)
    profile = scad.make_face_from_wire_rface(wire=section_wire, normal=(0, 0, 1))

    # ---- feature: spatial-offset-grip (build, profile=geometry) ----
    rail_edge = scad.make_spline_redge(control_points=[[0, 0, 0], [0, 0, 25], [22, 16, 50], [8, 30, 78], [8, 30, 100]], degree=3, knots=[0.0, 0.5, 1.0], multiplicities=[4, 1, 4])
    rail = scad.make_wire_from_edges_rwire(edges=[rail_edge])
    result = scad.sweep_rsolid(profile=profile, path=rail, is_frenet=False)

    # ---- feature: grip-end-edge-break (modify, profile=geometry) ----
    end_edges = scad.ql.edges().where(predicate=scad.ql.prop(path='geom.center.z', op='>=', value_=-0.01)).where(predicate=scad.ql.prop(path='geom.center.z', op='<=', value_=0.01))
    result = scad.chamfer_rsolid(solid=result, edges=end_edges.exactly(count=4), distance=0.8)

    return scad.make_part_rpart(part_id='part', body=result, name='Spatial offset rectangular equipment grip')

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
