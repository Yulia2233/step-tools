from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: round-section-bent-grip (build, profile=geometry) ----
    grip_section_sketch = scad.make_sketch_rsketch(name='grip_section', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    grip_section_sketch = scad.add_point_rsketch(sketch=grip_section_sketch, point_id='c', x=0.0, y=0.0)
    grip_section_sketch = scad.add_circle_rsketch(sketch=grip_section_sketch, entity_id='circle', center='c', radius=3.2)
    grip_section = scad.make_face_from_sketch_rface(sketch=grip_section_sketch)
    path_sketch = scad.make_sketch_rsketch(name='grip_path', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 0, 1)})
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p0', x=0, y=0)
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p1', x=0, y=26)
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p2', x=8, y=34)
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p3', x=50, y=34)
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p4', x=58, y=26)
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p5', x=58, y=0)
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p6', x=8, y=26)
    path_sketch = scad.add_point_rsketch(sketch=path_sketch, point_id='p7', x=50, y=26)
    path_sketch = scad.add_line_rsketch(sketch=path_sketch, entity_id='e0', start='p0', end='p1')
    path_sketch = scad.add_arc_rsketch(sketch=path_sketch, entity_id='e1', start='p2', end='p1', center='p6')
    path_sketch = scad.add_line_rsketch(sketch=path_sketch, entity_id='e2', start='p2', end='p3')
    path_sketch = scad.add_arc_rsketch(sketch=path_sketch, entity_id='e3', start='p4', end='p3', center='p7')
    path_sketch = scad.add_line_rsketch(sketch=path_sketch, entity_id='e4', start='p4', end='p5')
    grip_path = scad.make_wire_from_sketch_rwire(sketch=path_sketch)
    result = scad.sweep_rsolid(profile=grip_section, path=grip_path)
    
    # ---- feature: integral-two-foot-mounts (add, profile=geometry) ----
    foot0 = scad.make_box_rsolid(width=18.0, height=22.0, depth=5.0, bottom_face_center=(0, 0, -2))
    foot1 = scad.make_box_rsolid(width=18.0, height=22.0, depth=5.0, bottom_face_center=(58, 0, -2))
    result = scad.union_rsolid(result, foot0, foot1)
    
    # ---- feature: mounting-pattern-4-holes (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(0.0, -7.0, -3), axis=(0, 0, 1))
    bolt_1 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(0.0, 7.0, -3), axis=(0, 0, 1))
    bolt_2 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(58.0, -7.0, -3), axis=(0, 0, 1))
    bolt_3 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(58.0, 7.0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_0, bolt_1, bolt_2, bolt_3, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Swept machine guard handle variant 9')

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
