from pathlib import Path
import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: turned-functional-section (build, profile=geometry) ----
    section_s = scad.make_sketch_rsketch(name='section', plane={'origin': (0.0, 0.0, 0.0), 'x_axis': (1.0, 0.0, 0.0), 'y_axis': (0.0, 0.0, 1.0)})
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p0', x=0, y=0)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p1', x=29, y=0)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p2', x=29, y=6)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p3', x=20, y=6)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p4', x=20, y=9)
    section_s = scad.add_point_rsketch(sketch=section_s, point_id='p5', x=0, y=9)
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e0', start='p0', end='p1')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e1', start='p1', end='p2')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e2', start='p2', end='p3')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e3', start='p3', end='p4')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e4', start='p4', end='p5')
    section_s = scad.add_line_rsketch(sketch=section_s, entity_id='e5', start='p5', end='p0')
    section_face = scad.make_face_from_sketch_rface(sketch=section_s, profile='e0')
    result = scad.revolve_rsolid(profile=section_face, axis=(0, 0, 1), angle=360.0, origin=(0, 0, 0))
    
    # ---- feature: flange-lower-edge-round (modify, profile=geometry) ----
    rim = (scad.ql.edges().where(predicate=scad.ql.prop(path='geom.type', op='==', value_='CIRCLE'))
        .where(predicate=scad.ql.prop(path='geom.center.z', op='>=', value_=-0.001))
        .where(predicate=scad.ql.prop(path='geom.center.z', op='<=', value_=0.001))
        .where(predicate=scad.ql.prop(path='geom.length', op='>=', value_=182.20237390820802))
        .where(predicate=scad.ql.prop(path='geom.length', op='<=', value_=182.222373908208)).exactly(count=1).resolve(scope=result))
    result = scad.fillet_rsolid(solid=result, edges=rim, radius=0.7)
    
    # ---- feature: spherical-dome (add, profile=geometry) ----
    dome = scad.make_sphere_rsolid(radius=22.0, center=(0.0, 0.0, 6.0))
    upper_half = scad.make_box_rsolid(width=60.0, height=60.0, depth=40.0, bottom_face_center=(0.0, 0.0, 0.0))
    dome = scad.intersect_rsolid(dome, upper_half)
    result = scad.union_rsolid(result, dome)
    
    # ---- feature: spherical-inner-cavity (subtract, profile=geometry) ----
    tool = scad.make_sphere_rsolid(radius=17.0, center=(0.0, 0.0, 3.0))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: dome-crown-vent (subtract, profile=geometry) ----
    tool = scad.make_cylinder_rsolid(radius=3.0, height=40, bottom_face_center=(0, 0, -1), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: mounting-hole-pattern (subtract, profile=geometry) ----
    tools = []
    for center in [(25.0, 0.0, -1), (-12.5, 21.65064, -1), (-12.5, -21.65064, -1)]:
        tool = scad.make_cylinder_rsolid(radius=1.6, height=8, bottom_face_center=center, axis=(0, 0, 1))
        tools.append(tool)
    result = scad.cut_rsolid(result, tools, skip_non_intersecting=False)
    
    # ---- feature: transverse-service-port (subtract, profile=geometry) ----
    tool = scad.make_cylinder_rsolid(radius=2.2, height=72, bottom_face_center=(-36, 0, 11), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    # ---- feature: cable-entry-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=4.0, height=8.0, bottom_face_center=(17, 0, 12), axis=(1, 0, 0))
    result = scad.union_rsolid(result, boss)
    
    # ---- feature: cable-entry-throat (subtract, profile=geometry) ----
    tool = scad.make_cylinder_rsolid(radius=2.0, height=16, bottom_face_center=(12, 0, 12), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, tool, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='domed-instrument-cover combination 1')

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
