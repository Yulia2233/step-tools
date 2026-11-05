from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: four-station-sculpted-cover (build, profile=geometry) ----
    crown_0_sketch = scad.make_sketch_rsketch(name='crown_0', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p0', x=-18.55087, y=-14.5899)
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p1', x=19.43038, y=-13.39629)
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p2', x=18.55087, y=14.5899)
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p3', x=-19.43038, y=13.39629)
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e0', start='p0', end='p1')
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e1', start='p1', end='p2')
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e2', start='p2', end='p3')
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e3', start='p3', end='p0')
    crown_0 = scad.make_wire_from_sketch_rwire(sketch=crown_0_sketch)
    crown_1_sketch = scad.make_sketch_rsketch(name='crown_1', plane={'origin': (1, 0, 8), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p0', x=-19.67118, y=-16.70463)
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p1', x=22.18152, y=-13.19016)
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p2', x=19.67118, y=16.70463)
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p3', x=-22.18152, y=13.19016)
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e0', start='p0', end='p1')
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e1', start='p1', end='p2')
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e2', start='p2', end='p3')
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e3', start='p3', end='p0')
    crown_1 = scad.make_wire_from_sketch_rwire(sketch=crown_1_sketch)
    crown_2_sketch = scad.make_sketch_rsketch(name='crown_2', plane={'origin': (-1, 0, 17), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p0', x=-13.36835, y=-12.93396)
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p1', x=16.35409, y=-8.86249)
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p2', x=13.36835, y=12.93396)
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p3', x=-16.35409, y=8.86249)
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e0', start='p0', end='p1')
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e1', start='p1', end='p2')
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e2', start='p2', end='p3')
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e3', start='p3', end='p0')
    crown_2 = scad.make_wire_from_sketch_rwire(sketch=crown_2_sketch)
    crown_3_sketch = scad.make_sketch_rsketch(name='crown_3', plane={'origin': (0, 0, 26), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p0', x=-8.80709, y=-6.27974)
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p1', x=9.18402, y=-5.71434)
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p2', x=8.80709, y=6.27974)
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p3', x=-9.18402, y=5.71434)
    crown_3_sketch = scad.add_line_rsketch(sketch=crown_3_sketch, entity_id='e0', start='p0', end='p1')
    crown_3_sketch = scad.add_line_rsketch(sketch=crown_3_sketch, entity_id='e1', start='p1', end='p2')
    crown_3_sketch = scad.add_line_rsketch(sketch=crown_3_sketch, entity_id='e2', start='p2', end='p3')
    crown_3_sketch = scad.add_line_rsketch(sketch=crown_3_sketch, entity_id='e3', start='p3', end='p0')
    crown_3 = scad.make_wire_from_sketch_rwire(sketch=crown_3_sketch)
    result = scad.loft_rsolid(profiles=[crown_0, crown_1, crown_2, crown_3], ruled=False)
    
    # ---- feature: gasket-land-flange (add, profile=geometry) ----
    flange = scad.make_box_rsolid(width=54.0, height=42.0, depth=5.0, bottom_face_center=(0, 0, -2))
    result = scad.union_rsolid(result, flange)
    
    # ---- feature: lofted-electronics-pocket (subtract, profile=geometry) ----
    pocket_0_sketch = scad.make_sketch_rsketch(name='pocket_0', plane={'origin': (0, 0, -3), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    pocket_0_sketch = scad.add_point_rsketch(sketch=pocket_0_sketch, point_id='p0', x=-10.5, y=-7.0)
    pocket_0_sketch = scad.add_point_rsketch(sketch=pocket_0_sketch, point_id='p1', x=10.5, y=-7.0)
    pocket_0_sketch = scad.add_point_rsketch(sketch=pocket_0_sketch, point_id='p2', x=10.5, y=7.0)
    pocket_0_sketch = scad.add_point_rsketch(sketch=pocket_0_sketch, point_id='p3', x=-10.5, y=7.0)
    pocket_0_sketch = scad.add_line_rsketch(sketch=pocket_0_sketch, entity_id='e0', start='p0', end='p1')
    pocket_0_sketch = scad.add_line_rsketch(sketch=pocket_0_sketch, entity_id='e1', start='p1', end='p2')
    pocket_0_sketch = scad.add_line_rsketch(sketch=pocket_0_sketch, entity_id='e2', start='p2', end='p3')
    pocket_0_sketch = scad.add_line_rsketch(sketch=pocket_0_sketch, entity_id='e3', start='p3', end='p0')
    pocket_0 = scad.make_wire_from_sketch_rwire(sketch=pocket_0_sketch)
    pocket_1_sketch = scad.make_sketch_rsketch(name='pocket_1', plane={'origin': (0, 0, 8), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    pocket_1_sketch = scad.add_point_rsketch(sketch=pocket_1_sketch, point_id='p0', x=-8.5, y=-6.0)
    pocket_1_sketch = scad.add_point_rsketch(sketch=pocket_1_sketch, point_id='p1', x=8.5, y=-6.0)
    pocket_1_sketch = scad.add_point_rsketch(sketch=pocket_1_sketch, point_id='p2', x=8.5, y=6.0)
    pocket_1_sketch = scad.add_point_rsketch(sketch=pocket_1_sketch, point_id='p3', x=-8.5, y=6.0)
    pocket_1_sketch = scad.add_line_rsketch(sketch=pocket_1_sketch, entity_id='e0', start='p0', end='p1')
    pocket_1_sketch = scad.add_line_rsketch(sketch=pocket_1_sketch, entity_id='e1', start='p1', end='p2')
    pocket_1_sketch = scad.add_line_rsketch(sketch=pocket_1_sketch, entity_id='e2', start='p2', end='p3')
    pocket_1_sketch = scad.add_line_rsketch(sketch=pocket_1_sketch, entity_id='e3', start='p3', end='p0')
    pocket_1 = scad.make_wire_from_sketch_rwire(sketch=pocket_1_sketch)
    pocket_2_sketch = scad.make_sketch_rsketch(name='pocket_2', plane={'origin': (0, 0, 18), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    pocket_2_sketch = scad.add_point_rsketch(sketch=pocket_2_sketch, point_id='p0', x=-5.0, y=-3.5)
    pocket_2_sketch = scad.add_point_rsketch(sketch=pocket_2_sketch, point_id='p1', x=5.0, y=-3.5)
    pocket_2_sketch = scad.add_point_rsketch(sketch=pocket_2_sketch, point_id='p2', x=5.0, y=3.5)
    pocket_2_sketch = scad.add_point_rsketch(sketch=pocket_2_sketch, point_id='p3', x=-5.0, y=3.5)
    pocket_2_sketch = scad.add_line_rsketch(sketch=pocket_2_sketch, entity_id='e0', start='p0', end='p1')
    pocket_2_sketch = scad.add_line_rsketch(sketch=pocket_2_sketch, entity_id='e1', start='p1', end='p2')
    pocket_2_sketch = scad.add_line_rsketch(sketch=pocket_2_sketch, entity_id='e2', start='p2', end='p3')
    pocket_2_sketch = scad.add_line_rsketch(sketch=pocket_2_sketch, entity_id='e3', start='p3', end='p0')
    pocket_2 = scad.make_wire_from_sketch_rwire(sketch=pocket_2_sketch)
    pocket = scad.loft_rsolid(profiles=[pocket_0, pocket_1, pocket_2], ruled=False)
    result = scad.cut_rsolid(result, pocket, skip_non_intersecting=False)
    
    # ---- feature: mounting-pattern-2-holes (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(-22.0, -16.0, -3), axis=(0, 0, 1))
    bolt_1 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(22.0, 16.0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_0, bolt_1, skip_non_intersecting=False)
    
    # ---- feature: conical-fastener-leadins (subtract, profile=geometry) ----
    lead_0 = scad.make_cone_rsolid(bottom_radius=1.5, top_radius=2.4, height=1.0, bottom_face_center=(-22.0, -16.0, 2.1), axis=(0,0,1))
    lead_1 = scad.make_cone_rsolid(bottom_radius=1.5, top_radius=2.4, height=1.0, bottom_face_center=(22.0, 16.0, 2.1), axis=(0,0,1))
    result = scad.cut_rsolid(result, lead_0, lead_1, skip_non_intersecting=False)
    
    # ---- feature: side-cable-entry (subtract, profile=geometry) ----
    entry = scad.make_cylinder_rsolid(radius=2.2, height=50.0, bottom_face_center=(-25, 0, 10), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, entry, skip_non_intersecting=False)
    
    # ---- feature: top-indicator-recess (subtract, profile=geometry) ----
    indicator = scad.make_cylinder_rsolid(radius=2.5, height=5.0, bottom_face_center=(0, 0, 23), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, indicator, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Four-station sensor enclosure variant 7')

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
