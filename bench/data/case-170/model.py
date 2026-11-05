from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: turned-functional-section (build, profile=geometry) ----
    section_s = scad.make_sketch_rsketch(name='section', plane={'origin': (0.0, 0.0, 0.0), 'x_axis': (1.0, 0.0, 0.0), 'y_axis': (0.0, 0.0, 1.0)})
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p0', x=0, y=0)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p1', x=28, y=0)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p2', x=28, y=6)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p3', x=21, y=6)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p4', x=21, y=10)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p5', x=12, y=30)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p6', x=12, y=35)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p7', x=0, y=35)
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e0', start='p0', end='p1')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e1', start='p1', end='p2')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e2', start='p2', end='p3')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e3', start='p3', end='p4')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e4', start='p4', end='p5')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e5', start='p5', end='p6')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e6', start='p6', end='p7')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e7', start='p7', end='p0')
    section_face = scad.make_face_from_sketch_rface(sketch=section_s, profile='e0')
    result = scad.revolve_rsolid(profile=section_face, axis=(0, 0, 1), angle=360.0, origin=(0, 0, 0))
    
    # ---- feature: flange-lower-edge-bevel (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE'))
        .where(predicate=scad.ql.prop(path='geom.center.z', op='>=', value_=-0.001))
        .where(predicate=scad.ql.prop(path='geom.center.z', op='<=', value_=0.001))
        .where(predicate=scad.ql.prop(path='geom.length', op='>=', value_=175.91918860102842))
        .where(predicate=scad.ql.prop(path='geom.length', op='<=', value_=175.9391886010284)).exactly(count=1).resolve(scope=result))
    result = scad.chamfer_rsolid(solid=result, edges=rim, distance=0.65)
    
    # ---- feature: axial-bore (subtract, profile=geometry) ----
    tool = scad.make_cylinder_rsolid(radius=5.0, height=38, bottom_face_center=(0, 0, -1), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: conical-outlet-seat (subtract, profile=geometry) ----
    tool = scad.make_cone_rsolid(bottom_radius=4.8, top_radius=9.0, height=12.0, bottom_face_center=(0, 0, 24), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: transverse-service-port (subtract, profile=geometry) ----
    tool = scad.make_cylinder_rsolid(radius=2.7, height=72, bottom_face_center=(-36, 0, 14), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: mounting-hole-pattern (subtract, profile=geometry) ----
    tools = []
    for center in [(0.3311, 23.99772, -1), (-16.73482, 17.20307, -1), (-23.99772, 0.3311, -1), (-17.20307, -16.73482, -1), (-0.3311, -23.99772, -1), (16.73482, -17.20307, -1), (23.99772, -0.3311, -1), (17.20307, 16.73482, -1)]:
        tool = scad.make_cylinder_rsolid(radius=1.6, height=8, bottom_face_center=center, axis=(0, 0, 1))
        tools.append(tool)
    result = scad.cut_rsolid(result, tools, skip_non_intersecting=False)
    
    # ---- feature: bolt-head-counterbores (subtract, profile=geometry) ----
    tools = []
    for center in [(0.3311, 23.99772, 3), (-16.73482, 17.20307, 3), (-23.99772, 0.3311, 3), (-17.20307, -16.73482, 3), (-0.3311, -23.99772, 3), (16.73482, -17.20307, 3), (23.99772, -0.3311, 3), (17.20307, 16.73482, 3)]:
        tool = scad.make_cylinder_rsolid(radius=2.55, height=4.0, bottom_face_center=center, axis=(0, 0, 1))
        tools.append(tool)
    result = scad.cut_rsolid(result, tools, skip_non_intersecting=False)
    
    # ---- feature: outlet-wrench-flat (subtract, profile=geometry) ----
    tool = scad.make_box_rsolid(width=12.0, height=35.0, depth=8.0, bottom_face_center=(16.0, 0.0, 28.0))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='conical-manifold combination 10')

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
