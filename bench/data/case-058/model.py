from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: twisted-three-section-support (build, profile=geometry) ----
    section_0_sketch = scad.make_sketch_rsketch(name='section_0', plane={'origin': (0, 0, 0.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    section_0_sketch = scad.add_point_rsketch(sketch=section_0_sketch, point_id='p0', x=-12.0, y=-5.0)
    section_0_sketch = scad.add_point_rsketch(sketch=section_0_sketch, point_id='p1', x=12.0, y=-5.0)
    section_0_sketch = scad.add_point_rsketch(sketch=section_0_sketch, point_id='p2', x=12.0, y=5.0)
    section_0_sketch = scad.add_point_rsketch(sketch=section_0_sketch, point_id='p3', x=-12.0, y=5.0)
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e0', start='p0', end='p1')
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e1', start='p1', end='p2')
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e2', start='p2', end='p3')
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e3', start='p3', end='p0')
    section_0 = scad.make_wire_from_sketch_rwire(sketch=section_0_sketch)
    section_1_sketch = scad.make_sketch_rsketch(name='section_1', plane={'origin': (1, 0, 18.5), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    section_1_sketch = scad.add_point_rsketch(sketch=section_1_sketch, point_id='p0', x=-7.04461, y=-7.18495)
    section_1_sketch = scad.add_point_rsketch(sketch=section_1_sketch, point_id='p1', x=9.97472, y=-1.32472)
    section_1_sketch = scad.add_point_rsketch(sketch=section_1_sketch, point_id='p2', x=7.04461, y=7.18495)
    section_1_sketch = scad.add_point_rsketch(sketch=section_1_sketch, point_id='p3', x=-9.97472, y=1.32472)
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e0', start='p0', end='p1')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e1', start='p1', end='p2')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e2', start='p2', end='p3')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e3', start='p3', end='p0')
    section_1 = scad.make_wire_from_sketch_rwire(sketch=section_1_sketch)
    section_2_sketch = scad.make_sketch_rsketch(name='section_2', plane={'origin': (2, 0, 37.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    section_2_sketch = scad.add_point_rsketch(sketch=section_2_sketch, point_id='p0', x=-5.30097, y=-10.38748)
    section_2_sketch = scad.add_point_rsketch(sketch=section_2_sketch, point_id='p1', x=11.66, y=0.2109)
    section_2_sketch = scad.add_point_rsketch(sketch=section_2_sketch, point_id='p2', x=5.30097, y=10.38748)
    section_2_sketch = scad.add_point_rsketch(sketch=section_2_sketch, point_id='p3', x=-11.66, y=-0.2109)
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e0', start='p0', end='p1')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e1', start='p1', end='p2')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e2', start='p2', end='p3')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e3', start='p3', end='p0')
    section_2 = scad.make_wire_from_sketch_rwire(sketch=section_2_sketch)
    result = scad.loft_rsolid(profiles=[section_0, section_1, section_2], ruled=False)
    
    # ---- feature: machined-base-flange (add, profile=geometry) ----
    base = scad.make_box_rsolid(width=46.0, height=30.0, depth=5.0, bottom_face_center=(0, 0, -2))
    result = scad.union_rsolid(result, base)
    
    # ---- feature: integral-top-register (add, profile=geometry) ----
    register = scad.make_cylinder_rsolid(radius=5.0, height=3.0, bottom_face_center=(2, 0, 36), axis=(0, 0, 1))
    result = scad.union_rsolid(result, register)
    
    # ---- feature: cable-passage (subtract, profile=geometry) ----
    cable = scad.make_cylinder_rsolid(radius=2.0, height=43.0, bottom_face_center=(0, 0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, cable, skip_non_intersecting=False)
    
    # ---- feature: mounting-pattern-4-holes (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(-18.0, -9.0, -3), axis=(0, 0, 1))
    bolt_1 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(18.0, -9.0, -3), axis=(0, 0, 1))
    bolt_2 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(18.0, 9.0, -3), axis=(0, 0, 1))
    bolt_3 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(-18.0, 9.0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_0, bolt_1, bolt_2, bolt_3, skip_non_intersecting=False)
    
    # ---- feature: counterbored-fastener-seats (subtract, profile=geometry) ----
    bolt_seat_0 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-18.0, -9.0, 1.5), axis=(0, 0, 1))
    bolt_seat_1 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(18.0, -9.0, 1.5), axis=(0, 0, 1))
    bolt_seat_2 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(18.0, 9.0, 1.5), axis=(0, 0, 1))
    bolt_seat_3 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-18.0, 9.0, 1.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_seat_0, bolt_seat_1, bolt_seat_2, bolt_seat_3, skip_non_intersecting=False)
    
    # ---- feature: conical-fastener-leadins (subtract, profile=geometry) ----
    lead_0 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(-18.0, -9.0, 2.1), axis=(0,0,1))
    lead_1 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(18.0, -9.0, 2.1), axis=(0,0,1))
    lead_2 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(18.0, 9.0, 2.1), axis=(0,0,1))
    lead_3 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(-18.0, 9.0, 2.1), axis=(0,0,1))
    result = scad.cut_rsolid(result, lead_0, lead_1, lead_2, lead_3, skip_non_intersecting=False)
    
    # ---- feature: cross-drilled-sensor-interface (subtract, profile=geometry) ----
    cross = scad.make_cylinder_rsolid(radius=1.7, height=25.0, bottom_face_center=(0, -12.5, 24.05), axis=(0, 1, 0))
    result = scad.cut_rsolid(result, cross, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Lofted instrumentation support variant 8')

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
