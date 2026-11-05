from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    # ---- feature: five-station-variable-section-body (build, profile=sketch) ----
    section_0_sketch = scad.make_sketch_rsketch(name='section_0', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -10, -7), ('b', 10, -7), ('c', 10, 7), ('d', -10, 7)]:
        section_0_sketch = scad.add_point_rsketch(sketch=section_0_sketch, point_id=point_id, x=x, y=y)
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e0', start='a', end='b')
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e1', start='b', end='c')
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e2', start='c', end='d')
    section_0_sketch = scad.add_line_rsketch(sketch=section_0_sketch, entity_id='e3', start='d', end='a')
    section_0 = scad.make_wire_from_sketch_rwire(sketch=section_0_sketch)
    section_1_sketch = scad.make_sketch_rsketch(name='section_1', plane={'origin': (1, 0, 6), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -9, -8), ('b', 8, -8), ('c', 11, -2), ('d', 8, 8), ('e', -8, 8), ('f', -11, 1)]:
        section_1_sketch = scad.add_point_rsketch(sketch=section_1_sketch, point_id=point_id, x=x, y=y)
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e0', start='a', end='b')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e1', start='b', end='c')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e2', start='c', end='d')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e3', start='d', end='e')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e4', start='e', end='f')
    section_1_sketch = scad.add_line_rsketch(sketch=section_1_sketch, entity_id='e5', start='f', end='a')
    section_1 = scad.make_wire_from_sketch_rwire(sketch=section_1_sketch)
    section_2_sketch = scad.make_sketch_rsketch(name='section_2', plane={'origin': (2, 0.5, 12), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -8, -9), ('b', 6, -9), ('c', 10, -4), ('d', 9, 5), ('e', 3, 9), ('f', -7, 8), ('g', -10, 2)]:
        section_2_sketch = scad.add_point_rsketch(sketch=section_2_sketch, point_id=point_id, x=x, y=y)
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e0', start='a', end='b')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e1', start='b', end='c')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e2', start='c', end='d')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e3', start='d', end='e')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e4', start='e', end='f')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e5', start='f', end='g')
    section_2_sketch = scad.add_line_rsketch(sketch=section_2_sketch, entity_id='e6', start='g', end='a')
    section_2 = scad.make_wire_from_sketch_rwire(sketch=section_2_sketch)
    section_3_sketch = scad.make_sketch_rsketch(name='section_3', plane={'origin': (1, 1, 18), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -7, -7), ('b', 7, -7), ('c', 9, 0), ('d', 5, 7), ('e', -6, 7), ('f', -9, 0)]:
        section_3_sketch = scad.add_point_rsketch(sketch=section_3_sketch, point_id=point_id, x=x, y=y)
    section_3_sketch = scad.add_line_rsketch(sketch=section_3_sketch, entity_id='e0', start='a', end='b')
    section_3_sketch = scad.add_line_rsketch(sketch=section_3_sketch, entity_id='e1', start='b', end='c')
    section_3_sketch = scad.add_line_rsketch(sketch=section_3_sketch, entity_id='e2', start='c', end='d')
    section_3_sketch = scad.add_line_rsketch(sketch=section_3_sketch, entity_id='e3', start='d', end='e')
    section_3_sketch = scad.add_line_rsketch(sketch=section_3_sketch, entity_id='e4', start='e', end='f')
    section_3_sketch = scad.add_line_rsketch(sketch=section_3_sketch, entity_id='e5', start='f', end='a')
    section_3 = scad.make_wire_from_sketch_rwire(sketch=section_3_sketch)
    section_4_sketch = scad.make_sketch_rsketch(name='section_4', plane={'origin': (0, 1.5, 24), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    for point_id, x, y in [('a', -5, -6), ('b', 4, -7), ('c', 7, -2), ('d', 6, 4), ('e', 1, 7), ('f', -5, 5)]:
        section_4_sketch = scad.add_point_rsketch(sketch=section_4_sketch, point_id=point_id, x=x, y=y)
    section_4_sketch = scad.add_line_rsketch(sketch=section_4_sketch, entity_id='e0', start='a', end='b')
    section_4_sketch = scad.add_line_rsketch(sketch=section_4_sketch, entity_id='e1', start='b', end='c')
    section_4_sketch = scad.add_line_rsketch(sketch=section_4_sketch, entity_id='e2', start='c', end='d')
    section_4_sketch = scad.add_line_rsketch(sketch=section_4_sketch, entity_id='e3', start='d', end='e')
    section_4_sketch = scad.add_line_rsketch(sketch=section_4_sketch, entity_id='e4', start='e', end='f')
    section_4_sketch = scad.add_line_rsketch(sketch=section_4_sketch, entity_id='e5', start='f', end='a')
    section_4 = scad.make_wire_from_sketch_rwire(sketch=section_4_sketch)
    result = scad.loft_rsolid(profiles=[section_0, section_1, section_2, section_3, section_4], ruled=False)

    # ---- feature: offset-integral-boss (add, profile=geometry) ----
    boss = scad.make_cylinder_rsolid(radius=5.0, height=6.5, bottom_face_center=(9, 0, -1), axis=(0, 0, 1))
    result = scad.union_rsolid(result, boss)

    # ---- feature: boss-blind-bore (subtract, profile=geometry) ----
    bore = scad.make_cylinder_rsolid(radius=2.1, height=3.0, bottom_face_center=(9, 0, 2.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bore, skip_non_intersecting=False)

    return scad.make_part_rpart(part_id='part', body=result, name='Variable-section lofted mounting handle')

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
