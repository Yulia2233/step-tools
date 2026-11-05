from pathlib import Path

import simplecadapi as scad


@scad.part(id='part', revision='1.0.0', project_root=Path(__file__).parent)
def build() -> scad.Part:
    
    # ---- feature: quarter-circle-pipe-outer (build, profile=geometry) ----
    pipe_outer_sketch = scad.make_sketch_rsketch(name='pipe_outer', plane={'origin': (24, 0, 0), 'x_axis': (0, 0, 1), 'y_axis': (1, 0, 0)})
    pipe_outer_sketch = scad.add_point_rsketch(sketch=pipe_outer_sketch, point_id='c', x=0.0, y=0.0)
    pipe_outer_sketch = scad.add_circle_rsketch(sketch=pipe_outer_sketch, entity_id='circle', center='c', radius=5.0)
    pipe_outer = scad.make_face_from_sketch_rface(sketch=pipe_outer_sketch)
    bend_sketch = scad.make_sketch_rsketch(name='bend_path', plane='XY')
    bend_sketch = scad.add_point_rsketch(sketch=bend_sketch, point_id='p0', x=24, y=0)
    bend_sketch = scad.add_point_rsketch(sketch=bend_sketch, point_id='p1', x=0, y=24)
    bend_sketch = scad.add_point_rsketch(sketch=bend_sketch, point_id='p2', x=0, y=0)
    bend_sketch = scad.add_arc_rsketch(sketch=bend_sketch, entity_id='bend', start='p0', end='p1', center='p2')
    bend_path = scad.make_wire_from_sketch_rwire(sketch=bend_sketch)
    result = scad.sweep_rsolid(profile=pipe_outer, path=bend_path)
    
    # ---- feature: inlet-and-outlet-flanges (add, profile=geometry) ----
    inlet = scad.make_cylinder_rsolid(radius=10.0, height=5.0, bottom_face_center=(24, -2, 0), axis=(0, 1, 0))
    outlet = scad.make_cylinder_rsolid(radius=10.0, height=5.0, bottom_face_center=(-3, 24, 0), axis=(1, 0, 0))
    result = scad.union_rsolid(result, inlet, outlet)
    
    # ---- feature: swept-coolant-channel (subtract, profile=geometry) ----
    pipe_inner_sketch = scad.make_sketch_rsketch(name='pipe_inner', plane={'origin': (24, -4, 0), 'x_axis': (0, 0, 1), 'y_axis': (1, 0, 0)})
    pipe_inner_sketch = scad.add_point_rsketch(sketch=pipe_inner_sketch, point_id='c', x=0.0, y=0.0)
    pipe_inner_sketch = scad.add_circle_rsketch(sketch=pipe_inner_sketch, entity_id='circle', center='c', radius=3.0)
    pipe_inner = scad.make_face_from_sketch_rface(sketch=pipe_inner_sketch)
    flow_sketch = scad.make_sketch_rsketch(name='flow_path', plane='XY')
    flow_sketch = scad.add_point_rsketch(sketch=flow_sketch, point_id='p0', x=24, y=-4)
    flow_sketch = scad.add_point_rsketch(sketch=flow_sketch, point_id='p1', x=24, y=0)
    flow_sketch = scad.add_point_rsketch(sketch=flow_sketch, point_id='p2', x=0, y=24)
    flow_sketch = scad.add_point_rsketch(sketch=flow_sketch, point_id='p3', x=-4, y=24)
    flow_sketch = scad.add_point_rsketch(sketch=flow_sketch, point_id='p4', x=0, y=0)
    flow_sketch = scad.add_line_rsketch(sketch=flow_sketch, entity_id='inlet', start='p0', end='p1')
    flow_sketch = scad.add_arc_rsketch(sketch=flow_sketch, entity_id='bend', start='p1', end='p2', center='p4')
    flow_sketch = scad.add_line_rsketch(sketch=flow_sketch, entity_id='outlet', start='p2', end='p3')
    flow_path = scad.make_wire_from_sketch_rwire(sketch=flow_sketch)
    channel = scad.sweep_rsolid(profile=pipe_inner, path=flow_path)
    result = scad.cut_rsolid(result, channel, skip_non_intersecting=False)
    
    # ---- feature: flange-3-bolt-pattern (subtract, profile=geometry) ----
    in_bolt0 = scad.make_cylinder_rsolid(radius=1.1, height=8.0, bottom_face_center=(29.02046, -3, 5.02046), axis=(0, 1, 0))
    out_bolt0 = scad.make_cylinder_rsolid(radius=1.1, height=8.0, bottom_face_center=(-4, 29.02046, 5.02046), axis=(1, 0, 0))
    in_bolt1 = scad.make_cylinder_rsolid(radius=1.1, height=8.0, bottom_face_center=(17.14193, -3, 1.83762), axis=(0, 1, 0))
    out_bolt1 = scad.make_cylinder_rsolid(radius=1.1, height=8.0, bottom_face_center=(-4, 17.14193, 1.83762), axis=(1, 0, 0))
    in_bolt2 = scad.make_cylinder_rsolid(radius=1.1, height=8.0, bottom_face_center=(25.83762, -3, -6.85807), axis=(0, 1, 0))
    out_bolt2 = scad.make_cylinder_rsolid(radius=1.1, height=8.0, bottom_face_center=(-4, 25.83762, -6.85807), axis=(1, 0, 0))
    result = scad.cut_rsolid(result, in_bolt0, out_bolt0, in_bolt1, out_bolt1, in_bolt2, out_bolt2, skip_non_intersecting=False)
    
    # ---- feature: inlet-counterbore-seats (subtract, profile=geometry) ----
    in_seat0 = scad.make_cylinder_rsolid(radius=1.7, height=1.5, bottom_face_center=(29.02046, -2.2, 5.02046), axis=(0, 1, 0))
    in_seat1 = scad.make_cylinder_rsolid(radius=1.7, height=1.5, bottom_face_center=(17.14193, -2.2, 1.83762), axis=(0, 1, 0))
    in_seat2 = scad.make_cylinder_rsolid(radius=1.7, height=1.5, bottom_face_center=(25.83762, -2.2, -6.85807), axis=(0, 1, 0))
    result = scad.cut_rsolid(result, in_seat0, in_seat1, in_seat2, skip_non_intersecting=False)
    
    return scad.make_part_rpart(part_id='part', body=result, name='Swept elbow cooling manifold variant 2')

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
