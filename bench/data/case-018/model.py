from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: three-station-offset-nozzle (build, profile=geometry) ----
    outer_0_sketch = scad.make_sketch_rsketch(name='outer_0', plane={'origin': (0.0, 0, 0.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    outer_0_sketch = scad.add_point_rsketch(sketch=outer_0_sketch, point_id='c', x=0.0, y=0.0)
    outer_0_sketch = scad.add_circle_rsketch(sketch=outer_0_sketch, entity_id='circle', center='c', radius=12.0)
    outer_0 = scad.make_wire_from_sketch_rwire(sketch=outer_0_sketch)
    outer_1_sketch = scad.make_sketch_rsketch(name='outer_1', plane={'origin': (1.95, 0, 19.68), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    outer_1_sketch = scad.add_point_rsketch(sketch=outer_1_sketch, point_id='c', x=0.0, y=0.0)
    outer_1_sketch = scad.add_circle_rsketch(sketch=outer_1_sketch, entity_id='circle', center='c', radius=10.0)
    outer_1 = scad.make_wire_from_sketch_rwire(sketch=outer_1_sketch)
    outer_2_sketch = scad.make_sketch_rsketch(name='outer_2', plane={'origin': (3.0, 0, 41.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    outer_2_sketch = scad.add_point_rsketch(sketch=outer_2_sketch, point_id='c', x=0.0, y=0.0)
    outer_2_sketch = scad.add_circle_rsketch(sketch=outer_2_sketch, entity_id='circle', center='c', radius=7.0)
    outer_2 = scad.make_wire_from_sketch_rwire(sketch=outer_2_sketch)
    result = scad.loft_rsolid(profiles=[outer_0, outer_1, outer_2], ruled=False)
    
    # ---- feature: integral-mounting-flange (add, profile=geometry) ----
    flange = scad.make_cylinder_rsolid(radius=19.0, height=5.0, bottom_face_center=(0, 0, -2), axis=(0, 0, 1))
    result = scad.union_rsolid(result, flange)
    
    # ---- feature: three-station-flow-passage (subtract, profile=geometry) ----
    inner_0_sketch = scad.make_sketch_rsketch(name='inner_0', plane={'origin': (0.0, 0, -3.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    inner_0_sketch = scad.add_point_rsketch(sketch=inner_0_sketch, point_id='c', x=0.0, y=0.0)
    inner_0_sketch = scad.add_circle_rsketch(sketch=inner_0_sketch, entity_id='circle', center='c', radius=8.0)
    inner_0 = scad.make_wire_from_sketch_rwire(sketch=inner_0_sketch)
    inner_1_sketch = scad.make_sketch_rsketch(name='inner_1', plane={'origin': (1.95, 0, 19.68), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    inner_1_sketch = scad.add_point_rsketch(sketch=inner_1_sketch, point_id='c', x=0.0, y=0.0)
    inner_1_sketch = scad.add_circle_rsketch(sketch=inner_1_sketch, entity_id='circle', center='c', radius=5.8)
    inner_1 = scad.make_wire_from_sketch_rwire(sketch=inner_1_sketch)
    inner_2_sketch = scad.make_sketch_rsketch(name='inner_2', plane={'origin': (3.0, 0, 42.0), 'x_axis': (1, 0, 0), 'y_axis': (0, 1, 0)})
    inner_2_sketch = scad.add_point_rsketch(sketch=inner_2_sketch, point_id='c', x=0.0, y=0.0)
    inner_2_sketch = scad.add_circle_rsketch(sketch=inner_2_sketch, entity_id='circle', center='c', radius=4.0)
    inner_2 = scad.make_wire_from_sketch_rwire(sketch=inner_2_sketch)
    passage = scad.loft_rsolid(profiles=[inner_0, inner_1, inner_2], ruled=False)
    result = scad.cut_rsolid(result, passage, skip_non_intersecting=False)
    
    # ---- feature: mounting-pattern-4-holes (subtract, profile=geometry) ----
    bolt_0 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(16.0, 0.0, -3), axis=(0, 0, 1))
    bolt_1 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(0.0, 16.0, -3), axis=(0, 0, 1))
    bolt_2 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(-16.0, 0.0, -3), axis=(0, 0, 1))
    bolt_3 = scad.make_cylinder_rsolid(radius=1.5, height=8.0, bottom_face_center=(-0.0, -16.0, -3), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_0, bolt_1, bolt_2, bolt_3, skip_non_intersecting=False)
    
    # ---- feature: counterbored-fastener-seats (subtract, profile=geometry) ----
    bolt_seat_0 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(16.0, 0.0, 1.5), axis=(0, 0, 1))
    bolt_seat_1 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(0.0, 16.0, 1.5), axis=(0, 0, 1))
    bolt_seat_2 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-16.0, 0.0, 1.5), axis=(0, 0, 1))
    bolt_seat_3 = scad.make_cylinder_rsolid(radius=2.5, height=2.0, bottom_face_center=(-0.0, -16.0, 1.5), axis=(0, 0, 1))
    result = scad.cut_rsolid(result, bolt_seat_0, bolt_seat_1, bolt_seat_2, bolt_seat_3, skip_non_intersecting=False)
    
    # ---- feature: conical-fastener-leadins (subtract, profile=geometry) ----
    lead_0 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(16.0, 0.0, 2.1), axis=(0,0,1))
    lead_1 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(0.0, 16.0, 2.1), axis=(0,0,1))
    lead_2 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(-16.0, 0.0, 2.1), axis=(0,0,1))
    lead_3 = scad.make_cone_rsolid(bottom_radius=2.5, top_radius=3.2, height=1.0, bottom_face_center=(-0.0, -16.0, 2.1), axis=(0,0,1))
    result = scad.cut_rsolid(result, lead_0, lead_1, lead_2, lead_3, skip_non_intersecting=False)
    
    # ---- feature: radial-pressure-tap (subtract, profile=geometry) ----
    radial_tap = scad.make_cylinder_rsolid(radius=1.5, height=30.0, bottom_face_center=(-15, 0, 14), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, radial_tap, skip_non_intersecting=False)
    
    # ---- feature: flange-orientation-key (subtract, profile=geometry) ----
    key = scad.make_box_rsolid(width=5.0, height=3.0, depth=4.0, bottom_face_center=(18, 0, 0))
    result = scad.cut_rsolid(result, key, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Offset lofted fluid adapter variant 8')

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
