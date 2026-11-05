from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: four-station-sculpted-cover (build, profile=geometry) ----
    crown_0_sketch = scad.make_sketch_rsketch(name='crown_0', plane={'origin': (0, 0, 0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p0', x=-18.31942, y=-14.87948)
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p1', x=19.6384, y=-13.08944)
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p2', x=18.31942, y=14.87948)
    crown_0_sketch = scad.add_point_rsketch(sketch=crown_0_sketch, point_id='p3', x=-19.6384, y=13.08944)
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e0', start='p0', end='p1')
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e1', start='p1', end='p2')
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e2', start='p2', end='p3')
    crown_0_sketch = scad.add_line_rsketch(sketch=crown_0_sketch, entity_id='e3', start='p3', end='p0')
    crown_0 = scad.make_wire_from_sketch_rwire(sketch=crown_0_sketch)
    crown_1_sketch = scad.make_sketch_rsketch(name='crown_1', plane={'origin': (1, 0, 8), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p0', x=-19.40637, y=-17.01155)
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p1', x=22.38596, y=-12.84012)
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p2', x=19.40637, y=17.01155)
    crown_1_sketch = scad.add_point_rsketch(sketch=crown_1_sketch, point_id='p3', x=-22.38596, y=12.84012)
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e0', start='p0', end='p1')
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e1', start='p1', end='p2')
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e2', start='p2', end='p3')
    crown_1_sketch = scad.add_line_rsketch(sketch=crown_1_sketch, entity_id='e3', start='p3', end='p0')
    crown_1 = scad.make_wire_from_sketch_rwire(sketch=crown_1_sketch)
    crown_2_sketch = scad.make_sketch_rsketch(name='crown_2', plane={'origin': (-1, 0, 17), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p0', x=-13.16354, y=-13.14235)
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p1', x=16.49128, y=-8.60452)
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p2', x=13.16354, y=13.14235)
    crown_2_sketch = scad.add_point_rsketch(sketch=crown_2_sketch, point_id='p3', x=-16.49128, y=8.60452)
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e0', start='p0', end='p1')
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e1', start='p1', end='p2')
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e2', start='p2', end='p3')
    crown_2_sketch = scad.add_line_rsketch(sketch=crown_2_sketch, entity_id='e3', start='p3', end='p0')
    crown_2 = scad.make_wire_from_sketch_rwire(sketch=crown_2_sketch)
    crown_3_sketch = scad.make_sketch_rsketch(name='crown_3', plane={'origin': (0, 0, 26), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p0', x=-8.70737, y=-6.4173)
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p1', x=9.27265, y=-5.56938)
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p2', x=8.70737, y=6.4173)
    crown_3_sketch = scad.add_point_rsketch(sketch=crown_3_sketch, point_id='p3', x=-9.27265, y=5.56938)
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
    
    # ---- feature: counterbored-fastener-seats (subtract, profile=geometry) ----
    bolt_seat_0 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-22.0, -16.0, 1.5), axis=(0, 0, 1))
    bolt_seat_1 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(22.0, 16.0, 1.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_seat_0, bolt_seat_1, skip_non_intersecting=False)
    
    # ---- feature: conical-fastener-leadins (subtract, profile=geometry) ----
    lead_0 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(-22.0, -16.0, 2.1), axis=(0,0,1))
    lead_1 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(22.0, 16.0, 2.1), axis=(0,0,1))
    result = scad.cut_rsolid(result, lead_0, lead_1, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Four-station sensor enclosure variant 10')

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
