from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: turned-functional-section (build, profile=geometry) ----
    section_s = scad.make_sketch_rsketch(name='section', plane={'origin': (0.0, 0.0, 0.0), 'x_axis': (1.0, 0.0, 0.0), 'y_axis': (0.0, 0.0, 1.0)})
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p0', x=0, y=0)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p1', x=25, y=0)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p2', x=25, y=6)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p3', x=20, y=6)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p4', x=20, y=22)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p5', x=25, y=22)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p6', x=25, y=28)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p7', x=11, y=28)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p8', x=11, y=33)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p9', x=0, y=33)
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e0', start='p0', end='p1')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e1', start='p1', end='p2')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e2', start='p2', end='p3')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e3', start='p3', end='p4')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e4', start='p4', end='p5')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e5', start='p5', end='p6')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e6', start='p6', end='p7')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e7', start='p7', end='p8')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e8', start='p8', end='p9')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e9', start='p9', end='p0')
    section_face = scad.make_face_from_sketch_rface(sketch=section_s, profile='e0')
    result = scad.revolve_rsolid(profile=section_face, axis=(0, 0, 1), angle=360.0, origin=(0, 0, 0))
    
    # ---- feature: flange-lower-edge-round (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE'))
        .where(predicate=scad.ql.prop(path='geom.center.z', op='>=', value_=-0.001))
        .where(predicate=scad.ql.prop(path='geom.center.z', op='<=', value_=0.001))
        .where(predicate=scad.ql.prop(path='geom.length', op='>=', value_=157.06963267948967))
        .where(predicate=scad.ql.prop(path='geom.length', op='<=', value_=157.08963267948965)).exactly(count=1).resolve(scope=result))
    result = scad.fillet_rsolid(solid=result, edges=rim, radius=0.7)
    
    # ---- feature: toroidal-relief-14 (subtract, profile=geometry) ----
    groove_s = scad.make_sketch_rsketch(name='toroidal-relief', plane={'origin': (0.0, 0.0, 0.0), 'x_axis': (1.0, 0.0, 0.0), 'y_axis': (0.0, 0.0, 1.0)})
    groove_s = scad.add_point_rsketch(sketch=groove_s, point_id='c', x=21.0, y=14)
    groove_s = scad.add_circle_rsketch(sketch=groove_s, entity_id='circle', center='c', radius=4.5)
    groove_face = scad.make_face_from_sketch_rface(sketch=groove_s, profile='circle')
    tool = scad.revolve_rsolid(profile=groove_face, axis=(0, 0, 1), angle=360.0, origin=(0, 0, 0))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: axial-bore (subtract, profile=geometry) ----
    tool = scad.make_cylinder_rsolid(radius=5.0, height=36, bottom_face_center=(0, 0, -1), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: mounting-hole-pattern (subtract, profile=geometry) ----
    tools = []
    for center in [(19.0, 0.0, -1), (-9.5, 16.45448, -1), (-9.5, -16.45448, -1)]:
        tool = scad.make_cylinder_rsolid(radius=1.6, height=8, bottom_face_center=center, axis=(0, 0, 1))
        tools.append(tool)
    result = scad.cut_rsolid(result, tools, skip_non_intersecting=False)
    
    # ---- feature: transverse-service-port (subtract, profile=geometry) ----
    tool = scad.make_cylinder_rsolid(radius=1.7, height=72, bottom_face_center=(-36, 0, 30), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='cable-guide-pulley combination 1')

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
